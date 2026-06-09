from vic3analyser.analysis.market import analyse_market
from vic3analyser.analysis.pm_optimizer import analyse_pm_switches
from vic3analyser.analysis.profitability import analyse_profitability
from vic3analyser.extract.models import (
    ActivePM,
    Building,
    CountryEconomy,
    MarketGood,
    Snapshot,
    TechState,
)
from vic3analyser.ingest.defs import GameDefs


def _defs() -> GameDefs:
    return GameDefs(
        goods={"iron": {"cost": 40}, "steel": {"cost": 70}, "coal": {"cost": 30}},
        production_methods={
            "pm_basic_steel": {
                "unlocking_technologies": ["pig_iron"],
                "building_modifiers": {
                    "workforce_scaled": {
                        "goods_input_iron_add": 30,
                        "goods_output_steel_add": 25,
                    }
                },
            },
            "pm_automated_steel": {
                "unlocking_technologies": ["steam_donkey"],
                "building_modifiers": {
                    "workforce_scaled": {
                        "goods_input_iron_add": 40,
                        "goods_input_coal_add": 10,
                        "goods_output_steel_add": 50,
                    }
                },
            },
        },
        production_method_groups={
            "pmg_steel": {"production_methods": ["pm_basic_steel", "pm_automated_steel"]},
        },
        building_types={
            "building_steel_mills": {"production_method_groups": ["pmg_steel"]},
        },
    )


def _snap(researched, market_steel=80.0) -> Snapshot:
    return Snapshot(
        date="1836.2.1",
        player_tag="GBR",
        country=CountryEconomy(tag="GBR"),
        market=[
            MarketGood(good="iron", price=40.0, base_price=40.0),
            MarketGood(good="steel", price=market_steel, base_price=70.0),
            MarketGood(good="coal", price=30.0, base_price=30.0),
        ],
        buildings=[
            Building(
                id=1,
                building_type="building_steel_mills",
                state_id=5,
                level=4,
                active_pms=[ActivePM(group="pmg_steel", pm="pm_basic_steel")],
            )
        ],
        tech=TechState(researched=researched),
    )


def test_market_shortage_detection():
    snap = _snap(["pig_iron"], market_steel=84.0)
    report = analyse_market(snap)
    steel = next(g for g in report.goods if g.good == "steel")
    assert steel.status == "shortage"
    assert report.shortages and report.shortages[0].good == "steel"


def test_pm_switch_recommended_when_tech_available():
    # automated steel unlocked; at these prices it should beat basic.
    snap = _snap(["pig_iron", "steam_donkey"], market_steel=80.0)
    recs = analyse_pm_switches(snap, _defs())
    assert len(recs) == 1
    rec = recs[0]
    assert rec.current_pm == "pm_basic_steel"
    assert rec.best_pm == "pm_automated_steel"
    # basic value-added: 25*80 - 30*40 = 800
    # auto value-added : 50*80 - 40*40 - 10*30 = 2100
    assert rec.current_value == 800.0
    assert rec.best_value == 2100.0
    assert rec.delta_per_level == 1300.0
    assert rec.delta_total == 1300.0 * 4


def test_pm_switch_not_recommended_when_tech_locked():
    # automated steel NOT unlocked -> no switch suggested.
    snap = _snap(["pig_iron"], market_steel=80.0)
    recs = analyse_pm_switches(snap, _defs())
    assert recs == []


def test_pm_switch_not_recommended_when_current_is_best():
    # cheap steel price makes higher-throughput automation worse? Here automation
    # still wins on these numbers, so instead test: low steel price flips it.
    snap = _snap(["pig_iron", "steam_donkey"], market_steel=20.0)
    # basic: 25*20 - 1200 = -700 ; auto: 50*20 - 1600 - 300 = -900 -> basic better
    recs = analyse_pm_switches(snap, _defs())
    assert recs == []


def test_profitability_uses_real_figures_when_present():
    snap = _snap(["pig_iron"])
    snap.buildings[0].weekly_income = 100.0
    snap.buildings[0].weekly_expense = 60.0
    ranked = analyse_profitability(snap, _defs())
    assert ranked[0].weekly_profit == 40.0
    assert ranked[0].estimated is False
    assert ranked[0].per_level_profit == 10.0


def test_profitability_estimates_when_figures_absent():
    snap = _snap(["pig_iron"])  # no weekly_income/expense set
    ranked = analyse_profitability(snap, _defs())
    # basic value-added 800 * level 4 = 3200
    assert ranked[0].estimated is True
    assert ranked[0].weekly_profit == 3200.0
