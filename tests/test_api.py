"""End-to-end API test: synthetic install + crafted plaintext save through the
full pipeline and out the HTTP endpoints. No real game data required.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from vic3analyser.api.server import create_app
from vic3analyser.config import Config, Paths

GAMESTATE = """
date = 1836.2.1
version = "1.7"
country_manager = {
    database = {
        1 = { definition = "GBR" gdp = 500.0 budget = { money = 10000.0 weekly_net = 25.0 } }
    }
}
market_manager = {
    database = {
        10 = { goods_data = {
            100 = { goods = steel price = 90.0 }
            101 = { goods = iron price = 40.0 }
        } }
    }
}
building_manager = {
    database = {
        1000 = { building_type = building_steel_mills country = 1 state = 5 level = 4
                 production_methods = { pm_basic_steel } }
    }
}
state_manager = {
    database = {
        5 = { country = 1 name = STATE_LONDON infrastructure = 100 infrastructure_usage = 40 }
    }
}
"""


def _make_install(tmp_path: Path) -> Path:
    common = tmp_path / "game" / "common"
    for sub in ("goods", "production_methods", "production_method_groups", "building_types"):
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
    (common / "building_types" / "b.txt").write_text(
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
