"""Tests for the system-level optimizer / forecaster.

Uses a small synthetic economy (iron + coal → steel → tools) that exhibits real
cascades: building steel drains iron and coal, so a naive all-steel plan should
lose to a diversified one. All hermetic — no real game data or DB needed.
"""

from __future__ import annotations

import json

from vic3analyser.config import OptimizeConfig
from vic3analyser.extract.models import (
    ActivePM,
    Building,
    CountryEconomy,
    MarketGood,
    Snapshot,
    StateInfo,
    TechState,
)
from vic3analyser.ingest.defs import GameDefs
from vic3analyser.pipeline import _ser
from vic3analyser.analysis import econ_model as em
from vic3analyser.analysis import simulate as sim
from vic3analyser.analysis import optimize as opt
from vic3analyser.analysis.actions import economic_build_options, tech_options
from vic3analyser.analysis.capacity import allocate_build_levels, compute_capacity_budget
from vic3analyser.analysis.strategy import build_strategy


def _defs() -> GameDefs:
    def wf(**mods):
        return {"building_modifiers": {"workforce_scaled": dict(mods)}}

    return GameDefs(
        goods={
            "iron": {"cost": 40, "category": "industrial", "traded_quantity": 10},
            "coal": {"cost": 30, "category": "industrial", "traded_quantity": 10},
            "steel": {"cost": 70, "category": "industrial", "traded_quantity": 10},
            "tools": {"cost": 60, "category": "industrial", "traded_quantity": 10},
            "grain": {"cost": 20, "category": "staple", "traded_quantity": 10},
        },
        production_methods={
            "pm_iron_mine": {**wf(goods_output_iron_add=40, building_employment_laborers_add=3000), "unlocking_technologies": []},
            "pm_coal_mine": {**wf(goods_output_coal_add=40, building_employment_laborers_add=3000), "unlocking_technologies": []},
            "pm_steel_basic": {**wf(goods_input_iron_add=30, goods_input_coal_add=10, goods_output_steel_add=30, building_employment_laborers_add=4000), "unlocking_technologies": []},
            "pm_steel_auto": {**wf(goods_input_iron_add=40, goods_input_coal_add=20, goods_output_steel_add=60, building_employment_machinists_add=3000), "unlocking_technologies": ["steam"]},
            "pm_tools": {**wf(goods_input_steel_add=20, goods_output_tools_add=30, building_employment_laborers_add=3000), "unlocking_technologies": []},
            "pm_grain_farm": {**wf(goods_output_grain_add=30, building_employment_farmers_add=2000), "unlocking_technologies": []},
        },
        production_method_groups={
            "pmg_iron": {"production_methods": ["pm_iron_mine"]},
            "pmg_coal": {"production_methods": ["pm_coal_mine"]},
            "pmg_steel": {"production_methods": ["pm_steel_basic", "pm_steel_auto"]},
            "pmg_tools": {"production_methods": ["pm_tools"]},
            "pmg_grain": {"production_methods": ["pm_grain_farm"]},
        },
        building_types={
            "building_iron_mine": {"production_method_groups": ["pmg_iron"], "building_group": "bg_mining", "required_construction": "construction_cost_low"},
            "building_coal_mine": {"production_method_groups": ["pmg_coal"], "building_group": "bg_mining", "required_construction": "construction_cost_low"},
            "building_steel_mill": {"production_method_groups": ["pmg_steel"], "building_group": "bg_heavy_industry", "required_construction": "construction_cost_medium"},
            "building_tools_workshop": {"production_method_groups": ["pmg_tools"], "building_group": "bg_light_industry", "required_construction": "construction_cost_medium"},
            "building_grain_farm": {"production_method_groups": ["pmg_grain"], "building_group": "bg_agriculture", "required_construction": "construction_cost_very_low"},
        },
        technologies={"steam": {"era": "era_2", "category": "production"}},
        script_values={
            "construction_cost_very_low": 100,
            "construction_cost_low": 200,
            "construction_cost_medium": 400,
        },
    )


