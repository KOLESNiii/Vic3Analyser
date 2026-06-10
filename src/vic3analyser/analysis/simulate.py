"""Forecast the economy forward month-by-month under a plan.

This is the time dimension the rest of the analyser lacks. Given a
:class:`Plan` (an ordered build program + research order), it steps the economy
through the planning horizon:

* construction capacity is spent against the queue, so levels come online over
  time at the rate the player can actually build them;
* at each step the market re-settles to equilibrium prices (via
  :mod:`econ_model`), so the cascading effects of everything built so far are
  reflected — including diminishing returns as a good gets saturated;
* GDP, the government treasury, employment and a standard-of-living proxy are
  tracked into a time series that can be charted against a do-nothing baseline.

The financial model is deliberately simple and anchored on player-visible
observations rather than guessed constants:

* **GDP** is the snapshot's GDP plus the change in total value-added the model
  computes as production grows/optimizes.
* **Treasury** moves by a weekly balance equal to the observed balance plus the
  extra tax the government captures on GDP growth, where the capture rate is the
  player's own observed ``weekly_income / GDP``.
* **Standard of living** is the observed value nudged by employment growth and
  by the price of consumer goods (staple/luxury categories).

All of it is an estimate and flagged as such upstream.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .actions import tech_weeks
from .capacity import (
    CONSTRUCTION_BUILDING,
    construction_cost_per_point,
    points_per_sector_level,
)
from .econ_model import (
    PriceModel,
    pm_value_at,
    solve_equilibrium,
)

# Victoria 3 ticks weekly; a calendar month averages 52/12 weeks.
WEEKS_PER_MONTH = 52.0 / 12.0
# Consumer-goods categories whose prices drive the standard-of-living proxy.
_CONSUMER_CATEGORIES = frozenset({"staple", "luxury"})
# SoL proxy sensitivities (points of SoL per unit of the driver). Coarse.
_SOL_PER_EMPLOYMENT_FRACTION = 5.0
_SOL_PER_CONSUMER_PRICE_FRACTION = -3.0


@dataclass
class BuildStep:
    building_type: str
    levels: int
    state_id: int | None = None


@dataclass
class Plan:
    """An ordered economic plan the simulator can execute."""

    build_program: list[BuildStep] = field(default_factory=list)
    tech_program: list[str] = field(default_factory=list)

    def total_levels(self) -> int:
        return sum(s.levels for s in self.build_program)


@dataclass
class ForecastPoint:
    month: int
    gdp: float
    treasury: float
    weekly_balance: float
    sol: float
    employment: float
    built_levels: int
    insolvent: bool
    prices: dict[str, float] = field(default_factory=dict)


@dataclass
class Forecast:
    points: list[ForecastPoint]
    label: str
    final_gdp: float
    gdp0: float
    final_treasury: float
    min_treasury: float
    final_sol: float
    sol0: float
    ever_insolvent: bool
    horizon_months: int

    @property
    def gdp_growth_fraction(self) -> float:
        return (self.final_gdp - self.gdp0) / self.gdp0 if self.gdp0 else 0.0

    @property
    def annual_growth_rate(self) -> float:
        years = max(self.horizon_months / 12.0, 1e-6)
        if self.gdp0 <= 0 or self.final_gdp <= 0:
            return 0.0
        return (self.final_gdp / self.gdp0) ** (1.0 / years) - 1.0


# --- economy helpers --------------------------------------------------------

def aggregate_holdings(snap: Snapshot) -> dict[str, float]:
    """Player's current buildings collapsed to building_type → total levels."""
    holdings: dict[str, float] = defaultdict(float)
    for b in snap.buildings:
        if b.level > 0:
            holdings[b.building_type] += b.level
    return dict(holdings)


def economy_value_added(
    holdings: dict[str, float],
    chosen_pms: dict[str, list[str]],
    prices: dict[str, float],
    defs: GameDefs,
) -> float:
    """Total value-added across the economy at given prices (the GDP driver).

    Buildings that produce no market good (e.g. the construction sector, whose
    "output" is buildings, not a traded good) are skipped: their goods *demand*
    still moves prices through the footprint, but counting their input cost as
    negative GDP would be wrong — construction is investment, not consumption.
    """
    total = 0.0
    for btype, levels in holdings.items():
        for pm in chosen_pms.get(btype, []):
            if not defs.pm_goods(pm)["output"]:
                continue
            total += pm_value_at(pm, prices, defs) * levels
    return total


def actual_value_added(snap: Snapshot, prices: dict[str, float], defs: GameDefs) -> float:
    """Value-added of current buildings running their *current* PMs."""
    total = 0.0
    for b in snap.buildings:
        levels = max(b.level, 0)
        for apm in b.active_pms:
            total += pm_value_at(apm.pm, prices, defs) * levels
    return total


def total_employment(
    holdings: dict[str, float], chosen_pms: dict[str, list[str]], defs: GameDefs
) -> float:
    total = 0.0
    for btype, levels in holdings.items():
        for pm in chosen_pms.get(btype, []):
            total += sum(defs.pm_employment(pm).values()) * levels
    return total


