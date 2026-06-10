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
    points_per_sector_level,
)
from .econ_model import (
    PriceModel,
    add_flows,
    best_pm_in_group,
    pm_value_at,
    solve_equilibrium,
)
from .simulate import (
    WEEKS_PER_MONTH,
    Plan,
    BuildStep,
    aggregate_holdings,
    economy_value_added,
    evaluate_objective,
    simulate_plan,
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
    opt: BuildOption, batch: float, researched: set[str], prices: dict[str, float], defs: GameDefs
) -> tuple[dict[str, float], list[str]] | None:
    add_fp: dict[str, float] = {}
    pms: list[str] = []
    for group in opt.pm_groups:
        pm = best_pm_in_group(group, researched, prices, defs)
        if pm is None:
            return None
        pms.append(pm)
        add_flows(add_fp, pm, batch, defs)
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
    base_capacity: float,
    horizon_months: int,
    allow_cs: bool = True,
    rounds_per_month: int = 12,
) -> OptimizeResult:
    """Time-aware water-filling: walk month by month, capacity compounds as
    construction sectors complete, land/resource caps and solvency are honoured,
    and the marginal winner rotates as goods saturate (the cascade)."""
    researched = set(snap.tech.researched)
    holdings = aggregate_holdings(snap)
    cap_budget = compute_capacity_budget(snap, defs)
    per_sector = points_per_sector_level(snap)
    has_cs = allow_cs and _can_expand_construction(defs)
    cs_opt = _cs_option(defs) if has_cs else None

    base_prices, _, base_chosen = solve_equilibrium(holdings, researched, model, defs)
    base_value = economy_value_added(holdings, base_chosen, base_prices, defs) or 1.0
    gdp0 = snap.country.gdp if snap.country.gdp not in (None, 0) else base_value
    treasury = snap.country.treasury or 0.0
    credit = snap.country.credit_limit or 0.0
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

    def cap_room(opt: BuildOption) -> float:
        cap = cap_budget.cap_for(opt.building_type)
        if cap is None and opt.resource_gated and cap_budget.has_known_caps:
            return 0.0
        return float("inf") if cap is None else max(0.0, cap - added[opt.building_type])

    for month in range(1, horizon_months + 1):
        prices, footprint, chosen = solve_equilibrium(holdings, researched, model, defs)
        gdp = gdp0 * (economy_value_added(holdings, chosen, prices, defs) / base_value)
        weeks_left = (horizon_months - month + 1) * WEEKS_PER_MONTH
        run_fp = dict(footprint)
        budget = capacity * WEEKS_PER_MONTH + carry
        spent_month = 0.0

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
                bf = _batch_footprint(opt, batch, researched, cur_prices, defs)
                if bf is None:
                    continue
                add_fp, pms = bf
                new_fp = dict(run_fp)
                for g, v in add_fp.items():
                    new_fp[g] = new_fp.get(g, 0.0) + v
                mv = sum(pm_value_at(pm, model.prices(new_fp), defs) for pm in pms) * batch
                score = mv / cost if cost > 0 else 0.0
                if best is None or score > best[0]:
                    good = _main_output(opt, researched, cur_prices, defs)
                    best = (score, opt, batch, cost, add_fp, pms, good, False)

            best_prod_score = best[0] if best else 0.0

            # Construction sector: invest in capacity if the production it unlocks
            # over the remaining horizon beats building production directly now.
            if (
                has_cs
                and cs_opt is not None
                and treasury + credit > 0
                and cs_opt.cost_per_level <= budget
            ):
                batch_cs = max(1.0, round(slice_pts / cs_opt.cost_per_level))
                cost_cs = batch_cs * cs_opt.cost_per_level
                if cost_cs <= budget:
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

        # Treasury: observed balance + extra tax on GDP growth − extra
        # construction goods spend above the player's current build rate.
        cpp = construction_cost_per_point(prices, defs, researched, per_sector)
        spend_week = (spent_month / WEEKS_PER_MONTH) * cpp
        base_spend_week = base_spend_capacity * cpp_base
        weekly_balance = base_balance + tax_rate * (gdp - gdp0) - (spend_week - base_spend_week)
        treasury += weekly_balance * WEEKS_PER_MONTH

    final_prices, _, chosen_pms = solve_equilibrium(holdings, researched, model, defs)
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
    holdings = dict(aggregate_holdings(snap))
    for t, lv in added.items():
        holdings[t] = holdings.get(t, 0.0) + lv
    prices, _, chosen = solve_equilibrium(holdings, researched, model, defs)
    val = economy_value_added(holdings, chosen, prices, defs)
    gdp_final = gdp0 * (val / base_val) if base_val > 0 else gdp0
    growth = (gdp_final - gdp0) / gdp0 if gdp0 else 0.0

    emp = total_employment(holdings, chosen, defs)
    sol_term = (cfg.weight_sol and (emp - base_emp) / (base_emp or 1.0) * 5.0) or 0.0

    treasury = snap.country.treasury or 0.0
    credit = snap.country.credit_limit or 0.0
    base_balance = snap.country.weekly_balance or 0.0
    inc = snap.country.weekly_income or 0.0
    tax = max(0.0, min(inc / gdp0, 0.05)) if gdp0 else 0.0
    avg_balance = base_balance + tax * ((gdp_final - gdp0) / 2.0)
    weeks = WEEKS_PER_MONTH * cfg.horizon_months
    end_treasury = treasury + avg_balance * weeks
    insolvent = (end_treasury + credit < 0) or (treasury + credit < 0)
    solvency_term = (-1.0 + end_treasury / (abs(credit) + 1.0)) if insolvent else 0.1

    if cfg.objective == "gdp":
        score = gdp_final
    elif cfg.objective == "growth":
        score = growth
    elif cfg.objective == "cash":
        score = end_treasury
    else:
        score = cfg.weight_gdp * growth + cfg.weight_sol * sol_term + cfg.weight_solvency * solvency_term
    if insolvent and cfg.objective in ("gdp", "growth", "cash"):
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
    base_prices, _, base_chosen = solve_equilibrium(base_holdings, researched, model, defs)
    base_val = economy_value_added(base_holdings, base_chosen, base_prices, defs) or 1.0
    gdp0 = snap.country.gdp if snap.country.gdp not in (None, 0) else base_val
    base_emp = total_employment(base_holdings, base_chosen, defs) or 1.0

    # Keep construction sectors fixed; only shuffle production around them.
    sectors = {t: lv for t, lv in start.items() if t == CONSTRUCTION_BUILDING}
    prod = {t: lv for t, lv in start.items() if lv > 0 and t != CONSTRUCTION_BUILDING}
    budget_total = _total_cost(prod, cost_by_type)

    def obj(production: dict[str, float]) -> float:
        return _quick_objective(
            snap, defs, model, {**sectors, **production}, cfg, gdp0, base_val, base_emp
        )

    best_score = obj(prod)
    def has_room(o: BuildOption) -> bool:
        cap = cap_budget.cap_for(o.building_type)
        if cap is None and o.resource_gated and cap_budget.has_known_caps:
            return False
        if cap is not None and cap <= 0:
            return False
        return not cap_budget.is_arable(o.building_type) or cap_budget.free_arable > 0

    buildable = [
        o
        for o in options
        if o.building_type != CONSTRUCTION_BUILDING
        and o.buildable_now(researched, base_prices, defs)
        and has_room(o)
    ]
    if not buildable:
        return start

    for _ in range(effort):
        cand = dict(prod)
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
        if score > best_score:
            best_score, prod = score, cand
    return {**sectors, **prod}


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
) -> OptimizeResult:
    """Build an ordered plan from a greedy result + refined production levels."""
    order_index = {st.building_type: i for i, st in enumerate(greedy.trace)}
    items = sorted(refined_added.items(), key=lambda kv: order_index.get(kv[0], 10_000))
    program = _merge_program([BuildStep(t, int(lv)) for t, lv in items if lv >= 1])

    holdings = dict(aggregate_holdings(snap))
    for t, lv in refined_added.items():
        holdings[t] = holdings.get(t, 0.0) + lv
    final_prices, _, chosen_pms = solve_equilibrium(
        holdings, set(snap.tech.researched), model, defs
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


def optimize_growth(
    snap: Snapshot,
    defs: GameDefs,
    model: PriceModel,
    cfg: OptimizeConfig,
    capacity: float,
    horizon_months: int | None = None,
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
    for allow_cs in (True, False):
        greedy = _greedy(snap, defs, model, options, capacity, horizon, allow_cs=allow_cs)
        refined = _refine(snap, defs, model, options, greedy.added, cfg, cap_budget)
        res = _assemble(greedy, refined, snap, defs, model)
        fc = simulate_plan(snap, defs, model, res.plan, capacity, horizon)
        score, _ = evaluate_objective(fc, cfg, snap.country.credit_limit or 0.0)
        if score > best_score:
            best_score, best_res = score, res

    res = best_res
    assert res is not None

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
