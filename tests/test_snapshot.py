"""Adapter tests using a synthetic gamestate shaped like a real melted save.

These pin the adapter's contract and verify wiring: player resolution via
``player_manager``, state→building owner join, budget arrays/trends, GraphData
trends (gdp/sol/literacy), world-market price channels indexed by goods order,
the top-level ``technology`` manager, and ``pop_statistics``. Key names match a
melted Vic3 1.13 save (see SCHEMA.md).
"""

from vic3analyser.config import Config, Paths
from vic3analyser.extract.snapshot import build_snapshot
from vic3analyser.ingest.defs import GameDefs


def _defs() -> GameDefs:
    # Iteration order is the good's numeric id: 0=steel, 1=iron.
    return GameDefs(goods={"steel": {"cost": 70}, "iron": {"cost": 40}})


def _cfg(tag: str | None = "GBR") -> Config:
    return Config(
        paths=Paths(None, None, [], None, data_dir="."),
        player_tag=tag,
    )


def _graph(value: float) -> dict:
    """A minimal Vic3 GraphData block whose latest reading is ``value``."""
    return {"channels": {"0": {"date": "1836.1.1", "values": [value]}}}


def _gamestate() -> dict:
    return {
        "meta_data": {"version": "1.13.8", "game_date": "1836.2.1"},
        "date": "1836.2.1",
        "player_manager": {"database": {"0": {"user": "someone", "country": 1}}},
        "country_manager": {
            "database": {
                "1": {"definition": "GBR", "gdp": _graph(500.0),
                       "literacy": _graph(0.4), "avgsoltrend": _graph(9.5),
                       "budget": {"money": 10000.0, "credit": 50000.0,
                                   "weekly_income": [40.0, 60.0],
                                   "weekly_expenses": [50.0, 25.0],
                                   "balance_trend": {"current": 25.0}}},
                "2": {"definition": "FRA", "gdp": _graph(400.0)},
            }
        },
        # Per-market entries are just owners; prices live in world_market.
        "market_manager": {
            "world_market": {
                "price_trend": {"channels": {
                    "0": {"values": [84.0]},   # steel
                    "1": {"values": [36.0]},   # iron
                }}
            },
            "database": {"19": {"owner": 1}, "20": {"owner": 2}},
        },
        "building_manager": {
            "database": {
                "1000": {"building": "building_steel_mills", "state": 5, "levels": 3,
                          "production_methods": ["pm_basic_steel"],
                          "goods_sales": 50.0, "salary_rate": 20.0, "goods_cost": 10.0,
                          "cash_reserves": 25000.0},
                "1001": {"building": "building_barracks", "state": 6, "levels": 2},
            }
        },
        "technology": {
            "database": {
                "0": {"country": 1, "acquired_technologies": ["enclosure", "railways"]},
                "1": {"country": 2, "acquired_technologies": ["banking"]},
            }
        },
        "state_manager": {
            "database": {
                "5": {"country": 1, "region": "STATE_LONDON", "infrastructure": 100,
                       "infrastructure_usage": 60, "arable_land": 50,
                       "pop_statistics": {"population_lower_strata": 700000,
                                           "population_middle_strata": 250000,
                                           "population_upper_strata": 50000,
                                           "population_salaried_workforce": 200000}},
                "6": {"country": 2, "region": "STATE_PARIS"},
            }
        },
    }


def test_build_snapshot_basic():
    snap = build_snapshot(_gamestate(), _defs(), _cfg(), source="plaintext")
    assert snap.date == "1836.2.1"
    assert snap.player_tag == "GBR"
    assert snap.game_version == "1.13.8"  # from meta_data
    assert snap.country.gdp == 500.0  # latest GraphData reading
    assert snap.country.literacy == 0.4
    assert snap.country.avg_sol == 9.5
    assert snap.country.treasury == 10000.0
    assert snap.country.credit_limit == 50000.0
    assert snap.country.weekly_income == 100.0
    assert snap.country.weekly_expense == 75.0
    assert snap.country.weekly_balance == 25.0  # from balance_trend.current


def test_player_resolved_from_player_manager():
    # No configured tag: resolution must fall back to player_manager.
    snap = build_snapshot(_gamestate(), _defs(), _cfg(tag=None))
    assert snap.player_tag == "GBR"
    assert [b.building_type for b in snap.buildings] == ["building_steel_mills"]


def test_market_prices_from_world_market_by_good_order():
    snap = build_snapshot(_gamestate(), _defs(), _cfg())
    idx = snap.market_index()
    assert idx["steel"].price == 84.0
    assert idx["steel"].base_price == 70.0
    assert abs(idx["steel"].price_ratio - 84.0 / 70.0) < 1e-9
    assert idx["iron"].price == 36.0
    assert idx["iron"].base_price == 40.0


def test_only_player_owned_buildings_and_states():
    snap = build_snapshot(_gamestate(), _defs(), _cfg())
    assert [b.building_type for b in snap.buildings] == ["building_steel_mills"]
    # income=goods_sales(50), expense=salary(20)+goods_cost(10) -> profit 20.
    assert snap.buildings[0].weekly_income == 50.0
    assert snap.buildings[0].weekly_expense == 30.0
    assert snap.buildings[0].weekly_profit == 20.0
    assert snap.buildings[0].cash_reserves == 25000.0
    assert snap.buildings[0].active_pms[0].pm == "pm_basic_steel"
    assert [s.name for s in snap.states] == ["STATE_LONDON"]
    assert snap.states[0].infrastructure_free == 40.0
    assert snap.states[0].population == 1000000  # sum of strata
    assert snap.states[0].workforce == 200000


def test_tech_from_top_level_manager():
    snap = build_snapshot(_gamestate(), _defs(), _cfg())
    assert snap.tech.researched == ["enclosure", "railways"]
    assert snap.tech.has("railways")