def consumer_price_index(prices: dict[str, float], defs: GameDefs) -> float:
    """Mean price-vs-base ratio of consumer goods (1.0 = at base)."""
    ratios: list[float] = []
    for g, p in prices.items():
        if defs.good_category(g) in _CONSUMER_CATEGORIES:
            base = defs.good_base_price(g)
            if base and base > 0:
                ratios.append(p / base)
    return sum(ratios) / len(ratios) if ratios else 1.0


# --- the simulator ----------------------------------------------------------

def estimate_capacity(snap: Snapshot, defs: GameDefs) -> float:
    """Best-effort construction points/week when the save doesn't record it.

    Falls back to scaling by the size of the economy (bigger countries build
    faster), with a small floor so a plan can always make some progress.
    """
    pts = snap.construction.points_per_week
    if pts and pts > 0:
        return pts
    gdp = snap.country.gdp or 0.0
    # Very rough: ~1 construction point/week per 12k GDP, floored at 10.
    return max(10.0, gdp / 12000.0)


def _tax_capture_rate(snap: Snapshot, gdp0: float) -> float:
    """Weekly government money captured per unit of GDP, from observed data."""
    inc = snap.country.weekly_income
    if not inc or gdp0 <= 0:
        return 0.0
    return max(0.0, min(inc / gdp0, 0.05))


def simulate_plan(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    plan: Plan,
    capacity: float,
    horizon_months: int,
    label: str = "optimized",
) -> Forecast:
    """Run a plan forward and return its forecast trajectory."""
    researched = set(snap.tech.researched)
    holdings = aggregate_holdings(snap)

    # Anchor on the best-PM value of the *current* economy so the forecast's
    # GDP measures growth from new construction (PM-switch gains are reported
    # separately). GDP ≈ annualized value-added, so we track it as the ratio of
    # value-added to this base (scale-invariant: the unknown units cancel).
    base_prices, _, base_chosen = solve_equilibrium(holdings, researched, model, defs)
    base_value = economy_value_added(holdings, base_chosen, base_prices, defs)
    gdp0 = snap.country.gdp if snap.country.gdp not in (None, 0) else base_value
    if base_value <= 0:
        base_value = 1.0
    sol0 = snap.country.avg_sol if snap.country.avg_sol is not None else 0.0
    treasury = snap.country.treasury or 0.0
    credit = snap.country.credit_limit or 0.0
    base_balance = snap.country.weekly_balance or 0.0
    tax_rate = _tax_capture_rate(snap, gdp0)

    # Baseline employment / consumer index reference.
    emp0 = total_employment(holdings, base_chosen, defs) or 1.0
    cpi0 = consumer_price_index(base_prices, defs)

    # Construction queue from the plan's build program. Capacity grows as
    # construction-sector levels complete (the core growth lever), and building
    # is charged to the treasury via the construction goods basket.
    queue: list[list] = [[s.building_type, float(s.levels)] for s in plan.build_program if s.levels > 0]
    carry = 0.0  # construction points carried toward the current level
    tech_queue = list(plan.tech_program)
    tech_progress = 0.0
    base_capacity = capacity
    per_sector = points_per_sector_level(snap)
    cost_per_point_base = construction_cost_per_point(base_prices, defs, researched, per_sector)
    base_spend_capacity = base_capacity if snap.construction.points_per_week else 0.0

    points: list[ForecastPoint] = []
    min_treasury = treasury
    ever_insolvent = False
    built = 0

    for month in range(1, horizon_months + 1):
        # --- research: advance the head of the tech queue ------------------
        if tech_queue:
            tname = tech_queue[0]
            tech_progress += WEEKS_PER_MONTH
            if tech_progress >= tech_weeks(tname, defs):
                researched.add(tname)
                tech_queue.pop(0)
                tech_progress = 0.0

        # --- construction: spend this month's capacity --------------------
        budget = capacity * WEEKS_PER_MONTH
        spent_points = 0.0
        while queue and budget > 0:
            btype, remaining = queue[0]
            cost = defs.building_construction_cost(btype) or 0.0
            if cost <= 0:
                queue.pop(0)
                continue
            need = cost - carry
            if budget >= need:
                budget -= need
                spent_points += need
                carry = 0.0
                holdings[btype] = holdings.get(btype, 0.0) + 1.0
                built += 1
                if btype == CONSTRUCTION_BUILDING:
                    capacity += per_sector  # capacity compounds
                remaining -= 1.0
                if remaining <= 0:
                    queue.pop(0)
                else:
                    queue[0][1] = remaining
            else:
                carry += budget
                spent_points += budget
                budget = 0.0

        # --- settle the market and read off the metrics -------------------
        prices, _, chosen = solve_equilibrium(holdings, researched, model, defs)
        value = economy_value_added(holdings, chosen, prices, defs)
        gdp = gdp0 * (value / base_value)

        # Treasury: observed balance + extra tax on GDP growth − the *extra*
        # construction goods spend above what the player already builds at.
        cost_per_point = construction_cost_per_point(prices, defs, researched, per_sector)
        spend_week = (spent_points / WEEKS_PER_MONTH) * cost_per_point
        base_spend_week = base_spend_capacity * cost_per_point_base
        weekly_balance = base_balance + tax_rate * (gdp - gdp0) - (spend_week - base_spend_week)
        treasury += weekly_balance * WEEKS_PER_MONTH
        min_treasury = min(min_treasury, treasury)
        insolvent = treasury + credit < 0
        ever_insolvent = ever_insolvent or insolvent

        emp = total_employment(holdings, chosen, defs)
        cpi = consumer_price_index(prices, defs)
        sol = (
            sol0
            + _SOL_PER_EMPLOYMENT_FRACTION * ((emp - emp0) / emp0)
            + _SOL_PER_CONSUMER_PRICE_FRACTION * (cpi - cpi0)
        )

        points.append(
            ForecastPoint(
                month=month,
                gdp=gdp,
                treasury=treasury,
                weekly_balance=weekly_balance,
                sol=sol,
                employment=emp,
                built_levels=built,
                insolvent=insolvent,
                prices={g: round(p, 2) for g, p in prices.items()},
            )
        )

    last = points[-1] if points else None
    return Forecast(
        points=points,
        label=label,
        final_gdp=last.gdp if last else gdp0,
        gdp0=gdp0,
        final_treasury=last.treasury if last else treasury,
        min_treasury=min_treasury,
        final_sol=last.sol if last else sol0,
        sol0=sol0,
        ever_insolvent=ever_insolvent,
        horizon_months=horizon_months,
    )


