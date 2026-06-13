"""Search for the build plan that maximizes economic growth — with cascades.

The optimizer doesn't rank actions in isolation; it allocates the player's
scarce construction capacity across the *whole* horizon while the market reacts.
Two stages:

1. **Greedy marginal allocation (water-filling).** Repeatedly spend the next
   slice of construction on whichever building type yields the most extra
   value-added *per construction point at the current equilibrium*. Because the
   price model makes each extra level of a good worth less (and its inputs worth
   more), the marginal winner naturally rotates — pour into steel until steel
   sags and iron/coal become the better marginal pick. The marginal value is
   measured against the whole economy, so it includes the effect of the new
   build on everything already standing. This is the cascade.

2. **Local-search refinement.** Perturb the greedy allocation (shift capacity
   between types, drop a saturated type, seed a new one) and keep changes that
   improve a fast end-state objective. This explores combinations greedy can't
   reach and escapes its local optimum, bounded by ``search_effort``.

Tech research is layered on top: the technologies that most lift the value of
the player's economy at the planned equilibrium are scheduled in the plan and
unlock partway through the forecast.

The chosen plan is then handed to :mod:`simulate` for the full month-by-month
forecast that the dashboard charts.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .actions import BuildOption, economic_build_options, tech_options
from .capacity import (
    CONSTRUCTION_BUILDING,
    CapacityBudget,
    compute_capacity_budget,
    construction_cost_per_point,
    construction_points_per_level,
)
from .econ_model import (
    PriceModel,
    add_flows,
    best_pm_in_group,
    demand_shift_for,
    pm_value_at,
    solve_equilibrium,
)
from .fiscal import (
    ADMIN_BUILDING,
    admin_capacity_per_level,
    base_bureaucracy_demand,
    gov_capacity,
    tax_capture_factor,
)
from .labour import labour_pool, staffing_factor
from .private_construction import private_construction_points_week
from .production import (
    building_throughput_bonus,
    effective_active_laws,
    throughput_bonus_by_type,
)
from .simulate import (
    WEEKS_PER_MONTH,
    Plan,
    BuildStep,
    aggregate_holdings,
    economy_value_added,
    evaluate_objective,
    reserve_required,
    simulate_plan,
    solvency_headroom,
    _tax_capture_rate,
    total_employment,
)


@dataclass
class StepTrace:
    """One greedy allocation decision, for the cascade narrative."""

    order: int
    building_type: str
    levels: int
    value_per_point: float
    key_output: str | None
    key_output_price_ratio: float | None


@dataclass
class OptimizeResult:
    added: dict[str, float]
    plan: Plan
    trace: list[StepTrace]
    capacity: float  # starting construction points/week
    budget_points: float  # total points spent over the horizon
    final_prices: dict[str, float]
    base_prices: dict[str, float]
    chosen_pms: dict[str, list[str]]
    final_capacity: float = 0.0  # points/week after construction-sector expansion
    sector_levels_added: int = 0
    notes: list[str] = field(default_factory=list)
    # Non-dominated (growth, solvency, SoL) plans considered, when multi_objective.
    pareto: list[dict] = field(default_factory=list)


def _main_output(opt: BuildOption, researched: set[str], prices: dict[str, float], defs: GameDefs) -> str | None:
    """The highest-value output good of a building's best PMs (for narration)."""
    best_good = None
    best_val = 0.0
    for group in opt.pm_groups:
        pm = best_pm_in_group(group, researched, prices, defs)
        if pm is None:
            continue
        for g, q in defs.pm_goods(pm)["output"].items():
            base = defs.good_base_price(g) or 0.0
            if base * q > best_val:
                best_val, best_good = base * q, g
    return best_good


def _batch_footprint(
    opt: BuildOption,
    batch: float,
    researched: set[str],
    prices: dict[str, float],
    defs: GameDefs,
    bonus: float = 0.0,
) -> tuple[dict[str, float], list[str]] | None:
    add_fp: dict[str, float] = {}
    pms: list[str] = []
    for group in opt.pm_groups:
        pm = best_pm_in_group(group, researched, prices, defs)
        if pm is None:
            return None
        pms.append(pm)
        add_flows(add_fp, pm, batch, defs, bonus)
    return add_fp, pms


def _cs_option(defs: GameDefs) -> BuildOption:
    """A synthetic build option for the construction sector (capacity lever)."""
    return BuildOption(
        building_type=CONSTRUCTION_BUILDING,
        cost_per_level=defs.building_construction_cost(CONSTRUCTION_BUILDING) or 25.0,
        pm_groups=defs.building_pm_groups(CONSTRUCTION_BUILDING),
        unlocking_techs=defs.building_unlocking_techs(CONSTRUCTION_BUILDING),
        building_group="bg_construction",
        resource_gated=False,
        max_added_levels=10_000,
    )


