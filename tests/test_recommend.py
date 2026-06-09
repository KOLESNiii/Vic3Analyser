from vic3analyser.analysis.recommend import build_recommendations
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
        goods={"iron": {"cost": 40}, "steel": {"cost": 70}},
        production_methods={
            "pm_basic_steel": {
                "unlocking_technologies": [],
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
                        "goods_output_steel_add": 50,
                    }
                },
            },
        },
        production_method_groups={
            "pmg_steel": {"production_methods": ["pm_basic_steel", "pm_automated_steel"]},
        },
        building_types={"building_steel_mills": {"production_method_groups": ["pmg_steel"]}},
    )


def _snap() -> Snapshot:
    return Snapshot(
        date="1836.4.1",
        player_tag="GBR",
        country=CountryEconomy(tag="GBR"),
        market=[
            MarketGood(good="iron", price=40.0, base_price=40.0),
            MarketGood(good="steel", price=90.0, base_price=70.0),
        ],
        buildings=[
            Building(id=1, building_type="building_steel_mills", level=5,
                     active_pms=[ActivePM(pm="pm_basic_steel")])
        ],
        tech=TechState(researched=["steam_donkey"]),
    )


def test_recommendations_include_categories_and_rank():
    recs = build_recommendations(_snap(), _defs())
    assert recs, "expected recommendations"
    cats = {r.category for r in recs}
    # PM switch (automation now profitable), a build suggestion, market shortage
    assert "pm" in cats
    assert "market" in cats
    # sorted by impact descending
    impacts = [r.impact for r in recs]
    assert impacts == sorted(impacts, reverse=True)
    # the top PM rec mentions the automated switch
    pm_recs = [r for r in recs if r.category == "pm"]
    assert any("pm_automated_steel" in r.title for r in pm_recs)