def forecast_baseline(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    capacity: float,
    horizon_months: int,
) -> Forecast:
    """Do-nothing trajectory: no new construction, current PMs kept.

    Holds the economy flat (current GDP, treasury drifting by the observed
    balance). This is the counterfactual the optimized plan is measured against.
    """
    gdp0 = snap.country.gdp
    sol0 = snap.country.avg_sol if snap.country.avg_sol is not None else 0.0
    if gdp0 in (None, 0):
        base_prices, _, _ = solve_equilibrium(aggregate_holdings(snap), set(snap.tech.researched), model, defs)
        gdp0 = actual_value_added(snap, base_prices, defs)
    treasury = snap.country.treasury or 0.0
    credit = snap.country.credit_limit or 0.0
    base_balance = snap.country.weekly_balance or 0.0

    points: list[ForecastPoint] = []
    min_treasury = treasury
    ever_insolvent = False
    for month in range(1, horizon_months + 1):
        treasury += base_balance * WEEKS_PER_MONTH
        min_treasury = min(min_treasury, treasury)
        insolvent = treasury + credit < 0
        ever_insolvent = ever_insolvent or insolvent
        points.append(
            ForecastPoint(
                month=month,
                gdp=gdp0,
                treasury=treasury,
                weekly_balance=base_balance,
                sol=sol0,
                employment=0.0,
                built_levels=0,
                insolvent=insolvent,
            )
        )
    last = points[-1]
    return Forecast(
        points=points,
        label="baseline",
        final_gdp=last.gdp,
        gdp0=gdp0,
        final_treasury=last.treasury,
        min_treasury=min_treasury,
        final_sol=last.sol,
        sol0=sol0,
        ever_insolvent=ever_insolvent,
        horizon_months=horizon_months,
    )


# --- objective --------------------------------------------------------------

def evaluate_objective(
    fc: Forecast, cfg: OptimizeConfig, credit_limit: float = 0.0
) -> tuple[float, dict[str, float]]:
    """Score a forecast under the configured objective. Higher is better.

    Returns ``(score, breakdown)``. The composite objective combines fractional
    GDP growth, SoL change, and a solvency term (a heavy penalty for ever going
    insolvent, a mild reward for treasury headroom otherwise).
    """
    gdp_term = fc.gdp_growth_fraction
    sol_term = fc.final_sol - fc.sol0
    if fc.ever_insolvent:
        solvency_term = -1.0 + (fc.min_treasury / (abs(credit_limit) + 1.0))
    else:
        solvency_term = 0.1  # mild reward for staying solvent throughout

    breakdown = {"gdp": gdp_term, "sol": sol_term, "solvency": solvency_term}

    obj = cfg.objective
    if obj == "gdp":
        score = fc.final_gdp
    elif obj == "growth":
        score = fc.annual_growth_rate
    elif obj == "cash":
        score = fc.final_treasury
    else:  # composite
        score = (
            cfg.weight_gdp * gdp_term
            + cfg.weight_sol * sol_term
            + cfg.weight_solvency * solvency_term
        )
    # Even for single-metric objectives, never recommend an insolvent plan over
    # a solvent one: fold a hard penalty in.
    if fc.ever_insolvent and obj in ("gdp", "growth", "cash"):
        score -= abs(score) * 0.5 + 1.0
    return score, breakdown
