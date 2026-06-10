from pathlib import Path

from vic3analyser.config import Config, Paths
from vic3analyser.ingest.defs import load_defs


def _make_install(tmp_path: Path) -> Path:
    common = tmp_path / "game" / "common"
    (common / "goods").mkdir(parents=True)
    (common / "production_methods").mkdir(parents=True)
    (common / "production_method_groups").mkdir(parents=True)
    (common / "buildings").mkdir(parents=True)
    (common / "technology" / "technologies").mkdir(parents=True)

    (common / "goods" / "00_goods.txt").write_text(
        """
        iron = { cost = 40 category = industrial }
        steel = { cost = 70 category = industrial }
        """
    )
    (common / "production_methods" / "01_steel.txt").write_text(
        """
        pm_basic_steel = {
            unlocking_technologies = { pig_iron }
            building_modifiers = {
                workforce_scaled = {
                    goods_input_iron_add = 30
                    goods_output_steel_add = 25
                }
            }
        }
        pm_automated_steel = {
            unlocking_technologies = { steam_donkey }
            building_modifiers = {
                workforce_scaled = {
                    goods_input_iron_add = 40
                    goods_output_steel_add = 45
                }
            }
        }
        """
    )
    (common / "production_method_groups" / "01.txt").write_text(
        """
        pmg_base_building_steel_mills = {
            production_methods = { pm_basic_steel pm_automated_steel }
        }
        """
    )
    (common / "buildings" / "01.txt").write_text(
        """
        building_steel_mills = {
            production_method_groups = { pmg_base_building_steel_mills }
        }
        """
    )
    (common / "technology" / "technologies" / "01.txt").write_text(
        "steam_donkey = { era = era_2 }\npig_iron = { era = era_1 }"
    )
    return tmp_path


def _cfg(install: Path, data_dir: Path) -> Config:
    return Config(
        paths=Paths(
            vic3_install=install,
            save_dir=None,
            mod_dirs=[],
            rakaly_bin=None,
            data_dir=data_dir,
        ),
        player_tag=None,
    )


def test_load_defs_and_helpers(tmp_path):
    install = _make_install(tmp_path)
    cfg = _cfg(install, tmp_path / "data")
    defs = load_defs(cfg, use_cache=False)

    assert defs.good_base_price("iron") == 40
    assert defs.good_base_price("steel") == 70

    flows = defs.pm_goods("pm_automated_steel")
    assert flows["input"] == {"iron": 40.0}
    assert flows["output"] == {"steel": 45.0}

    assert defs.pm_unlocking_techs("pm_automated_steel") == ["steam_donkey"]
    assert defs.building_pm_groups("building_steel_mills") == [
        "pmg_base_building_steel_mills"
    ]
    assert defs.group_pms("pmg_base_building_steel_mills") == [
        "pm_basic_steel",
        "pm_automated_steel",
    ]


def test_defs_cache_roundtrip(tmp_path):
    install = _make_install(tmp_path)
    cfg = _cfg(install, tmp_path / "data")
    first = load_defs(cfg, use_cache=True)
    assert (cfg.paths.data_dir / "defs_cache.json").exists()
    # Second load should hit the cache and produce identical content.
    second = load_defs(cfg, use_cache=True)
    assert second.goods == first.goods
    assert second.production_methods == first.production_methods


def test_mod_overlay_overrides(tmp_path):
    install = _make_install(tmp_path)
    mod = tmp_path / "mymod"
    (mod / "common" / "goods").mkdir(parents=True)
    (mod / "common" / "goods" / "zz_override.txt").write_text(
        "iron = { cost = 99 category = industrial }"
    )
    cfg = Config(
        paths=Paths(
            vic3_install=install,
            save_dir=None,
            mod_dirs=[mod],
            rakaly_bin=None,
            data_dir=tmp_path / "data",
        ),
        player_tag=None,
    )
    defs = load_defs(cfg, use_cache=False)
    assert defs.good_base_price("iron") == 99