def _admin_option(defs: GameDefs) -> BuildOption:
    """A synthetic build option for government_administration (bureaucracy)."""
    return BuildOption(
        building_type=ADMIN_BUILDING,
        cost_per_level=defs.building_construction_cost(ADMIN_BUILDING) or 0.0,
        pm_groups=defs.building_pm_groups(ADMIN_BUILDING),
        unlocking_techs=defs.building_unlocking_techs(ADMIN_BUILDING),
        building_group=defs.building_group_of(ADMIN_BUILDING),
        resource_gated=False,
        max_added_levels=10_000,
    )


def _can_expand_construction(defs: GameDefs) -> bool:
    """Whether the current defs include a usable construction-sector building."""
    return (
        CONSTRUCTION_BUILDING in defs.building_types
        and bool(defs.building_pm_groups(CONSTRUCTION_BUILDING))
        and (defs.building_construction_cost(CONSTRUCTION_BUILDING) or 0.0) > 0
    )


# Damping applied to the *forward* value a construction sector unlocks, since
# future production has diminishing returns we can't fully foresee. Keeps the
# capacity-vs-output trade-off conservative; the CS-on/off outer choice in
# :func:`optimize_growth` is the final safety net.
_CS_FORESIGHT_DISCOUNT = 0.5


def _greedy(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    options: list[BuildOption],
    cfg: OptimizeConfig,
    base_capacity: float,
    horizon_months: int,
    allow_cs: bool = True,
    rounds_per_month: int = 12,
    tick: "Callable[[str], None] | None" = None,
    tick_label: str = "Optimising",
) -> OptimizeResult:
    """Time-aware water-filling: walk month by month, capacity compounds as
    construction sectors complete, land/resource caps and solvency are honoured,
    and the marginal winner rotates as goods saturate (the cascade)."""
    researched = set(snap.tech.researched)
    holdings = aggregate_holdings(snap)
    cap_budget = compute_capacity_budget(snap, defs)
    active_laws = effective_active_laws(snap, defs, cfg)
    per_sector = construction_points_per_level(snap, defs, researched, cfg)
    has_cs = allow_cs and _can_expand_construction(defs)
    cs_opt = _cs_option(defs) if has_cs else None
    # Construction sectors are urban (building-slot- and labour-limited); the save
    # doesn't expose slot counts, so bound their expansion to a sane multiple of
    # the current footprint and the player's state count. Without this the
    # greedy can spam thousands of sectors a 4-state country could never place.
    # (Phase 3's labour budget makes this a hard, principled cap.)
    _cur_cs = aggregate_holdings(snap).get(CONSTRUCTION_BUILDING, 0.0)
    cs_expansion_cap = max(_cur_cs * 2.0, len(snap.states) * 5.0, 15.0)
    # Pace construction-sector expansion over several months so it grows
    # alongside its input producers (you can't operate 20 new sectors before the
    # logging camps that feed them exist, or wood spikes). Spreads the cap across
    # ~6 months; the cascade fills the gaps with the goods those sectors consume.
    cs_month_cap = max(2.0, cs_expansion_cap / 6.0)

    def tp(h: dict[str, float]) -> dict[str, float]:
        return throughput_bonus_by_type(h, researched, active_laws, defs, cfg)

    def bonus_for(btype: str, level_after: float) -> float:
        return building_throughput_bonus(btype, level_after, researched, active_laws, defs, cfg)

    base_prices, _, base_chosen = solve_equilibrium(
        holdings, researched, model, defs, throughput=tp(holdings)
    )
    base_value = economy_value_added(holdings, base_chosen, base_prices, defs, tp(holdings)) or 1.0
    gdp0 = snap.country.gdp if snap.country.gdp not in (None, 0) else base_value
    treasury = snap.country.treasury or 0.0
    credit = snap.country.credit_limit or 0.0
    reserve = reserve_required(snap, cfg)
    base_balance = snap.country.weekly_balance or 0.0
    tax_rate = _tax_capture_rate(snap, gdp0)
    cpp_base = construction_cost_per_point(base_prices, defs, researched, per_sector)
    base_spend_capacity = base_capacity if snap.construction.points_per_week else 0.0

    capacity = base_capacity
    added: dict[str, float] = defaultdict(float)
    arable_used = 0.0
    program: list[BuildStep] = []
    trace: list[StepTrace] = []
    order = 0
    total_spent = 0.0
    carry = 0.0
    tech_queue: list[str] = []  # tech handled separately; kept for parity

    # Bureaucracy coverage: expansion raises demand ∝ total levels, so the plan
    # must build government_administration to stay out of deficit (and keep tax
    # capacity up). We top admin up at each month before pouring into production.
    base_total_levels = sum(holdings.values()) or 1.0
    base_bur_demand = base_bureaucracy_demand(snap)
    admin_per_bur = admin_capacity_per_level(researched, base_prices, defs)[0]
    admin_cost = defs.building_construction_cost(ADMIN_BUILDING) or 0.0
    model_bur = cfg.model_bureaucracy and admin_per_bur > 0 and admin_cost > 0
    admin_opt = _admin_option(defs) if model_bur else None
    base_tax_capacity = gov_capacity(
        holdings, snap, researched, base_prices, defs, active_laws, base_total_levels
    ).tax_capacity

    pool = labour_pool(snap)
    emp0_labour = total_employment(holdings, base_chosen, defs) or 1.0
    sol_for_labour = snap.country.avg_sol or 0.0

    def fiscal_gdp_and_tax(
        h: dict[str, float], raw_gdp: float, chosen: dict[str, list[str]], prices: dict[str, float], month: int
    ) -> tuple[float, float]:
        """Apply labour staffing + bureaucracy penalty + tax-capacity throttle, so
        the search optimises the same constrained objective the forecast scores."""
        adj = raw_gdp
        if cfg.model_labour and pool is not None:
            emp = total_employment(h, chosen, defs)
            adj *= staffing_factor(pool, emp / emp0_labour, month, cfg, sol_for_labour)
        if not cfg.model_bureaucracy:
            return adj, 1.0
        gov = gov_capacity(h, snap, researched, prices, defs, active_laws, base_total_levels)
        adj *= 1.0 - gov.bureaucracy_penalty
        return adj, tax_capture_factor(gov, adj, gdp0, base_tax_capacity)

    base_admin_levels = aggregate_holdings(snap).get(ADMIN_BUILDING, 0.0)

    def admin_levels_needed(h: dict[str, float], gdp_ratio: float = 1.0) -> int:
        """Admin levels to keep both bureaucracy *and* tax capacity in step.

        Bureaucracy demand grows with economic size; tax capacity must grow with
        GDP or the tax throttle chokes income (the solvency trap). We target the
        larger of the two so administration scales with the economy it serves.
        """
        if not model_bur or base_total_levels <= 0:
            return 0
        demand = base_bur_demand * (sum(h.values()) / base_total_levels)
        bur_target = demand / admin_per_bur if admin_per_bur > 0 else 0.0
        # Tax capacity scales linearly with admin levels, so to tax a GDP that is
        # ``gdp_ratio`` times the start we need ~that many times the admin.
        tax_target = base_admin_levels * gdp_ratio if base_admin_levels > 0 else 0.0
        target = max(bur_target, tax_target)
        have = h.get(ADMIN_BUILDING, 0.0)
        return int(target - have + 0.999) if target > have else 0

    def cap_room(opt: BuildOption) -> float:
        cap = cap_budget.cap_for(opt.building_type)
        if cap is not None:
            return max(0.0, cap - added[opt.building_type])
        # Arable buildings are gated separately by the shared free-land pool.
        if cap_budget.is_arable(opt.building_type):
            return float("inf")
        # A resource/land-gated building with no known slot in the player's
        # states can't be placed there (e.g. rye where only wheat/rice grow).
        if opt.resource_gated and cap_budget.has_known_caps:
            return 0.0
        return float("inf")

    gdp_prev = gdp0
    for month in range(1, horizon_months + 1):
        if tick is not None and (month % 6 == 0 or month == horizon_months):
            tick(f"{tick_label} ({month}/{horizon_months} mo)")
        demand_shift = (
            demand_shift_for(gdp_prev / gdp0 - 1.0 if gdp0 else 0.0, model, defs, cfg.demand_elasticity)
            if cfg.model_endogenous_demand
            else None
        )
        prices, footprint, chosen = solve_equilibrium(
            holdings, researched, model, defs, throughput=tp(holdings), demand_shift=demand_shift
        )
        raw_gdp = gdp0 * (economy_value_added(holdings, chosen, prices, defs, tp(holdings)) / base_value)
        gdp, tax_factor = fiscal_gdp_and_tax(holdings, raw_gdp, chosen, prices, month)
        gdp_prev = gdp
        weeks_left = (horizon_months - month + 1) * WEEKS_PER_MONTH
        run_fp = dict(footprint)
        cpp = construction_cost_per_point(prices, defs, researched, per_sector)
        gov_points = capacity * WEEKS_PER_MONTH
        private_points = (
            private_construction_points_week(snap, defs, cfg, cpp) * WEEKS_PER_MONTH
            if cfg.model_investment_pool
            else 0.0
        )
        budget = gov_points + private_points + carry
        # Only the government share of construction is paid from the treasury;
        # the investment pool funds the rest. Attribute spend proportionally.
        treasury_frac = gov_points / (gov_points + private_points) if (gov_points + private_points) > 0 else 1.0
        spent_month = 0.0
        cs_this_month = 0.0  # construction-sector levels added this month (paced)

        def solvent_after(extra_cost: float) -> bool:
            if cfg.solvency_policy != "hard_buffer":
                return True
            candidate_spent = spent_month + extra_cost
            spend_week = (candidate_spent / WEEKS_PER_MONTH) * cpp * treasury_frac
            base_spend_week = base_spend_capacity * cpp_base
            weekly_balance = (
                base_balance + tax_rate * (gdp - gdp0) * tax_factor - (spend_week - base_spend_week)
            )
            projected = treasury + weekly_balance * WEEKS_PER_MONTH
            return solvency_headroom(projected, credit, reserve) >= 0

        # Cover bureaucracy first: build government_administration up to demand so
        # expansion isn't throttled and tax capacity keeps pace (mandatory
        # overhead, like a player keeping bureaucracy out of the red).
        if admin_opt is not None:
            need = admin_levels_needed(holdings, gdp / gdp0 if gdp0 else 1.0)
            while need > 0 and budget >= admin_cost and solvent_after(admin_cost):
                a_bonus = bonus_for(ADMIN_BUILDING, holdings.get(ADMIN_BUILDING, 0.0) + 1.0)
                abf = _batch_footprint(admin_opt, 1.0, researched, model.prices(run_fp), defs, a_bonus)
                if abf is None:
                    break
                for g, v in abf[0].items():
                    run_fp[g] = run_fp.get(g, 0.0) + v
                holdings[ADMIN_BUILDING] = holdings.get(ADMIN_BUILDING, 0.0) + 1.0
                added[ADMIN_BUILDING] += 1.0
                budget -= admin_cost
                spent_month += admin_cost
                order += 1
                program.append(BuildStep(building_type=ADMIN_BUILDING, levels=1))
                trace.append(
                    StepTrace(
                        order=order,
                        building_type=ADMIN_BUILDING,
                        levels=1,
                        value_per_point=0.0,
                        key_output="bureaucracy",
                        key_output_price_ratio=None,
                    )
                )
                need -= 1

        for r in range(rounds_per_month):
            if budget <= 0:
                break
            slice_pts = budget / (rounds_per_month - r)
            cur_prices = model.prices(run_fp)
            best = None  # (score, opt, batch, cost, add_fp, pms, good, is_cs)

            for opt in options:
                if not opt.buildable_now(researched, cur_prices, defs):
                    continue
                room = cap_room(opt)
                if room <= 0:
                    continue
                if cap_budget.is_arable(opt.building_type) and arable_used >= cap_budget.free_arable:
                    continue
                batch = max(1.0, round(slice_pts / opt.cost_per_level))
                batch = min(batch, room)
                if cap_budget.is_arable(opt.building_type):
                    batch = min(batch, cap_budget.free_arable - arable_used)
                if batch < 1:
                    continue
                cost = batch * opt.cost_per_level
                if cost > budget:
                    batch = budget // opt.cost_per_level
                    if batch < 1:
                        continue
                    cost = batch * opt.cost_per_level
                if not solvent_after(cost):
                    continue
                level_after = holdings.get(opt.building_type, 0.0) + batch
                bonus = bonus_for(opt.building_type, level_after)
                bf = _batch_footprint(opt, batch, researched, cur_prices, defs, bonus)
                if bf is None:
                    continue
                add_fp, pms = bf
                new_fp = dict(run_fp)
                for g, v in add_fp.items():
                    new_fp[g] = new_fp.get(g, 0.0) + v
                marg_prices = model.prices(new_fp, demand_shift)
                mv = sum(pm_value_at(pm, marg_prices, defs, bonus) for pm in pms) * batch
                score = mv / cost if cost > 0 else 0.0
                if best is None or score > best[0]:
                    good = _main_output(opt, researched, cur_prices, defs)
                    best = (score, opt, batch, cost, add_fp, pms, good, False)

            best_prod_score = best[0] if best else 0.0

            # Construction sector: invest in capacity if the production it unlocks
            # over the remaining horizon beats building production directly now.
            cs_room = min(cs_expansion_cap - added[CONSTRUCTION_BUILDING], cs_month_cap - cs_this_month)
            if (
                has_cs
                and cs_opt is not None
                and treasury + credit > 0
                and cs_opt.cost_per_level <= budget
                and cs_room >= 1.0
            ):
                batch_cs = max(1.0, round(slice_pts / cs_opt.cost_per_level))
                batch_cs = min(batch_cs, cs_room)
                cost_cs = batch_cs * cs_opt.cost_per_level
                if cost_cs <= budget and solvent_after(cost_cs):
                    future_points = per_sector * batch_cs * weeks_left
                    cs_value = future_points * max(best_prod_score, 0.0) * _CS_FORESIGHT_DISCOUNT
                    cs_score = cs_value / cost_cs if cost_cs > 0 else 0.0
                    if cs_score > best_prod_score:
                        bf = _batch_footprint(cs_opt, batch_cs, researched, cur_prices, defs)
                        add_fp = bf[0] if bf else {}
                        pms = bf[1] if bf else []
                        best = (cs_score, cs_opt, batch_cs, cost_cs, add_fp, pms, None, True)

            if best is None or best[0] <= 0:
                break
            score, opt, batch, cost, add_fp, pms, good, is_cs = best
            holdings[opt.building_type] = holdings.get(opt.building_type, 0.0) + batch
            added[opt.building_type] += batch
            if cap_budget.is_arable(opt.building_type):
                arable_used += batch
            if is_cs:
                capacity += per_sector * batch
                cs_this_month += batch
            for g, v in add_fp.items():
                run_fp[g] = run_fp.get(g, 0.0) + v
            budget -= cost
            spent_month += cost
            order += 1
            ratio = None
            if good is not None:
                base = model.base_price.get(good)
                if base:
                    ratio = model.prices(run_fp).get(good, base) / base
            program.append(BuildStep(building_type=opt.building_type, levels=int(batch)))
            trace.append(
                StepTrace(
                    order=order,
                    building_type=opt.building_type,
                    levels=int(batch),
                    value_per_point=score,
                    key_output=good,
                    key_output_price_ratio=ratio,
                )
            )

        carry = budget if budget > 0 else 0.0
        total_spent += spent_month

        # Treasury: observed balance + extra (capacity-throttled) tax on GDP
        # growth − extra *government* construction spend (the investment pool
        # funds the private share for free).
        spend_week = (spent_month / WEEKS_PER_MONTH) * cpp * treasury_frac
        base_spend_week = base_spend_capacity * cpp_base
        weekly_balance = (
            base_balance + tax_rate * (gdp - gdp0) * tax_factor - (spend_week - base_spend_week)
        )
        treasury += weekly_balance * WEEKS_PER_MONTH

    final_prices, _, chosen_pms = solve_equilibrium(
        holdings, researched, model, defs, throughput=tp(holdings)
    )
    sectors = int(added.get(CONSTRUCTION_BUILDING, 0.0))
    return OptimizeResult(
        added=dict(added),
        plan=Plan(build_program=_merge_program(program)),
        trace=trace,
        capacity=base_capacity,
        budget_points=total_spent,
        final_prices=final_prices,
        base_prices=base_prices,
        chosen_pms=chosen_pms,
        final_capacity=capacity,
        sector_levels_added=sectors,
    )


