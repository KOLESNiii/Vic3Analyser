"""Player-visible capacity limits and construction economics.

Two things the optimizer needs to be realistic, both now extracted from the save
+ static defs:

* **Land / resource caps.** Agriculture and plantations share a state's
  ``arable_land`` pool (one level each); mines, logging, fishing etc. are capped
  per state by ``capped_resources``. Without these the optimizer happily
  recommends 80 logging camps in a region that can hold 7.
* **Construction economics.** Real construction capacity is small early on, so
  the dominant growth lever is *expanding the construction sector*. A sector
  level adds ``points_per_sector_level`` capacity/week and consumes a goods
  basket (wood/fabric → later iron/steel/tools). Modelling that basket lets
  building compete for those goods (raising their prices) and lets the treasury
  be charged for construction — so the plan can't expand for free.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .build_where import analyse_where_to_build
from .econ_model import best_pm_in_group, price_of

CONSTRUCTION_BUILDING = "building_construction_sector"
# Fallback capacity per construction-sector level when the save doesn't let us
# derive it (points/week).
_DEFAULT_POINTS_PER_SECTOR = 12.0


@dataclass
class CapacityBudget:
    """Free build capacity across the player's states, for the whole country."""

    free_arable: float
    arable_types: set[str]
    capped_free: dict[str, float] = field(default_factory=dict)
    has_known_caps: bool = False

    def cap_for(self, building_type: str) -> float | None:
        """Hard cap on additional levels of a type, or ``None`` if unconstrained
        (urban industry — slot-limited, but slots aren't in the save)."""
        if building_type in self.capped_free:
            return max(0.0, self.capped_free[building_type])
        return None

    def is_arable(self, building_type: str) -> bool:
        return building_type in self.arable_types


@dataclass
class StateAllocation:
    """A feasible placement slice for part of a build step."""

    state_id: int | None
    state_name: str | None
    levels: int


def compute_capacity_budget(snap: Snapshot, defs: GameDefs) -> CapacityBudget:
    """Aggregate free land/resource capacity across the player's states."""
    # Current levels of each (building_type, state).
    levels: dict[tuple[str, int | None], float] = defaultdict(float)
    for b in snap.buildings:
        if b.level > 0:
            levels[(b.building_type, b.state_id)] += b.level

    free_arable = 0.0
    arable_types: set[str] = set()
    capped_free: dict[str, float] = defaultdict(float)

    for s in snap.states:
        # Shared arable pool: total (static) minus what's already in use.
        if s.arable_total is not None:
            used = s.arable_used if s.arable_used is not None else s.arable_land or 0
            free_arable += max(0.0, s.arable_total - used)
        arable_types.update(s.arable_buildings)
        # Per-type resource caps, net of what's already built in this state.
        for bt, cap in s.capped_resources.items():
            built = levels.get((bt, s.id), 0.0)
            capped_free[bt] += max(0.0, cap - built)

    return CapacityBudget(
        free_arable=free_arable,
        arable_types=arable_types,
        capped_free=dict(capped_free),
        has_known_caps=bool(arable_types or capped_free),
    )


def allocate_build_levels(
    snap: Snapshot, building_type: str, levels: int
) -> list[StateAllocation]:
    """Allocate a build step across states without exceeding known hard caps.

    This is a reporting/planning helper: the optimizer searches country-level
    totals for speed, then the strategy report turns each total into feasible
    state slices where the save/static defs expose a cap. Urban buildings are
    ranked by the existing where-to-build score and remain soft suggestions.
    """
    if levels <= 0:
        return []

    ranked_ids = [s.state_id for s in analyse_where_to_build(snap)]
    states_by_id = {s.id: s for s in snap.states if s.id is not None}
    states = [states_by_id[sid] for sid in ranked_ids if sid in states_by_id]
    states.extend(s for s in snap.states if s not in states)

    remaining = int(levels)
    out: list[StateAllocation] = []
    current_levels: dict[tuple[str, int | None], float] = defaultdict(float)
    for b in snap.buildings:
        if b.level > 0:
            current_levels[(b.building_type, b.state_id)] += b.level

    for state in states:
        if remaining <= 0:
            break
        room = _state_room_for(state, building_type, current_levels)
        if room is None:
            if out:
                continue
            take = remaining
        else:
            take = min(remaining, int(room))
        if take <= 0:
            continue
        out.append(StateAllocation(state.id, state.name, take))
        remaining -= take

    if not out and remaining > 0:
        # No state data. Keep the build order usable, but mark the placement as
        # unknown rather than inventing a state.
        out.append(StateAllocation(None, None, remaining))
    return out


