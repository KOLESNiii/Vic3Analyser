"""Build-order sequencing + land-gating fixes.

- The reported build order keeps the optimiser's interleaved cascade sequence
  (input producers alongside their consumers) instead of grouping by type.
- Concrete farm buildings live in child groups (bg_staple_crops under
  bg_agriculture), so land-gating must follow the group ancestry — otherwise
  crops that don't grow in any owned state get built as unlimited urban industry.
"""

from vic3analyser.ingest.defs import GameDefs
from vic3analyser.analysis.actions import economic_build_options
from vic3analyser.analysis.optimize import StepTrace, _interleaved_program


def _trace(types: list[str]) -> list[StepTrace]:
    return [
        StepTrace(
            order=i,
            building_type=t,
            levels=1,
            value_per_point=0.0,
            key_output=None,
            key_output_price_ratio=None,
        )
        for i, t in enumerate(types)
    ]


def test_interleaved_program_keeps_cascade_order():
    # construction sectors alternate with the logging that feeds them.
    trace = _trace(
        ["building_construction_sector", "building_logging_camp", "building_construction_sector",
         "building_logging_camp", "building_logging_camp"]
    )
    totals = {"building_construction_sector": 2, "building_logging_camp": 3}
    prog = _interleaved_program(trace, totals)
    seq = [(s.building_type, s.levels) for s in prog]
    # Consecutive same-type merge, but the alternation is preserved.
    assert seq == [
        ("building_construction_sector", 1),
        ("building_logging_camp", 1),
        ("building_construction_sector", 1),
        ("building_logging_camp", 2),
    ]


def test_interleaved_program_caps_and_appends_to_refined_totals():
    trace = _trace(["building_a", "building_b", "building_a"])
    # refinement dropped 'a' to 1 and grew 'b' to 2 (not all in the trace).
    prog = _interleaved_program(trace, {"building_a": 1, "building_b": 2})
    seq = [(s.building_type, s.levels) for s in prog]
    assert seq[0] == ("building_a", 1)  # capped at 1, second 'a' step dropped
    # one 'b' from the trace + one leftover (refined beyond trace), merged.
    assert sum(lv for t, lv in seq if t == "building_b") == 2
    assert sum(lv for t, lv in seq if t == "building_a") == 1


def _farm_defs() -> GameDefs:
    return GameDefs(
        goods={"grain": {"cost": 30}},
        production_methods={"pm_f": {"building_modifiers": {"workforce_scaled": {"goods_output_grain_add": 10}}}},
        production_method_groups={"pmg_f": {"production_methods": ["pm_f"]}},
        building_groups={
            "bg_agriculture": {},
            "bg_staple_crops": {"parent_group": "bg_agriculture"},
            "bg_manufacturing": {},
        },
        building_types={
            "building_rye_farm": {
                "building_group": "bg_staple_crops",
                "production_method_groups": ["pmg_f"],
                "required_construction": 200,
            },
            "building_steel_mill": {
                "building_group": "bg_manufacturing",
                "production_method_groups": ["pmg_f"],
                "required_construction": 200,
            },
        },
    )


def test_staple_crops_are_land_gated_via_ancestry():
    d = _farm_defs()
    opts = {o.building_type: o for o in economic_build_options(None, d)}
    # rye_farm's group (bg_staple_crops) descends from bg_agriculture -> gated.
    assert opts["building_rye_farm"].resource_gated is True
    # manufacturing is urban -> not land-gated.
    assert opts["building_steel_mill"].resource_gated is False