def _merge_program(program: list[BuildStep]) -> list[BuildStep]:
    """Collapse consecutive same-type steps to keep the build order readable."""
    merged: list[BuildStep] = []
    for step in program:
        if merged and merged[-1].building_type == step.building_type:
            merged[-1].levels += step.levels
        else:
            merged.append(BuildStep(step.building_type, step.levels))
    return merged


def _interleaved_program(trace: list[StepTrace], totals: dict[str, int]) -> list[BuildStep]:
    """Replay the greedy's time-ordered build sequence, capped at the (possibly
    refined) per-type totals, so the reported order keeps the cascade interleaving
    instead of grouping every type into one block.

    Any type the refinement grew beyond what greedy built is appended at the end;
    consecutive same-type steps are then merged for readability.
    """
    remaining = dict(totals)
    steps: list[BuildStep] = []
    for st in trace:
        take = min(st.levels, remaining.get(st.building_type, 0))
        if take > 0:
            steps.append(BuildStep(st.building_type, take))
            remaining[st.building_type] -= take
    for btype, lv in remaining.items():
        if lv > 0:
            steps.append(BuildStep(btype, lv))
    return _merge_program(steps)


# --- fast end-state objective for refinement --------------------------------

def _quick_objective(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    added: dict[str, float],
    cfg: OptimizeConfig,
    gdp0: float,
    base_val: float,
    base_emp: float,
) -> float:
    """Cheap composite score from a single end-state equilibrium.

    Mirrors :func:`simulate.evaluate_objective` but estimates the treasury path
    linearly (GDP ramps from ``gdp0`` to the end state), so the optimizer can
    explore many combinations without a full month-by-month sim each time.
    """
    researched = set(snap.tech.researched)
    active_laws = effective_active_laws(snap, defs, cfg)
    holdings = dict(aggregate_holdings(snap))
    for t, lv in added.items():
        holdings[t] = holdings.get(t, 0.0) + lv
    tp = throughput_bonus_by_type(holdings, researched, active_laws, defs, cfg)
    prices, _, chosen = solve_equilibrium(holdings, researched, model, defs, throughput=tp)
    val = economy_value_added(holdings, chosen, prices, defs, tp)
    gdp_final = gdp0 * (val / base_val) if base_val > 0 else gdp0

    # Labour: understaffing at the horizon scales output down.
    emp = total_employment(holdings, chosen, defs)
    if cfg.model_labour:
        pool = labour_pool(snap)
        if pool is not None and base_emp > 0:
            gdp_final *= staffing_factor(
                pool, emp / base_emp, cfg.horizon_months, cfg, snap.country.avg_sol or 0.0
            )

    # Government capacity: bureaucracy deficit penalises GDP; tax beyond capacity
    # isn't collected (keeps the end-state objective consistent with the sim).
    tax_factor = 1.0
    if cfg.model_bureaucracy:
        base_total_levels = sum(aggregate_holdings(snap).values()) or 1.0
        base_tax_capacity = gov_capacity(
            aggregate_holdings(snap), snap, researched, prices, defs, active_laws, base_total_levels
        ).tax_capacity
        gov = gov_capacity(holdings, snap, researched, prices, defs, active_laws, base_total_levels)
        gdp_final *= 1.0 - gov.bureaucracy_penalty
        tax_factor = tax_capture_factor(gov, gdp_final, gdp0, base_tax_capacity)
    growth = (gdp_final - gdp0) / gdp0 if gdp0 else 0.0

    sol_term = (cfg.weight_sol and (emp - base_emp) / (base_emp or 1.0) * 5.0) or 0.0

    treasury = snap.country.treasury or 0.0
    credit = snap.country.credit_limit or 0.0
    reserve = reserve_required(snap, cfg)
    base_balance = snap.country.weekly_balance or 0.0
    inc = snap.country.weekly_income or 0.0
    tax = max(0.0, min(inc / gdp0, 0.05)) if gdp0 else 0.0
    avg_balance = base_balance + tax * ((gdp_final - gdp0) / 2.0) * tax_factor
    weeks = WEEKS_PER_MONTH * cfg.horizon_months
    end_treasury = treasury + avg_balance * weeks
    insolvent = (end_treasury + credit < 0) or (treasury + credit < 0)
    min_headroom = min(
        solvency_headroom(treasury, credit, reserve),
        solvency_headroom(end_treasury, credit, reserve),
    )
    feasible = min_headroom >= 0
    if not feasible:
        solvency_term = -1.0 + (min_headroom / (abs(credit) + reserve + 1.0))
    elif insolvent:
        solvency_term = -1.0 + end_treasury / (abs(credit) + 1.0)
    else:
        solvency_term = 0.1

    if cfg.objective == "gdp":
        score = gdp_final
    elif cfg.objective == "growth":
        score = growth
    elif cfg.objective == "cash":
        score = end_treasury
    else:
        score = cfg.weight_gdp * growth + cfg.weight_sol * sol_term + cfg.weight_solvency * solvency_term
    if cfg.solvency_policy == "hard_buffer" and not feasible:
        score = -1_000_000_000.0 + solvency_term
    elif insolvent and cfg.objective in ("gdp", "growth", "cash"):
        score -= abs(score) * 0.5 + 1.0
    return score


