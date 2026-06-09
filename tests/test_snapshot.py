"""Adapter tests using a synthetic gamestate shaped per SCHEMA.md assumptions.

These pin the adapter's contract and verify wiring (player resolution, owner
filtering, market/defs join). Real key names are confirmed against a melted
save in Phase 2; when they change, only the candidate-key lists in
``extract/snapshot.py`` move, and these fixtures update alongside.
"""

from vic3analyser.config import Config, Paths
from vic3analyser.extract.snapshot import build_snapshot
from vic3analyser.ingest.defs import GameDefs


def _defs() -> GameDefs:
    return GameDefs(goods={"steel": {"cost": 70}, "iron": {"cost": 40}})


def _cfg(tag: str | None = "GBR") -> Config:
    return Config(
        paths=Paths(None, None, [], None, data_dir="."),
        player_tag=tag,
    )


def _gamestate() -> dict:
    return {
        "date": "1836.2.1",
        "version": "1.7.3",
        "country_manager": {
            "database": {
                "1": {"definition": "GBR", "gdp": 500.0,
                       "budget": {"money": 10000.0, "weekly_net": 25.0}},
                "2": {"definition": "FRA", "gdp": 400.0},
            }
        },
        "market_manager": {
            "database": {
                "10": {
                    "goods_data": {
                        "100": {"goods": "steel", "price": 84.0, "supply": 100, "demand": 130},
                        "101": {"goods": "iron", "price": 36.0},
                    }
                }
            }
        },
        "building_manager": {
            "database": {
                "1000": {"building_type": "building_steel_mills", "country": 1,
                          "state": 5, "level": 3, "production_methods": ["pm_basic_steel"],
                          "income": 50.0, "expense": 30.0},
                "1001": {"building_type": "building_barracks", "country": 2, "level": 2},
            }
        },
        "state_manager": {
            "database": {
                "5": {"country": 1, "name": "STATE_LONDON", "infrastructure": 100,
                       "infrastructure_usage": 60, "unemployment": 1200},
                "6": {"country": 2, "name": "STATE_PARIS"},
            }
        },
    }


def test_build_snapshot_basic():
    snap = build_snapshot(_gamestate(), _defs(), _cfg(), source="plaintext")
    assert snap.date == "1836.2.1"
    assert snap.player_tag == "GBR"
    assert snap.game_version == "1.7.3"
    assert snap.country.gdp == 500.0
    assert snap.country.treasury == 10000.0
    assert snap.country.weekly_balance == 25.0


def test_market_joins_base_price():
    snap = build_snapshot(_gamestate(), _defs(), _cfg())
    idx = snap.market_index()
    assert idx["steel"].price == 84.0
    assert idx["steel"].base_price == 70.0
    assert abs(idx["steel"].price_ratio - 84.0 / 70.0) < 1e-9
    assert idx["iron"].base_price == 40.0


def test_only_player_owned_buildings_and_states():
    snap = build_snapshot(_gamestate(), _defs(), _cfg())
    assert [b.building_type for b in snap.buildings] == ["building_steel_mills"]
    assert snap.buildings[0].weekly_profit == 20.0
    assert snap.buildings[0].active_pms[0].pm == "pm_basic_steel"
    assert [s.name for s in snap.states] == ["STATE_LONDON"]
    assert snap.states[0].infrastructure_free == 40.0