def _defs_with_construction() -> GameDefs:
    d = _defs()
    d.goods["wood"] = {"cost": 20, "category": "industrial", "traded_quantity": 10}
    d.production_methods["pm_costly_construction"] = {
        "building_modifiers": {
            "workforce_scaled": {
                "goods_input_wood_add": 100,
                "building_employment_laborers_add": 5000,
            }
        },
        "unlocking_technologies": [],
    }
    d.production_method_groups["pmg_construction"] = {
        "production_methods": ["pm_costly_construction"]
    }
    d.building_types["building_construction_sector"] = {
        "production_method_groups": ["pmg_construction"],
        "building_group": "bg_construction",
        "required_construction": "construction_cost_very_low",
    }
    return d


def _snap(steel_price: float = 95.0, **country_over) -> Snapshot:
    country = dict(
        tag="GBR", gdp=100000.0, treasury=20000.0, weekly_income=700.0,
        weekly_expense=650.0, weekly_balance=50.0, credit_limit=50000.0, avg_sol=12.0,
    )
    country.update(country_over)
    return Snapshot(
        date="1836.4.1",
        player_tag="GBR",
        country=CountryEconomy(**country),
        market=[
            MarketGood(good="iron", price=44.0, base_price=40.0, category="industrial"),
            MarketGood(good="coal", price=33.0, base_price=30.0, category="industrial"),
            MarketGood(good="steel", price=steel_price, base_price=70.0, category="industrial"),
            MarketGood(good="tools", price=66.0, base_price=60.0, category="industrial"),
            MarketGood(good="grain", price=20.0, base_price=20.0, category="staple"),
        ],
        buildings=[
            Building(id=1, building_type="building_steel_mill", level=5, active_pms=[ActivePM(pm="pm_steel_basic")]),
            Building(id=2, building_type="building_iron_mine", level=4, active_pms=[ActivePM(pm="pm_iron_mine")]),
            Building(id=3, building_type="building_coal_mine", level=3, active_pms=[ActivePM(pm="pm_coal_mine")]),
        ],
        tech=TechState(researched=["steam"]),
    )


# --- defs accessors ---------------------------------------------------------

def test_defs_accessors_resolve_script_values_and_employment():
    d = _defs()
    assert d.building_construction_cost("building_steel_mill") == 400.0  # alias resolved
    assert d.building_construction_cost("building_grain_farm") == 100.0
    assert d.good_traded_quantity("iron") == 10.0
    assert d.good_category("grain") == "staple"
    emp = d.pm_employment("pm_steel_basic")
    assert emp.get("laborers") == 4000.0


# --- price model ------------------------------------------------------------

def test_price_model_monotonic_and_cascading():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.25)
    fp = em.snapshot_footprint(s, d)
    p0 = m.prices(fp)
    # More steel supply ⇒ steel price falls.
    more_steel = dict(fp); more_steel["steel"] = fp.get("steel", 0) + 200
    assert m.prices(more_steel)["steel"] < p0["steel"]
    # More steel *production* also consumes iron ⇒ iron price rises (cascade).
    more_steel["iron"] = fp.get("iron", 0) - 200
    assert m.prices(more_steel)["iron"] > p0["iron"]


def test_equilibrium_converges_and_picks_best_pm():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.25)
    holdings = {"building_steel_mill": 5.0, "building_iron_mine": 4.0, "building_coal_mine": 3.0}
    prices, fp, chosen = em.solve_equilibrium(holdings, {"steam"}, m, d)
    # converged prices are finite and within Vic3's clamp band
    for g, p in prices.items():
        base = d.good_base_price(g)
        assert 0.25 * base - 1e-6 <= p <= 1.75 * base + 1e-6
    # with steam available the steel mill runs the higher-output automated PM
    assert "pm_steel_auto" in chosen["building_steel_mill"]


def test_calibrate_share_from_history():
    d = _defs()
    older = _snap()
    # newer snapshot: player added steel capacity and steel price fell.
    newer = _snap(steel_price=82.0)
    newer.buildings[0].level = 9  # more steel mills ⇒ more steel supply
    est = em.calibrate_share([older, newer], d)
    assert est is None or (0.01 <= est <= 1.0)


