"""Synthesize the optimizer + forecaster into one explained strategy report.

This is the top-level output of the advanced engine: a sequenced build order,
the multi-year forecast against a do-nothing baseline, the production-method
switches and research that compound it, a plain-language narrative of the
cascades that drove the plan, and the price outlook those cascades imply. It is
the "what should I actually do, and what happens if I do" answer.

Everything is built from the player-visible snapshot and the game defs, and is
explicitly an estimate (the assumptions block says exactly what was assumed or
calibrated).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .actions import economic_build_options, tech_options
from .capacity import CONSTRUCTION_BUILDING, allocate_build_levels
from .econ_model import PriceModel, best_pm_in_group, build_price_model, pm_value_at
from .optimize import OptimizeResult, optimize_growth
from .simulate import (
    Forecast,
    estimate_capacity,
    evaluate_objective,
    forecast_baseline,
    simulate_plan,
)


@dataclass
class StrategyReport:
    summary: dict = field(default_factory=dict)
    assumptions: dict = field(default_factory=dict)
    series: dict = field(default_factory=dict)
    build_order: list[dict] = field(default_factory=list)
    pm_switches: list[dict] = field(default_factory=list)
    tech_program: list[dict] = field(default_factory=list)
    cascade: list[str] = field(default_factory=list)
    price_outlook: list[dict] = field(default_factory=list)
    objective_breakdown: dict = field(default_factory=dict)


def _short(name: str) -> str:
    """Trim the ``building_`` / ``pm_`` prefix for display."""
    for p in ("building_", "pm_"):
        if name.startswith(p):
            return name[len(p):]
    return name


def _series(opt_fc: Forecast, base_fc: Forecast) -> dict:
    months = [p.month for p in opt_fc.points]
    return {
        "months": months,
        "optimized_gdp": [round(p.gdp) for p in opt_fc.points],
        "baseline_gdp": [round(p.gdp) for p in base_fc.points],
        "optimized_treasury": [round(p.treasury) for p in opt_fc.points],
        "baseline_treasury": [round(p.treasury) for p in base_fc.points],
        "optimized_sol": [round(p.sol, 2) for p in opt_fc.points],
        "built_levels": [p.built_levels for p in opt_fc.points],
    }


def _build_order(snap: Snapshot, defs: GameDefs, res: OptimizeResult) -> list[dict]:
    opts = {o.building_type: o for o in economic_build_options(snap, defs)}
    rows: list[dict] = []
    for step in res.plan.build_program:
        opt = opts.get(step.building_type)
        per_level = opt.cost_per_level if opt else defs.building_construction_cost(step.building_type)
        cost = per_level * step.levels if per_level else None
        resource_gated = opt.resource_gated if opt else False
        allocations = allocate_build_levels(snap, step.building_type, step.levels)
        is_capacity = step.building_type == CONSTRUCTION_BUILDING
        rows.append(
            {
                "building_type": step.building_type,
                "name": _short(step.building_type),
                "levels": step.levels,
                "construction_cost": cost,
                "suggested_state": allocations[0].state_id if allocations else None,
                "state_allocations": [
                    {
                        "state_id": a.state_id,
                        "state_name": a.state_name,
                        "levels": a.levels,
                    }
                    for a in allocations
                ],
                "pms": res.chosen_pms.get(step.building_type, []),
                "resource_gated": resource_gated,
                "note": "expands construction capacity" if is_capacity else None,
            }
        )
    return rows


def _pm_switches(snap: Snapshot, defs: GameDefs, prices: dict[str, float]) -> list[dict]:
    """Existing buildings whose active PM is beaten by another at the plan's
    equilibrium prices — free value-added on top of the build plan."""
    researched = set(snap.tech.researched)
    out: list[dict] = []
    for b in snap.buildings:
        if b.level <= 0:
            continue
        active = {apm.pm for apm in b.active_pms}
        for group in defs.building_pm_groups(b.building_type):
            cur = next((p for p in defs.group_pms(group) if p in active), None)
            best = best_pm_in_group(group, researched, prices, defs)
            if best is None or best == cur:
                continue
            cur_val = pm_value_at(cur, prices, defs) if cur else 0.0
            delta = (pm_value_at(best, prices, defs) - cur_val) * max(b.level, 1)
            if delta <= 0:
                continue
            out.append(
                {
                    "building_type": b.building_type,
                    "name": _short(b.building_type),
                    "state_id": b.state_id,
                    "from_pm": cur,
                    "to_pm": best,
                    "delta_value": round(delta),
                }
            )
    out.sort(key=lambda r: r["delta_value"], reverse=True)
    # Collapse duplicates (same type+switch across many buildings) for brevity.
    return out[:25]


def _tech_rows(snap: Snapshot, defs: GameDefs, res: OptimizeResult) -> list[dict]:
    opts = {o.tech: o for o in tech_options(snap, defs)}
    rows: list[dict] = []
    for tech in res.plan.tech_program:
        o = opts.get(tech)
        rows.append(
            {
                "tech": tech,
                "era": o.era if o else None,
                "weeks": o.weeks if o else None,
                "unlocks_pms": [_short(p) for p in (o.unlocks_pms[:4] if o else [])],
                "unlocks_buildings": [_short(b) for b in (o.unlocks_buildings[:4] if o else [])],
            }
        )
    return rows


def _price_outlook(model: PriceModel, res: OptimizeResult, limit: int = 12) -> list[dict]:
    """Goods whose projected equilibrium price moves most under the plan."""
    rows: list[dict] = []
    for g, base in model.base_price.items():
        if base <= 0:
            continue
        start = res.base_prices.get(g, base)
        end = res.final_prices.get(g, base)
        if start <= 0:
            continue
        change = (end / start - 1.0) * 100.0  # percent change in the good's price
        if abs(change) < 1.0:
            continue
        rows.append(
            {
                "good": g,
                "start_ratio": round(start / base, 3),
                "projected_ratio": round(end / base, 3),
                "change_pct": round(change, 1),
            }
        )
    rows.sort(key=lambda r: abs(r["change_pct"]), reverse=True)
    return rows[:limit]


def _cascade_narrative(snap: Snapshot, model: PriceModel, res: OptimizeResult) -> list[str]:
    """Human-readable account of why the plan is shaped the way it is."""
    lines: list[str] = []
    lines.append(
        f"Allocating ~{res.budget_points:,.0f} construction points "
        f"(~{res.capacity:,.0f}/week) across {len(res.added)} building types."
    )

    # Walk the greedy trace, calling out when the best marginal pick rotates to a
    # new good as the previous one saturates — the cascade in action. Collapse
    # the oscillations greedy makes (A→B→A while balancing a chain) and cap the
    # number of lines so the narrative reads as a story, not a log.
    max_lines = 8
    seen_transitions: set[tuple] = set()
    prev = None
    transitions = 0
    for st in res.trace:
        if (
            prev is not None
            and st.key_output is not None
            and st.key_output != prev.key_output
        ):
            key = (prev.key_output, st.key_output)
            if key not in seen_transitions:
                seen_transitions.add(key)
                prev_ratio = (
                    f" (~{prev.key_output_price_ratio:.2f}× base)"
                    if prev.key_output_price_ratio
                    else ""
                )
                lines.append(
                    f"As {_short(prev.building_type)} saturates "
                    f"{prev.key_output}{prev_ratio}, "
                    f"{_short(st.building_type)} (→ {st.key_output}) becomes the "
                    f"strongest marginal build."
                )
                transitions += 1
                if transitions >= max_lines:
                    break
        prev = st
    distinct_goods = len({t.key_output for t in res.trace if t.key_output})
    if distinct_goods > max_lines:
        lines.append(
            f"…the marginal pick keeps rotating, spreading capacity across "
            f"{distinct_goods} goods as each one's price is bid down."
        )

    # Biggest projected price moves.
    movers = _price_outlook(model, res, limit=4)
    if movers:
        parts = [f"{m['good']} {m['change_pct']:+.0f}%" for m in movers]
        lines.append("Projected price shifts from the plan: " + ", ".join(parts) + ".")
    return lines


def build_strategy(
    snap: Snapshot,
    defs: GameDefs,
    cfg: OptimizeConfig | None = None,
    history: list[Snapshot] | None = None,
    capacity: float | None = None,
    horizon_months: int | None = None,
) -> StrategyReport:
    """Run the full advanced analysis and package it for the dashboard/API."""
    cfg = cfg or OptimizeConfig()
    horizon = horizon_months or cfg.horizon_months
    cap = capacity if capacity is not None else (
        cfg.construction_capacity if cfg.construction_capacity else estimate_capacity(snap, defs)
    )

    model = build_price_model(snap, defs, share=cfg.world_market_share, history=history)
    res = optimize_growth(snap, defs, model, cfg, cap, horizon)

    opt_fc = simulate_plan(snap, defs, model, res.plan, cap, horizon, label="optimized")
    base_fc = forecast_baseline(snap, defs, model, cap, horizon)
    score, breakdown = evaluate_objective(opt_fc, cfg, snap.country.credit_limit or 0.0)

    summary = {
        "objective": cfg.objective,
        "horizon_months": horizon,
        "gdp0": round(opt_fc.gdp0),
        "baseline_gdp": round(base_fc.final_gdp),
        "optimized_gdp": round(opt_fc.final_gdp),
        "gdp_uplift_pct": round((opt_fc.final_gdp / base_fc.final_gdp - 1) * 100, 1)
        if base_fc.final_gdp
        else None,
        "annual_growth_pct": round(opt_fc.annual_growth_rate * 100, 1),
        "final_treasury": round(opt_fc.final_treasury),
        "min_treasury": round(opt_fc.min_treasury),
        "ever_insolvent": opt_fc.ever_insolvent,
        "sol0": round(opt_fc.sol0, 1),
        "final_sol": round(opt_fc.final_sol, 1),
        "total_levels": int(sum(res.added.values())),
        "construction_start_capacity": round(res.capacity, 1),
        "construction_final_capacity": round(res.final_capacity or res.capacity, 1),
        "construction_sector_levels_added": res.sector_levels_added,
        "score": round(score, 4),
    }
    assumptions = {
        "construction_capacity": round(cap, 1),
        "capacity_from_save": bool(snap.construction.points_per_week),
        "world_market_share": round(model.share, 3),
        "elasticity_calibrated": model.calibrated,
        "notes": res.notes,
        "estimated": True,
    }

    return StrategyReport(
        summary=summary,
        assumptions=assumptions,
        series=_series(opt_fc, base_fc),
        build_order=_build_order(snap, defs, res),
        pm_switches=_pm_switches(snap, defs, res.final_prices),
        tech_program=_tech_rows(snap, defs, res),
        cascade=_cascade_narrative(snap, model, res),
        price_outlook=_price_outlook(model, res),
        objective_breakdown={k: round(v, 4) for k, v in breakdown.items()},
    )
