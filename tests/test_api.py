"""End-to-end API test: synthetic install + crafted plaintext save through the
full pipeline and out the HTTP endpoints. No real game data required.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from vic3analyser.api.server import create_app
from vic3analyser.config import Config, Paths

GAMESTATE = """
meta_data = { version = "1.13.8" game_date = 1836.2.1 }
date = 1836.2.1
player_manager = { database = { 0 = { country = 1 } } }
country_manager = {
    database = {
        1 = { definition = "GBR"
              gdp = { channels = { 0 = { values = { 500.0 } } } }
              budget = { money = 10000.0
                         weekly_income = { 60.0 40.0 }
                         weekly_expenses = { 50.0 25.0 }
                         balance_trend = { current = 25.0 } } }
    }
}
market_manager = {
    world_market = { price_trend = { channels = {
        0 = { values = { 40.0 } }
        1 = { values = { 90.0 } }
    } } }
    database = { 19 = { owner = 1 } }
}
building_manager = {
    database = {
        1000 = { building = building_steel_mills state = 5 levels = 4
                 production_methods = { pm_basic_steel }
                 goods_sales = 50.0 salary_rate = 20.0 goods_cost = 10.0 }
    }
}
technology = {
    database = { 0 = { country = 1 acquired_technologies = { enclosure } } }
}
state_manager = {
    database = {
        5 = { country = 1 region = STATE_LONDON infrastructure = 100 infrastructure_usage = 40
              pop_statistics = { population_lower_strata = 700000
                                 population_middle_strata = 250000
                                 population_upper_strata = 50000
                                 population_salaried_workforce = 200000 } }
    }
}
"""


def _make_install(tmp_path: Path) -> Path:
    common = tmp_path / "game" / "common"
    for sub in ("goods", "production_methods", "production_method_groups", "buildings"):
        (common / sub).mkdir(parents=True)
    (common / "technology" / "technologies").mkdir(parents=True)
    (common / "goods" / "g.txt").write_text("iron = { cost = 40 }\nsteel = { cost = 70 }")
    (common / "production_methods" / "p.txt").write_text(
        """
        pm_basic_steel = { unlocking_technologies = {}
            building_modifiers = { workforce_scaled = {
                goods_input_iron_add = 30 goods_output_steel_add = 25 } } }
        pm_automated_steel = { unlocking_technologies = { steam_donkey }
            building_modifiers = { workforce_scaled = {
                goods_input_iron_add = 40 goods_output_steel_add = 50 } } }
        """
    )
    (common / "production_method_groups" / "g.txt").write_text(
        "pmg_steel = { production_methods = { pm_basic_steel pm_automated_steel } }"
    )
    (common / "buildings" / "b.txt").write_text(
        "building_steel_mills = { production_method_groups = { pmg_steel } }"
    )
    return tmp_path


def _cfg(tmp_path: Path) -> Config:
    return Config(
        paths=Paths(
            vic3_install=_make_install(tmp_path),
            save_dir=None,
            mod_dirs=[],
            rakaly_bin=None,
            data_dir=tmp_path / "data",
        ),
        player_tag="GBR",
    )


def test_full_api_flow(tmp_path):
    save = tmp_path / "test.v3"
    save.write_text(GAMESTATE)
    app = create_app(_cfg(tmp_path))

    with TestClient(app) as client:
        status = client.get("/api/status").json()
        assert status["defs_loaded"] is True

        ing = client.post("/api/ingest", params={"path": str(save)})
        assert ing.status_code == 200, ing.text
        assert ing.json()["ingested"] == "1836.2.1"

        data = client.get("/api/analysis").json()
        assert data["player_tag"] == "GBR"
        assert data["country"]["gdp"] == 500.0

        # steel is above base price -> flagged as a shortage
        shortages = [g["good"] for g in data["market"]["shortages"]]
        assert "steel" in shortages

        # automation tech not researched in this save -> no PM switch yet,
        # but build + recommendations should be populated.
        assert any(c["building_type"] == "building_steel_mills" for c in data["build_what"])
        assert isinstance(data["recommendations"], list) and data["recommendations"]

        series = client.get("/api/series", params={"player_tag": "GBR"}).json()
        assert series and series[0]["gdp"] == 500.0


def test_on_demand_analysis(tmp_path):
    """Settings/saves endpoints: list saves and analyse the latest on demand."""
    cfg = _cfg(tmp_path)
    save_dir = tmp_path / "saves"
    save_dir.mkdir()
    cfg.paths.save_dir = save_dir
    cfg.auto_watch = False  # on-demand only; watcher must not auto-ingest

    (save_dir / "autosave.v3").write_text(GAMESTATE)
    latest = save_dir / "manual.v3"
    latest.write_text(GAMESTATE.replace("1836.2.1", "1840.5.1"))

    app = create_app(cfg)
    with TestClient(app) as client:
        status = client.get("/api/status").json()
        assert status["auto_watch"] is False
        assert status["watching"] is False
        assert status["last_ingest"] is None  # nothing ingested automatically

        saves = client.get("/api/saves").json()
        assert [s["name"] for s in saves] == ["manual.v3", "autosave.v3"]
        assert saves[1]["is_autosave"] is True

        # latest of any kind is the manual save ...
        res = client.post("/api/analyse-latest")
        assert res.status_code == 200, res.text
        assert res.json()["ingested"] == "1840.5.1"

        # ... but autosave_only picks the older autosave instead.
        res = client.post("/api/analyse-latest", params={"autosave_only": True})
        assert res.status_code == 200, res.text
        assert res.json()["ingested"] == "1836.2.1"

        # default watch mode is "any"; switch it to autosaves only
        assert status["watch_mode"] == "any"
        out = client.post("/api/settings", params={"watch_mode": "autosave"}).json()
        assert out["watch_mode"] == "autosave"

        # toggling auto_watch on starts the watcher (with the new mode)
        out = client.post("/api/settings", params={"auto_watch": True}).json()
        assert out["auto_watch"] is True and out["watching"] is True
        assert out["watch_mode"] == "autosave"
