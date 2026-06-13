"""Phase 2 — government & taxation: bureaucracy penalty, tax-capacity throttle,
admin capacity, law multipliers."""

from vic3analyser.extract.models import (
    ActivePM,
    Building,
    CountryEconomy,
    Snapshot,
    StateInfo,
    TechState,
)
from vic3analyser.ingest.defs import GameDefs
from vic3analyser.analysis.fiscal import (
    ADMIN_BUILDING,
    GovCapacity,
    admin_capacity_per_level,
    gov_capacity,
    tax_capacity_law_mult,
    tax_capture_factor,
)


def _admin_defs() -> GameDefs:
    return GameDefs(
        production_methods={
            "pm_horizontal_drawer_cabinets": {
                "country_modifiers": {"workforce_scaled": {"country_bureaucracy_add": 50}},
                "state_modifiers": {"workforce_scaled": {"state_tax_capacity_add": 10}},
            }
        },
        production_method_groups={"pmg_admin": {"production_methods": ["pm_horizontal_drawer_cabinets"]}},
        building_types={ADMIN_BUILDING: {"production_method_groups": ["pmg_admin"]}},
        laws={
            "law_traditionalism": {
                "group": "lawgroup_economic_system",
                "modifier": {"state_tax_capacity_mult": -0.25},
            }
        },
    )


def test_admin_capacity_per_level():
    d = _admin_defs()
    bur, tax = admin_capacity_per_level(set(), {}, d)
    assert bur == 50.0 and tax == 10.0


def test_bureaucracy_penalty_only_on_deficit():
    assert GovCapacity(300, 100, 60).bureaucracy_penalty == 0.0  # surplus
    # Deficit of 50 on demand 100 -> 0.5 frac * 0.5 gain = 0.25 penalty.
    assert GovCapacity(50, 100, 60).bureaucracy_penalty == 0.25
    # Penalty is capped (never wipes the whole economy).
    assert GovCapacity(0, 100, 60).bureaucracy_penalty <= 0.30


def test_tax_capacity_law_mult():
    d = _admin_defs()
    assert tax_capacity_law_mult([], d) == 1.0
    assert tax_capacity_law_mult(["law_traditionalism"], d) == 0.75


def test_tax_capture_throttles_when_gdp_outgrows_capacity():
    # Capacity unchanged, GDP doubled -> only half the growth-tax is collectable.
    gov = GovCapacity(300, 100, 60)
    assert tax_capture_factor(gov, gdp=200.0, gdp0=100.0, base_tax_capacity=60.0) == 0.5
    # Capacity doubled in step with GDP -> fully collected.
    gov2 = GovCapacity(300, 100, 120)
    assert tax_capture_factor(gov2, gdp=200.0, gdp0=100.0, base_tax_capacity=60.0) == 1.0


def test_gov_capacity_scales_demand_with_size():
    d = _admin_defs()
    snap = Snapshot(
        date="1836.1.1",
        player_tag="SAR",
        country=CountryEconomy(tag="SAR"),
        states=[StateInfo(id=1, bureaucracy_cost=100.0)],
        buildings=[
            Building(
                id=1,
                building_type=ADMIN_BUILDING,
                level=4,
                active_pms=[ActivePM(group="pmg_admin", pm="pm_horizontal_drawer_cabinets")],
            )
        ],
        tech=TechState(researched=[]),
    )
    holdings = {ADMIN_BUILDING: 4.0}
    gc = gov_capacity(holdings, snap, set(), {}, d, [], base_total_levels=4.0)
    assert gc.bureaucracy_produced == 200.0  # 4 levels * 50
    assert gc.bureaucracy_demand == 100.0  # unchanged size
    assert gc.tax_capacity == 40.0  # 4 * 10 * 1.0
    # Double the economy's size -> bureaucracy demand doubles.
    gc2 = gov_capacity({ADMIN_BUILDING: 4.0, "building_x": 4.0}, snap, set(), {}, d, [], base_total_levels=4.0)
    assert gc2.bureaucracy_demand == 200.0