def _total_cost(added: dict[str, float], cost_by_type: dict[str, float]) -> float:
    return sum(lv * cost_by_type.get(t, 0.0) for t, lv in added.items())


def _violates_caps(
    prod: dict[str, float], cap_budget: CapacityBudget
) -> bool:
    """Whether a production allocation breaks a resource or arable cap."""
    for bt, lv in prod.items():
        cap = cap_budget.cap_for(bt)
        if cap is not None and lv > cap + 1e-6:
            return True
    arable = sum(lv for bt, lv in prod.items() if cap_budget.is_arable(bt))
    return arable > cap_budget.free_arable + 1e-6


def _refine(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    options: list[BuildOption],
    start: dict[str, float],
    cfg: OptimizeConfig,
    cap_budget: CapacityBudget,
    seed: int = 12345,
    tick: "Callable[[str], None] | None" = None,
) -> dict[str, float]:
    """Hill-climb the *production* allocation (construction sectors are kept
    fixed), honouring land/resource caps, keeping quick-objective improvements."""
    effort = max(0, cfg.search_effort)
    if effort == 0:
        return dict(start)

    rng = random.Random(seed)
    cost_by_type = {o.building_type: o.cost_per_level for o in options}
    researched = set(snap.tech.researched)

    base_holdings = aggregate_holdings(snap)
    base_active_laws = effective_active_laws(snap, defs, cfg)
    base_tp = throughput_bonus_by_type(base_holdings, researched, base_active_laws, defs, cfg)
    base_prices, _, base_chosen = solve_equilibrium(
        base_holdings, researched, model, defs, throughput=base_tp
    )
    base_val = economy_value_added(base_holdings, base_chosen, base_prices, defs, base_tp) or 1.0
    gdp0 = snap.country.gdp if snap.country.gdp not in (None, 0) else base_val
    base_emp = total_employment(base_holdings, base_chosen, defs) or 1.0

    # Keep capacity buildings (construction sectors + administration) fixed; only
    # shuffle production around them, so the hill-climb can't break bureaucracy
    # coverage or undo a construction-capacity decision.
    fixed_types = {CONSTRUCTION_BUILDING, ADMIN_BUILDING}
    sectors = {t: lv for t, lv in start.items() if t in fixed_types}
    prod = {t: lv for t, lv in start.items() if lv > 0 and t not in fixed_types}
    budget_total = _total_cost(prod, cost_by_type)

    def obj(production: dict[str, float]) -> float:
        return _quick_objective(
            snap, defs, model, {**sectors, **production}, cfg, gdp0, base_val, base_emp
        )

    best_score = obj(prod)
    # Simulated annealing keeps a *current* state that may be worse than the best
    # seen, so it can climb out of the local optimum greedy hill-climbing gets
    # stuck in. Temperature is scaled to the objective and cooled geometrically.
    anneal = cfg.search_algo == "anneal"
    cur, cur_score = dict(prod), best_score
    temp0 = max(abs(best_score) * 0.10, 1e-3)
    cooling = 0.92

    def has_room(o: BuildOption) -> bool:
        cap = cap_budget.cap_for(o.building_type)
        if cap is not None:
            return cap > 0
        if cap_budget.is_arable(o.building_type):
            return cap_budget.free_arable > 0
        # Land/resource-gated but no known slot in the player's states.
        return not (o.resource_gated and cap_budget.has_known_caps)

    buildable = [
        o
        for o in options
        if o.building_type != CONSTRUCTION_BUILDING
        and o.buildable_now(researched, base_prices, defs)
        and has_room(o)
    ]
    if not buildable:
        return start

    refine_step = max(1, effort // 20)
    for i in range(effort):
        if tick is not None and i % refine_step == 0:
            tick(f"Refining plan ({i}/{effort})")
        cand = dict(cur)
        move = rng.random()
        donors = [t for t, lv in cand.items() if lv > 0]
        opt = rng.choice(buildable)
        if move < 0.45 and donors:
            d = rng.choice(donors)
            chunk = min(cand[d], max(1.0, round(cand[d] * rng.uniform(0.1, 0.5))))
            cand[d] -= chunk
            if cand[d] <= 0:
                del cand[d]
            moved_pts = chunk * cost_by_type.get(d, 0.0)
            add_lv = max(1.0, round(moved_pts / opt.cost_per_level))
            cand[opt.building_type] = cand.get(opt.building_type, 0.0) + add_lv
        elif move < 0.75 and donors:
            del cand[rng.choice(donors)]
        else:
            add_lv = max(1.0, round((budget_total * rng.uniform(0.02, 0.1)) / opt.cost_per_level))
            cand[opt.building_type] = cand.get(opt.building_type, 0.0) + add_lv

        if _total_cost(cand, cost_by_type) > budget_total * 1.02:
            continue
        if _violates_caps(cand, cap_budget):
            continue
        score = obj(cand)
        if anneal:
            temp = temp0 * (cooling ** (i * 10.0 / max(effort, 1)))
            delta = score - cur_score
            if delta >= 0 or rng.random() < _accept_prob(delta, temp):
                cur, cur_score = cand, score
            if score > best_score:
                best_score, prod = score, cand  # always remember the best seen
        elif score > best_score:
            best_score, prod = score, cand
            cur, cur_score = cand, score
    return {**sectors, **prod}


def _accept_prob(delta: float, temp: float) -> float:
    """Metropolis acceptance probability for a worse move (delta < 0)."""
    if temp <= 0:
        return 0.0
    import math

    return math.exp(max(-50.0, delta / temp))


# --- tech scheduling --------------------------------------------------------

def _schedule_tech(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    holdings: dict[str, float],
    final_prices: dict[str, float],
    economic_types: set[str],
    limit: int = 6,
) -> list[str]:
    """Pick economic techs that most lift the player's economy, prereqs first.

    Uplift = extra value-added the player's *current* building types would gain
    if a single missing tech unlocked a better PM, valued at the planned
    equilibrium prices and weighted by levels. Restricted to economic buildings
    so military/administrative techs don't leak into the research order.
    """
    researched = set(snap.tech.researched)
    levels_by_type = {t: lv for t, lv in holdings.items() if t in economic_types}
    uplift: dict[str, float] = defaultdict(float)

    for btype, levels in levels_by_type.items():
        for group in defs.building_pm_groups(btype):
            pms = defs.group_pms(group)
            avail = [
                pm_value_at(pm, final_prices, defs)
                for pm in pms
                if all(t in researched for t in defs.pm_unlocking_techs(pm))
            ]
            cur_best = max(avail) if avail else 0.0
            for pm in pms:
                missing = [t for t in defs.pm_unlocking_techs(pm) if t not in researched]
                if len(missing) != 1:
                    continue
                gain = pm_value_at(pm, final_prices, defs) - cur_best
                if gain > 0:
                    uplift[missing[0]] += gain * levels

    opts = {o.tech: o for o in tech_options(snap, defs)}
    ranked = sorted(uplift.items(), key=lambda kv: kv[1], reverse=True)
    out: list[str] = []
    for tech, _gain in ranked:
        opt = opts.get(tech)
        if opt is None or not opt.researchable_now(researched):
            continue
        out.append(tech)
        if len(out) >= limit:
            break
    return out


# --- public entry point -----------------------------------------------------

def _assemble(
    greedy: OptimizeResult,
    refined_added: dict[str, float],
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    cfg: OptimizeConfig,
) -> OptimizeResult:
    """Build an ordered plan from a greedy result + refined production levels.

    The build order preserves the greedy's *interleaved* construction sequence
    (input producers come online alongside their consumers — e.g. logging camps
    right after the construction sectors that burn wood — so a good's price
    doesn't spike while you build out), reconciled to the refined per-type totals.
    """
    totals = {t: int(lv) for t, lv in refined_added.items() if lv >= 1}
    program = _interleaved_program(greedy.trace, totals)

    holdings = dict(aggregate_holdings(snap))
    for t, lv in refined_added.items():
        holdings[t] = holdings.get(t, 0.0) + lv
    researched = set(snap.tech.researched)
    tp = throughput_bonus_by_type(
        holdings, researched, effective_active_laws(snap, defs, cfg), defs, cfg
    )
    final_prices, _, chosen_pms = solve_equilibrium(
        holdings, researched, model, defs, throughput=tp
    )
    res = OptimizeResult(
        added={t: lv for t, lv in refined_added.items() if lv >= 1},
        plan=Plan(build_program=program),
        trace=greedy.trace,
        capacity=greedy.capacity,
        budget_points=greedy.budget_points,
        final_prices=final_prices,
        base_prices=greedy.base_prices,
        chosen_pms=chosen_pms,
        final_capacity=greedy.final_capacity,
        sector_levels_added=greedy.sector_levels_added,
    )
    return res


def _pareto_frontier(candidates: list[tuple]) -> list[dict]:
    """Non-dominated plans on (GDP growth ↑, min headroom ↑, final SoL ↑).

    Surfaces the genuine trade-offs between the plans the search evaluated, so
    the report can show "more growth costs solvency headroom" rather than only
    the single objective-optimal plan.
    """
    pts = [
        {
            "growth_pct": round(fc.annual_growth_rate * 100, 1),
            "min_headroom": round(fc.min_headroom),
            "final_sol": round(fc.final_sol, 1),
            "feasible": fc.solvency_feasible,
            "total_levels": int(sum(res.added.values())),
            "_key": (fc.annual_growth_rate, fc.min_headroom, fc.final_sol),
        }
        for res, fc in candidates
    ]

    def dominated(a: dict, b: dict) -> bool:  # b dominates a?
        ge = all(b["_key"][i] >= a["_key"][i] for i in range(3))
        gt = any(b["_key"][i] > a["_key"][i] for i in range(3))
        return ge and gt

    front = [p for p in pts if not any(dominated(p, q) for q in pts if q is not p)]
    # Dedup and drop the sort key; biggest growth first.
    seen: set = set()
    out: list[dict] = []
    for p in sorted(front, key=lambda p: -p["_key"][0]):
        key = p["_key"]
        if key in seen:
            continue
        seen.add(key)
        out.append({k: v for k, v in p.items() if k != "_key"})
    return out


def optimize_growth(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    cfg: OptimizeConfig,
    capacity: float,
    horizon_months: int | None = None,
    tick: "Callable[[str], None] | None" = None,
) -> OptimizeResult:
    """Growth-maximizing plan: time-aware water-filling (capacity compounds via
    construction-sector investment) + production refinement. Tries expanding
    construction *and* not expanding it, and keeps whichever forecasts better —
    so capacity expansion is only recommended when it actually pays off."""
    horizon = horizon_months or cfg.horizon_months
    options = economic_build_options(snap, defs)
    cap_budget = compute_capacity_budget(snap, defs)

    best_res: OptimizeResult | None = None
    best_score = float("-inf")
    frontier: list[tuple[OptimizeResult, object]] = []

    def _forecast(res: OptimizeResult):
        return simulate_plan(
            snap, defs, model, res.plan, capacity, horizon, cfg=cfg, pace=True,
            tick=tick, tick_label="Scoring plan",
        )

    for allow_cs in (True, False):
        label = f"Optimising ({'with' if allow_cs else 'without'} new construction)"
        greedy = _greedy(
            snap, defs, model, options, cfg, capacity, horizon,
            allow_cs=allow_cs, tick=tick, tick_label=label,
        )
        # Refinement optimises a fast *proxy* objective, which can diverge from
        # the full forecast; score the unrefined greedy plan too and keep
        # whichever actually wins, so refinement can only help.
        candidates = [_assemble(greedy, greedy.added, snap, defs, model, cfg)]
        refined = _refine(snap, defs, model, options, greedy.added, cfg, cap_budget, tick=tick)
        if refined != greedy.added:
            candidates.append(_assemble(greedy, refined, snap, defs, model, cfg))
        for res in candidates:
            fc = _forecast(res)
            frontier.append((res, fc))
            score = evaluate_objective(fc, cfg, snap.country.credit_limit or 0.0)[0]
            if score > best_score:
                best_score, best_res = score, res

    res = best_res
    assert res is not None
    if cfg.multi_objective:
        res.pareto = _pareto_frontier(frontier)

    economic_types = {o.building_type for o in options}
    holdings = dict(aggregate_holdings(snap))
    for t, lv in res.added.items():
        holdings[t] = holdings.get(t, 0.0) + lv
    res.plan.tech_program = _schedule_tech(
        snap, defs, model, holdings, res.final_prices, economic_types
    )

    notes: list[str] = []
    if model.calibrated:
        notes.append(f"Price elasticity calibrated from save history (share≈{model.share:.0%}).")
    else:
        notes.append(f"Price elasticity uses assumed market share {model.share:.0%} (no history to calibrate).")
    if snap.construction.points_per_week:
        notes.append(f"Construction capacity {snap.construction.points_per_week:,.0f}/wk read from the save.")
    else:
        notes.append("Construction capacity estimated (not recorded in the save).")
    if res.sector_levels_added > 0:
        notes.append(
            f"Plan expands construction: +{res.sector_levels_added} sector level(s) "
            f"→ ~{res.final_capacity:,.0f}/wk by the horizon."
        )
    res.notes = notes
    return res
