"""The action space the optimizer searches over.

An economic plan is built out of three kinds of move:

* **build** N levels of a building type (the dominant lever for growth),
* **switch** a building's production method (handled implicitly: the optimized
  economy always runs the best PM per slot at the prevailing equilibrium price,
  so PM switches fall out of the equilibrium solve and are *reported* by diffing
  against the current active PMs — see :mod:`strategy`),
* **research** a technology, which unlocks better PMs / new buildings partway
  through the trajectory.

This module enumerates the *candidates* and the static metadata each carries
(construction cost, tech gating, capacity class). The valuation of a move — how
much it actually grows the economy once cascades are accounted for — is the
simulator's job, because it depends on the evolving equilibrium.

Everything is player-visible: building costs and gating come from the game defs
the player can read, capacity from the player's own states.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from ..ingest.parser import as_list
from .build_where import analyse_where_to_build
from .econ_model import best_pm_in_group

# Building groups whose levels are gated by land/resources rather than urban
# building slots. We can only *softly* cap these (the save rarely persists the
# remaining capacity), but the classification still informs state assignment and
# the assumptions we surface.
RESOURCE_GROUPS = frozenset(
    {
        "bg_agriculture",
        "bg_plantations",
        "bg_ranching",
        "bg_mining",
        "bg_oil_extraction",
        "bg_logging",
        "bg_fishing",
        "bg_gold_fields",
        "bg_rubber",
    }
)

# Rough research time per technology era, in game-weeks. Real research speed
# depends on innovation (literacy/SoL — player-visible but volatile); this is a
# deliberately coarse, configurable-by-era estimate, flagged as such upstream.
_ERA_WEEKS = {
    "era_1": 26,
    "era_2": 39,
    "era_3": 52,
    "era_4": 65,
    "era_5": 78,
    "era_6": 91,
    "era_7": 104,
}
_DEFAULT_TECH_WEEKS = 52

# Default cap on how many levels of a single building type one plan may add,
# when no tighter capacity is known. Price feedback (diminishing returns)
# usually bites long before this; it just bounds the search.
DEFAULT_MAX_ADDED_LEVELS = 100


@dataclass
class BuildOption:
    """A candidate building type the plan may invest construction into."""

    building_type: str
    cost_per_level: float
    pm_groups: list[str]
    unlocking_techs: list[str]
    building_group: str | None
    resource_gated: bool
    max_added_levels: int

    def buildable_now(self, researched: set[str], prices: dict[str, float], defs: GameDefs) -> bool:
        """True when the player's tech allows building it and running every slot."""
        if any(t not in researched for t in self.unlocking_techs):
            return False
        for group in self.pm_groups:
            if best_pm_in_group(group, researched, prices, defs) is None:
                return False
        return True


@dataclass
class TechOption:
    """A researchable technology and what it unlocks for the economy."""

    tech: str
    era: str | None
    weeks: int
    unlocks_pms: list[str] = field(default_factory=list)
    unlocks_buildings: list[str] = field(default_factory=list)
    prereqs: list[str] = field(default_factory=list)

    def researchable_now(self, researched: set[str]) -> bool:
        return self.tech not in researched and all(p in researched for p in self.prereqs)


def tech_weeks(tech: str, defs: GameDefs) -> int:
    """Estimated game-weeks to research a tech, from its era (coarse)."""
    tdef = defs.technologies.get(tech, {})
    era = tdef.get("era") if isinstance(tdef, dict) else None
    return _ERA_WEEKS.get(str(era), _DEFAULT_TECH_WEEKS)


def _produces_priced_good(btype: str, defs: GameDefs) -> bool:
    """Whether any PM of the building outputs a good with a known base price."""
    for group in defs.building_pm_groups(btype):
        for pm in defs.group_pms(group):
            for g in defs.pm_goods(pm)["output"]:
                if defs.good_base_price(g) is not None:
                    return True
    return False


def economic_build_options(
    snap: Snapshot,
    defs: GameDefs,
    max_added_levels: int = DEFAULT_MAX_ADDED_LEVELS,
) -> list[BuildOption]:
    """All economic building types the plan could invest in (gating deferred).

    "Economic" = has PM groups and produces a priced good (drops purely military
    / administrative buildings that contribute no market value-added). Whether a
    type is *buildable now* depends on tech and is checked per step by the
    simulator via :meth:`BuildOption.buildable_now`.
    """
    options: list[BuildOption] = []
    for btype, bt in defs.building_types.items():
        groups = defs.building_pm_groups(btype)
        if not groups or not _produces_priced_good(btype, defs):
            continue
        cost = defs.building_construction_cost(btype)
        if cost is None or cost <= 0:
            continue
        group = bt.get("building_group") if isinstance(bt, dict) else None
        group = str(group) if group is not None else None
        # Land/resource gating follows the group *ancestry*: the concrete farm
        # buildings live in child groups (e.g. ``bg_staple_crops`` under
        # ``bg_agriculture``), so a direct-group check would miss them and treat
        # them as unlimited urban industry.
        resource_gated = any(g in RESOURCE_GROUPS for g in defs.building_group_chain(btype))
        options.append(
            BuildOption(
                building_type=btype,
                cost_per_level=cost,
                pm_groups=groups,
                unlocking_techs=defs.building_unlocking_techs(btype),
                building_group=group,
                resource_gated=resource_gated,
                max_added_levels=max_added_levels,
            )
        )
    return options


def tech_options(snap: Snapshot, defs: GameDefs) -> list[TechOption]:
    """Not-yet-researched technologies that unlock economic PMs or buildings."""
    researched = set(snap.tech.researched)

    # Reverse-index: which PMs / buildings each tech unlocks.
    pm_by_tech: dict[str, list[str]] = {}
    for pm in defs.production_methods:
        for t in defs.pm_unlocking_techs(pm):
            pm_by_tech.setdefault(t, []).append(pm)
    bld_by_tech: dict[str, list[str]] = {}
    for btype in defs.building_types:
        for t in defs.building_unlocking_techs(btype):
            bld_by_tech.setdefault(t, []).append(btype)

    options: list[TechOption] = []
    for tname, tdef in defs.technologies.items():
        if tname in researched:
            continue
        pms = pm_by_tech.get(tname, [])
        blds = bld_by_tech.get(tname, [])
        if not pms and not blds:
            continue  # not an economic-relevant tech
        era = tdef.get("era") if isinstance(tdef, dict) else None
        era = str(era) if era is not None else None
        # A tech's own prerequisites live on its ``unlocking_technologies``.
        prereq_list = (
            [str(t) for t in as_list(tdef.get("unlocking_technologies"))]
            if isinstance(tdef, dict)
            else []
        )
        options.append(
            TechOption(
                tech=tname,
                era=era,
                weeks=_ERA_WEEKS.get(era or "", _DEFAULT_TECH_WEEKS),
                unlocks_pms=pms,
                unlocks_buildings=blds,
                prereqs=prereq_list,
            )
        )
    return options


def state_assignment(snap: Snapshot, resource_gated: bool) -> list[int | None]:
    """Preferred state ids to place a building in, best capacity first.

    Reuses the existing where-to-build capacity ranking. The order is a
    suggestion the strategy report attaches to each build; the country-level
    optimizer reasons about totals, not per-state placement.
    """
    ranked = analyse_where_to_build(snap)
    return [s.state_id for s in ranked]