def _state_room_for(
    state, building_type: str, current_levels: dict[tuple[str, int | None], float]
) -> float | None:
    """Hard room for one state/type, or None if no hard cap is known."""
    if building_type in state.capped_resources:
        built = current_levels.get((building_type, state.id), 0.0)
        return max(0.0, state.capped_resources[building_type] - built)
    if building_type in state.arable_buildings:
        if state.arable_total is None:
            return None
        used = state.arable_used if state.arable_used is not None else state.arable_land or 0
        return max(0.0, state.arable_total - used)
    return None


def points_per_sector_level(snap: Snapshot) -> float:
    p = snap.construction.points_per_sector_level
    return p if p and p > 0 else _DEFAULT_POINTS_PER_SECTOR


def _construction_add(pm: str, defs: GameDefs) -> float:
    """Construction points/level a construction-sector PM grants
    (``country_construction_add``)."""
    return defs.pm_capacity_outputs(pm).get("country_construction_add", 0.0)


def construction_pms(defs: GameDefs) -> list[str]:
    groups = defs.building_pm_groups(CONSTRUCTION_BUILDING)
    return defs.group_pms(groups[0]) if groups else []


def current_construction_pm(snap: Snapshot, defs: GameDefs) -> str | None:
    """The construction-sector PM the player is currently running, if any."""
    group_pms = set(construction_pms(defs))
    for b in snap.buildings:
        if b.building_type == CONSTRUCTION_BUILDING:
            for apm in b.active_pms:
                if apm.pm in group_pms:
                    return apm.pm
    return None


def best_construction_pm(researched: set[str], defs: GameDefs) -> str | None:
    """Researched construction-sector PM with the most points/level (the frame
    tier a growth-minded player upgrades to: wooden→iron→steel→arc)."""
    best: str | None = None
    best_add = -1.0
    for pm in construction_pms(defs):
        if any(t not in researched for t in defs.pm_unlocking_techs(pm)):
            continue
        add = _construction_add(pm, defs)
        if add > best_add:
            best, best_add = pm, add
    return best


def construction_pm_upgrade(
    snap: Snapshot, defs: GameDefs, researched: set[str], cfg: OptimizeConfig | None = None
) -> tuple[str | None, str | None, float]:
    """``(current_pm, best_pm, points_multiplier)`` for the construction frame.

    The multiplier is how much more points/level the best researched frame gives
    over the current one — the construction-throughput lever. ``1.0`` when there's
    no upgrade or the feature is disabled.
    """
    if cfg is not None and not cfg.model_construction_pm:
        return None, None, 1.0
    cur = current_construction_pm(snap, defs)
    best = best_construction_pm(researched, defs)
    cur_add = _construction_add(cur, defs) if cur else 0.0
    best_add = _construction_add(best, defs) if best else 0.0
    if best is None or cur is None or cur_add <= 0 or best_add <= cur_add:
        return cur, best, 1.0
    return cur, best, best_add / cur_add


def construction_points_per_level(
    snap: Snapshot, defs: GameDefs, researched: set[str], cfg: OptimizeConfig | None = None
) -> float:
    """Points/week a *new* construction-sector level adds.

    Anchored on the save's observed points/level (which already bakes in the
    player's real bonuses), scaled by the frame-tier upgrade ratio when the
    plan adopts a better researched frame. Falls back to the observed value.
    """
    observed = points_per_sector_level(snap)
    _cur, _best, mult = construction_pm_upgrade(snap, defs, researched, cfg)
    return observed * mult


def construction_cost_per_point(
    prices: dict[str, float],
    defs: GameDefs,
    researched: set[str],
    per_level_points: float,
    pm: str | None = None,
) -> float:
    """Money cost of one construction point, from the construction sector's goods
    basket valued at the given prices. Uses the frame ``pm`` actually being run
    (best researched tier) so a richer-but-faster frame is priced correctly."""
    if per_level_points <= 0:
        return 0.0
    if pm is None:
        pm = best_construction_pm(researched, defs)
    if pm is None:
        groups = defs.building_pm_groups(CONSTRUCTION_BUILDING)
        pm = best_pm_in_group(groups[0], researched, prices, defs) if groups else None
    if pm is None:
        return 0.0
    inputs = defs.pm_goods(pm)["input"]
    cost_per_level = sum(price_of(g, prices, defs) * q for g, q in inputs.items())
    return cost_per_level / per_level_points
