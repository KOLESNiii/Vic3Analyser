from vic3analyser.analysis.build_what import analyse_what_to_build
from vic3analyser.analysis.build_where import analyse_where_to_build
from vic3analyser.analysis.construction import analyse_construction
from vic3analyser.analysis.tech import analyse_tech_priorities
from vic3analyser.extract.models import (
    ActivePM,
    Building,
    ConstructionItem,
    ConstructionState,
    CountryEconomy,
    MarketGood,
    Snapshot,
    StateInfo,
    TechState,
)
from vic3analyser.ingest.defs import GameDefs


def _defs() -> GameDefs:
    return GameDefs(
        goods={"iron": {"cost": 40}, "steel": {"cost": 70}, "tools": {"cost": 50}},
        production_methods={
            "pm_iron_basic": {
                "unlocking_technologies": [],
                "building_modifiers": {
                    "workforce_scaled": {"goods_output_iron_add": 20}
                },
            },
            "pm_tools_basic": {
                "unlocking_technologies": [],
                "building_modifiers": {
                    "workforce_scaled": {
                        "goods_input_iron_add": 10,
                        "goods_output_tools_add": 20,
                    }
                },
            },
            "pm_tools_adv": {
                "unlocking_technologies": ["machine_tools"],
                "building_modifiers": {
                    "workforce_scaled": {
                        "goods_input_iron_add": 15,
                        "goods_output_tools_add": 40,
                    }
                },
            },
        },
        production_method_groups={
            "pmg_iron": {"production_methods": ["pm_iron_basic"]},
            "pmg_tools": {"production_methods": ["pm_tools_basic", "pm_tools_adv"]},
        },
        building_types={
            "building_iron_mine": {"production_method_groups": ["pmg_iron"]},
            "building_tooling_workshops": {"production_method_groups": ["pmg_tools"]},
        },
    )


def _market(tools_price=50.0):
    return [
        MarketGood(good="iron", price=40.0, base_price=40.0),
        MarketGood(good="steel", price=70.0, base_price=70.0),
        MarketGood(good="tools", price=tools_price, base_price=50.0),
    ]


def _snap(researched=None, states=None, construction=None, buildings=None, tools_price=50.0):
    return Snapshot(
        date="1836.3.1",
        player_tag="GBR",
        country=CountryEconomy(tag="GBR"),
        market=_market(tools_price),
        buildings=buildings or [],
        states=states or [],
        tech=TechState(researched=researched or []),
        construction=construction or ConstructionState(),
    )


def test_what_to_build_ranks_and_filters():
    cands = analyse_what_to_build(_snap(), _defs())
    types = [c.building_type for c in cands]
    # both produce priced goods, so both appear
    assert set(types) == {"building_iron_mine", "building_tooling_workshops"}
    # tooling: 20*50 - 10*40 = 600 ; iron mine: 20*40 = 800 -> iron ranks first
    by_type = {c.building_type: c for c in cands}
    assert by_type["building_iron_mine"].raw_value_added == 800.0
    assert by_type["building_tooling_workshops"].raw_value_added == 600.0


def test_what_to_build_demand_weighting():
    # raise tools price -> tools outputs in shortage -> score boosted
    cands = analyse_what_to_build(_snap(tools_price=90.0), _defs())
    by_type = {c.building_type: c for c in cands}
    tools = by_type["building_tooling_workshops"]
    assert tools.output_shortage > 0.1
    assert tools.score > tools.raw_value_added  # demand bonus applied


def test_where_to_build_ranking():
    states = [
        StateInfo(id=1, name="A", infrastructure=100, infrastructure_used=90, unemployment=100),
        StateInfo(id=2, name="B", infrastructure=100, infrastructure_used=10, unemployment=5000),
    ]
    ranked = analyse_where_to_build(_snap(states=states))
    assert ranked[0].name == "B"  # more free infra + more idle labour
    assert ranked[0].score > ranked[1].score


def test_construction_payback_and_suggestions():
    queue = [ConstructionItem(building_type="building_iron_mine", levels=1, remaining_cost=8000.0)]
    snap = _snap(construction=ConstructionState(points_per_week=50.0, queue=queue))
    report = analyse_construction(snap, _defs())
    item = report.queue[0]
    # est weekly profit = 800 (per level) * 1 ; payback = 8000/800 = 10 weeks
    assert item.est_weekly_profit == 800.0
    assert item.payback_weeks == 10.0
    # tooling not queued -> suggested
    assert "building_tooling_workshops" in report.suggested_additions
    assert "building_iron_mine" not in report.suggested_additions


def test_tech_priorities_uplift():
    # player operates a tooling workshop; machine_tools unlocks pm_tools_adv
    buildings = [
        Building(id=1, building_type="building_tooling_workshops", level=3,
                 active_pms=[ActivePM(pm="pm_tools_basic")])
    ]
    snap = _snap(buildings=buildings)
    prios = analyse_tech_priorities(snap, _defs())
    assert prios and prios[0].tech == "machine_tools"
    # adv value: 40*50 - 15*40 = 1400 ; basic: 20*50 - 10*40 = 600 ; gain 800 * 3 levels
    assert prios[0].potential_uplift == 800.0 * 3
    assert "building_tooling_workshops:pm_tools_adv" in prios[0].unlocks
