"""Phase 1 — production & price realism: throughput, economy of scale,
construction-frame tiers, endogenous demand, tradeable-aware pricing."""

from vic3analyser.config import OptimizeConfig
from vic3analyser.extract.models import (
    ActivePM,
    Building,
    ConstructionState,
    CountryEconomy,
    MarketGood,
    Snapshot,
    TechState,
)
from vic3analyser.ingest.defs import GameDefs
from vic3analyser.analysis.capacity import (
    best_construction_pm,
    construction_points_per_level,
    construction_pm_upgrade,
)
from vic3analyser.analysis.econ_model import build_price_model, demand_shift_for, pm_value_at
from vic3analyser.analysis.production import (
    building_throughput_bonus,
    economy_of_scale_bonus,
)

CFG = OptimizeConfig()


def _construction_defs() -> GameDefs:
    return GameDefs(
        goods={"wood": {"cost": 30}, "iron": {"cost": 40}},
        production_methods={
            "pm_wooden_buildings": {
                "country_modifiers": {"workforce_scaled": {"country_construction_add": 2}},
                "building_modifiers": {"workforce_scaled": {"goods_input_wood_add": 75}},
            },
            "pm_iron_frame_buildings": {
                "unlocking_technologies": ["urban_planning"],
                "country_modifiers": {"workforce_scaled": {"country_construction_add": 5}},
                "building_modifiers": {"workforce_scaled": {"goods_input_iron_add": 50}},
            },
        },
        production_method_groups={
            "pmg_cs": {"production_methods": ["pm_wooden_buildings", "pm_iron_frame_buildings"]}
        },
        building_types={
            "building_construction_sector": {"production_method_groups": ["pmg_cs"]}
        },
    )


def _cs_snap(researched) -> Snapshot:
    return Snapshot(
        date="1836.1.1",
        player_tag="SAR",
        country=CountryEconomy(tag="SAR"),
        buildings=[
            Building(
                id=1,
                building_type="building_construction_sector",
                level=10,
                active_pms=[ActivePM(group="pmg_cs", pm="pm_wooden_buildings")],
            )
        ],
        tech=TechState(researched=researched),
        construction=ConstructionState(points_per_sector_level=12.0),
    )


def test_construction_frame_upgrade_scales_points():
    d = _construction_defs()
    # iron frame unresearched -> stay on wooden, no upgrade.
    cur, best, mult = construction_pm_upgrade(_cs_snap([]), d, set(), CFG)
    assert best == "pm_wooden_buildings" and mult == 1.0

    # iron frame researched -> best frame is iron (5 vs 2 pts), 2.5x points.
    researched = {"urban_planning"}
    assert best_construction_pm(researched, d) == "pm_iron_frame_buildings"
    cur, best, mult = construction_pm_upgrade(_cs_snap(["urban_planning"]), d, researched, CFG)
    assert cur == "pm_wooden_buildings" and best == "pm_iron_frame_buildings"
    assert mult == 2.5
    # observed 12 pts/level scales to 30 with the better frame.
    assert construction_points_per_level(_cs_snap(["urban_planning"]), d, researched, CFG) == 30.0


def test_construction_pm_feature_flag_off_keeps_observed():
    d = _construction_defs()
    cfg = OptimizeConfig(model_construction_pm=False)
    snap = _cs_snap(["urban_planning"])
    assert construction_points_per_level(snap, d, {"urban_planning"}, cfg) == 12.0


def _eos_defs() -> GameDefs:
    return GameDefs(
        building_groups={
            "bg_manufacturing": {"economy_of_scale": "yes"},
            "bg_subsistence_agriculture": {"is_subsistence": "yes", "parent_group": "bg_manufacturing"},
        },
        building_types={
            "building_steel_mills": {"building_group": "bg_manufacturing"},
            "building_subsistence_farm": {"building_group": "bg_subsistence_agriculture"},
        },
        defines={"NEconomy": {"ECONOMY_OF_SCALE_START_LEVEL": 1}},
    )


def test_economy_of_scale_only_for_eos_groups():
    d = _eos_defs()
    # +1% throughput per level above the start level (1).
    assert economy_of_scale_bonus("building_steel_mills", 10, d, CFG) == 0.09
    # Capped at the scale cap (20 levels): never grows past +19%.
    assert economy_of_scale_bonus("building_steel_mills", 100, d, CFG) == 0.19
    # Subsistence is excluded even though it inherits the flag.
    assert economy_of_scale_bonus("building_subsistence_farm", 50, d, CFG) == 0.0
    # Disabled by config.
    off = OptimizeConfig(model_economy_of_scale=False)
    assert economy_of_scale_bonus("building_steel_mills", 10, d, off) == 0.0


def _tech_throughput_defs() -> GameDefs:
    return GameDefs(
        goods={"steel": {"cost": 70}, "iron": {"cost": 40}},
        production_methods={
            "pm_steel": {
                "building_modifiers": {
                    "workforce_scaled": {"goods_input_iron_add": 30, "goods_output_steel_add": 25}
                }
            }
        },
        building_types={"building_steel_mills": {"building_group": "bg_heavy_industry"}},
        building_groups={"bg_heavy_industry": {}},
        technologies={
            "pig_iron": {"modifier": {"building_group_bg_heavy_industry_throughput_add": 0.2}}
        },
    )


def test_tech_throughput_scales_value():
    d = _tech_throughput_defs()
    prices = {"steel": 70.0, "iron": 40.0}
    base = pm_value_at("pm_steel", prices, d)  # 25*70 - 30*40 = 550
    assert base == 550.0
    # +20% throughput from the researched tech scales value-added by 1.2.
    bonus = building_throughput_bonus("building_steel_mills", 1, {"pig_iron"}, [], d, CFG)
    assert bonus == 0.2
    assert round(pm_value_at("pm_steel", prices, d, bonus), 2) == round(550.0 * 1.2, 2)
    # Unresearched -> no bonus.
    assert building_throughput_bonus("building_steel_mills", 1, set(), [], d, CFG) == 0.0


def test_demand_shift_raises_consumer_goods():
    d = GameDefs(
        goods={
            "grain": {"cost": 30, "category": "staple"},
            "iron": {"cost": 40, "category": "industrial"},
        }
    )
    snap = Snapshot(
        date="1836.1.1",
        player_tag="SAR",
        country=CountryEconomy(tag="SAR"),
        market=[
            MarketGood(good="grain", price=30, base_price=30, category="staple"),
            MarketGood(good="iron", price=40, base_price=40, category="industrial"),
        ],
    )
    model = build_price_model(snap, d)
    shift = demand_shift_for(0.5, model, d, elasticity=0.5)
    assert shift.get("grain", 0) > 0  # staple demand rises with growth
    assert "iron" not in shift  # industrial good unaffected
