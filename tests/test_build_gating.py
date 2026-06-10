"""Buildings/goods the player can't act on must not be recommended.

Regression tests for two fixes:
* ``build_what`` gates on the building's own ``unlocking_technologies`` (not just
  its PMs'), so unbuildable buildings aren't suggested;
* market shortages in goods nobody can produce yet are classed ``locked`` and
  excluded from the actionable shortage list (the "aeroplanes in 1836" noise).
"""

from vic3analyser.analysis.build_what import analyse_what_to_build, producible_goods
from vic3analyser.analysis.market import analyse_market
from vic3analyser.extract.models import (
    CountryEconomy,
    MarketGood,
    Snapshot,
    TechState,
)
from vic3analyser.ingest.defs import GameDefs


def _defs() -> GameDefs:
    return GameDefs(
        goods={"grain": {"cost": 20}, "aeroplanes": {"cost": 80}},
        production_methods={
            "pm_farm": {  # no tech needed
                "building_modifiers": {
                    "workforce_scaled": {"goods_output_grain_add": 20}
                },
            },
            "pm_assembly": {  # needs flight tech
                "unlocking_technologies": ["flight"],
                "building_modifiers": {
                    "workforce_scaled": {"goods_output_aeroplanes_add": 10}
                },
            },
        },
        production_method_groups={
            "pmg_farm": {"production_methods": ["pm_farm"]},
            "pmg_air": {"production_methods": ["pm_assembly"]},
        },
        building_types={
            "building_wheat_farm": {"production_method_groups": ["pmg_farm"]},
            "building_aerodrome": {
                "production_method_groups": ["pmg_air"],
                "unlocking_technologies": ["flight"],
            },
        },
    )


def _snap() -> Snapshot:
    return Snapshot(
        date="1836.2.1",
        player_tag="GBR",
        country=CountryEconomy(tag="GBR"),
        market=[
            MarketGood(good="grain", price=30.0, base_price=20.0),       # shortage
            MarketGood(good="aeroplanes", price=140.0, base_price=80.0),  # ceiling
        ],
        tech=TechState(researched=[]),  # flight NOT researched
    )


def test_unbuildable_building_excluded_from_build_what():
    candidates = analyse_what_to_build(_snap(), _defs())
    names = [c.building_type for c in candidates]
    assert "building_wheat_farm" in names      # buildable, no tech needed
    assert "building_aerodrome" not in names   # needs flight -> excluded


def test_producible_goods_excludes_locked():
    prod = producible_goods(_snap(), _defs())
    assert "grain" in prod
    assert "aeroplanes" not in prod


def test_locked_good_not_an_actionable_shortage():
    snap = _snap()
    report = analyse_market(snap, producible_goods(snap, _defs()))
    by = {g.good: g for g in report.goods}
    assert by["grain"].status == "shortage"
    assert by["aeroplanes"].status == "locked"
    # The actionable shortage list must not include the locked good.
    assert "aeroplanes" not in [g.good for g in report.shortages]