# --- actions ----------------------------------------------------------------

def test_economic_build_options_gating_and_cost():
    d = _defs()
    s = _snap()
    opts = {o.building_type: o for o in economic_build_options(s, d)}
    assert "building_steel_mill" in opts
    assert opts["building_steel_mill"].cost_per_level == 400.0
    assert opts["building_iron_mine"].resource_gated is True  # bg_mining
    assert opts["building_steel_mill"].resource_gated is False
    # tech options surface economic techs only
    techs = {t.tech for t in tech_options(s, d)}
    # steam is already researched in the snapshot, so it shouldn't appear
    assert "steam" not in techs


# --- capacity ---------------------------------------------------------------

def test_capacity_budget_and_state_allocation_respect_caps():
    d = _defs()
    s = _snap()
    s.buildings[1].state_id = 1
    s.states = [
        StateInfo(
            id=1,
            name="STATE_A",
            infrastructure=20,
            infrastructure_used=5,
            arable_land=8,
            arable_total=10,
            arable_buildings=["building_grain_farm"],
            capped_resources={"building_iron_mine": 6},
        ),
        StateInfo(
            id=2,
            name="STATE_B",
            infrastructure=12,
            infrastructure_used=2,
            arable_land=1,
            arable_total=5,
            arable_used=1,
            arable_buildings=["building_grain_farm"],
            capped_resources={"building_iron_mine": 2},
        ),
    ]

    budget = compute_capacity_budget(s, d)
    assert budget.cap_for("building_iron_mine") == 4.0
    assert budget.free_arable == 6.0

    iron_alloc = allocate_build_levels(s, "building_iron_mine", 4)
    assert sum(a.levels for a in iron_alloc) == 4
    assert {a.state_id: a.levels for a in iron_alloc} == {1: 2, 2: 2}

    farm_alloc = allocate_build_levels(s, "building_grain_farm", 6)
    assert sum(a.levels for a in farm_alloc) == 6
    assert all(a.levels <= 4 for a in farm_alloc)


# --- simulator --------------------------------------------------------------

def test_simulate_builds_over_time_and_baseline_flat():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.25)
    cap = 50.0  # points/week
    plan = sim.Plan(build_program=[sim.BuildStep("building_iron_mine", 10)])
    fc = sim.simulate_plan(s, d, m, plan, capacity=cap, horizon_months=24)
    base = sim.forecast_baseline(s, d, m, cap, 24)
    assert fc.points[-1].built_levels > 0
    assert fc.points[-1].built_levels >= fc.points[0].built_levels  # monotonic
    # baseline holds GDP flat at the starting value
    assert all(abs(p.gdp - base.gdp0) < 1.0 for p in base.points)


def test_simulate_flags_insolvency():
    d = _defs()
    # heavy deficit, thin treasury, no credit ⇒ baseline goes insolvent.
    s = _snap(treasury=100.0, weekly_balance=-500.0, credit_limit=0.0)
    m = em.build_price_model(s, d, share=0.25)
    base = sim.forecast_baseline(s, d, m, 50.0, 24)
    assert base.ever_insolvent is True


def test_simulate_gdp_uses_scale_invariant_ratio():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.25)
    plan = sim.Plan(build_program=[sim.BuildStep("building_tools_workshop", 6)])
    fc = sim.simulate_plan(s, d, m, plan, capacity=50.0, horizon_months=24)
    # building profitable downstream capacity grows GDP above the anchor
    assert fc.final_gdp > fc.gdp0


def test_objective_prefers_more_growth_when_solvent():
    d = _defs()
    s = _snap(treasury=100000.0, credit_limit=100000.0)
    m = em.build_price_model(s, d, share=0.25)
    cfg = _cfg(objective="growth")
    low = sim.simulate_plan(
        s, d, m, sim.Plan(build_program=[sim.BuildStep("building_iron_mine", 1)]), 50.0, 24, cfg=cfg
    )
    high = sim.simulate_plan(
        s, d, m, sim.Plan(build_program=[sim.BuildStep("building_iron_mine", 8)]), 50.0, 24, cfg=cfg
    )
    low_score, _ = sim.evaluate_objective(low, cfg, s.country.credit_limit)
    high_score, _ = sim.evaluate_objective(high, cfg, s.country.credit_limit)
    assert high.solvency_feasible and low.solvency_feasible
    assert high_score > low_score


def test_infeasible_plan_loses_to_feasible_plan():
    d = _defs_with_construction()
    s = _snap(
        treasury=8000.0,
        weekly_income=500.0,
        weekly_expense=500.0,
        weekly_balance=0.0,
        credit_limit=0.0,
    )
    cfg = _cfg(objective="growth", solvency_buffer_weeks=12)
    m = em.build_price_model(s, d, share=0.25)
    feasible = sim.simulate_plan(s, d, m, sim.Plan(), 80.0, 12, cfg=cfg)
    infeasible = sim.simulate_plan(
        s,
        d,
        m,
        sim.Plan(build_program=[sim.BuildStep("building_steel_mill", 20)]),
        80.0,
        12,
        cfg=cfg,
    )
    feasible_score, _ = sim.evaluate_objective(feasible, cfg, s.country.credit_limit)
    infeasible_score, breakdown = sim.evaluate_objective(infeasible, cfg, s.country.credit_limit)
    assert feasible.solvency_feasible
    assert not infeasible.solvency_feasible
    assert breakdown["reserve_required"] == 6000.0
    assert feasible_score > infeasible_score


def test_missing_weekly_expense_means_zero_reserve():
    d = _defs()
    s = _snap(weekly_expense=None)
    cfg = _cfg(objective="growth", solvency_buffer_weeks=12)
    m = em.build_price_model(s, d, share=0.25)
    fc = sim.simulate_plan(s, d, m, sim.Plan(), 40.0, 6, cfg=cfg)
    score, breakdown = sim.evaluate_objective(fc, cfg, s.country.credit_limit)
    assert fc.reserve_required == 0.0
    assert breakdown["reserve_required"] == 0.0
    assert isinstance(score, float)


# --- optimizer --------------------------------------------------------------

def _cfg(**over) -> OptimizeConfig:
    base = dict(horizon_months=24, objective="composite", search_effort=40, world_market_share=0.3)
    base.update(over)
    return OptimizeConfig(**base)


def test_optimizer_diversifies_under_feedback():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.3)
    res = opt.optimize_growth(s, d, m, _cfg(), capacity=40.0)
    # cascade-driven diversification: not all capacity into one building type
    assert len(res.added) >= 2
    # building steel raises iron/coal demand, so an input producer is picked too
    assert any(t in res.added for t in ("building_iron_mine", "building_coal_mine"))


def test_refinement_never_worse_than_unrefined():
    # Refinement is scored against the unrefined greedy plan on the *true*
    # objective, so neither search algorithm can do worse than no refinement.
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.3)

    def score(**over) -> float:
        cfg = _cfg(objective="growth", **over)
        res = opt.optimize_growth(s, d, m, cfg, capacity=40.0)
        fc = sim.simulate_plan(s, d, m, res.plan, 40.0, cfg.horizon_months, cfg=cfg, pace=True)
        return fc.annual_growth_rate

    baseline = score(search_effort=0)
    assert score(search_algo="greedy", search_effort=80) >= baseline - 1e-9
    assert score(search_algo="anneal", search_effort=80) >= baseline - 1e-9


def test_multi_objective_emits_pareto_frontier():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.3)
    res = opt.optimize_growth(s, d, m, _cfg(multi_objective=True), capacity=40.0)
    assert res.pareto  # at least one non-dominated plan
    assert all("growth_pct" in p and "min_headroom" in p for p in res.pareto)
    # Without the flag the frontier stays empty (no extra cost).
    res2 = opt.optimize_growth(s, d, m, _cfg(multi_objective=False), capacity=40.0)
    assert res2.pareto == []


def test_optimizer_respects_budget():
    d = _defs()
    s = _snap()
    m = em.build_price_model(s, d, share=0.3)
    cap = 40.0
    res = opt.optimize_growth(s, d, m, _cfg(), capacity=cap)
    cost_by_type = {o.building_type: o.cost_per_level for o in economic_build_options(s, d)}
    spent = sum(lv * cost_by_type[t] for t, lv in res.added.items())
    assert spent <= res.budget_points * 1.05  # within tolerance


def test_optimizer_beats_naive_single_good():
    d = _defs()
    s = _snap()
    cfg = _cfg()
    m = em.build_price_model(s, d, share=0.3)
    cap = 40.0
    res = opt.optimize_growth(s, d, m, cfg, capacity=cap)

    opt_fc = sim.simulate_plan(s, d, m, res.plan, cap, cfg.horizon_months)
    opt_score, _ = sim.evaluate_objective(opt_fc, cfg, s.country.credit_limit)

    # naive plan: pour the whole budget into steel mills only
    steel_cost = d.building_construction_cost("building_steel_mill")
    levels = int(res.budget_points / steel_cost)
    naive = sim.Plan(build_program=[sim.BuildStep("building_steel_mill", levels)])
    naive_fc = sim.simulate_plan(s, d, m, naive, cap, cfg.horizon_months)
    naive_score, _ = sim.evaluate_objective(naive_fc, cfg, s.country.credit_limit)

    assert opt_score >= naive_score


def test_optimizer_rejects_high_growth_construction_plan_that_breaches_reserve():
    d = _defs_with_construction()
    s = _snap(
        treasury=30000.0,
        weekly_income=5000.0,
        weekly_expense=2000.0,
        weekly_balance=0.0,
        credit_limit=0.0,
    )
    s.construction.points_per_week = 40.0
    s.construction.points_per_sector_level = 40.0
    cfg = _cfg(objective="growth", horizon_months=36, search_effort=40, solvency_buffer_weeks=12)
    m = em.build_price_model(s, d, share=0.3)

    aggressive = sim.Plan(
        build_program=[
            sim.BuildStep("building_construction_sector", 4),
            sim.BuildStep("building_iron_mine", 40),
            sim.BuildStep("building_coal_mine", 40),
            sim.BuildStep("building_steel_mill", 40),
            sim.BuildStep("building_tools_workshop", 40),
        ]
    )
    aggressive_fc = sim.simulate_plan(s, d, m, aggressive, 40.0, cfg.horizon_months, cfg=cfg)
    res = opt.optimize_growth(s, d, m, cfg, capacity=40.0)
    opt_fc = sim.simulate_plan(s, d, m, res.plan, 40.0, cfg.horizon_months, cfg=cfg)

    assert aggressive_fc.final_gdp > opt_fc.final_gdp
    assert not aggressive_fc.solvency_feasible
    assert opt_fc.solvency_feasible
    assert res.added.get("building_construction_sector", 0) == 0


# --- strategy report --------------------------------------------------------

def test_build_strategy_report_shape_and_jsonable():
    d = _defs()
    s = _snap()
    rep = build_strategy(s, d, _cfg(), history=None)
    assert rep.summary["optimized_gdp"] >= rep.summary["gdp0"]
    assert rep.summary["horizon_months"] == 24
    assert len(rep.series["months"]) == 24
    assert len(rep.series["optimized_gdp"]) == 24
    assert rep.build_order  # non-empty plan
    assert rep.cascade  # has a narrative
    # fully JSON-serializable for the API
    payload = json.dumps(_ser(rep))
    assert "summary" in payload and "build_order" in payload


def test_strategy_runs_from_snapshot_only():
    """The engine consumes only the player-visible Snapshot — no gamestate, so
    it structurally cannot read AI/other-country nodes."""
    d = _defs()
    s = _snap()
    rep = build_strategy(s, d, _cfg())
    # output is scoped to the player's own tag/economy
    assert rep.summary["gdp0"] == round(s.country.gdp)
    assert rep.assumptions["estimated"] is True
