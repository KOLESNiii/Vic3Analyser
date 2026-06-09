"""Research priorities: which technologies unlock the most economic value.

For the building types the player actually operates, find PMs that a single
not-yet-researched technology would unlock, and estimate the value-added uplift
versus the player's current best available PM in that slot — aggregated across
the player's buildings (scaled by level). Techs are ranked by total potential
uplift, answering "what to research next for the economy".
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .pricing import market_map, value_goods


@dataclass
class TechPriority:
    tech: str
    potential_uplift: float
    unlocks: list[str] = field(default_factory=list)  # building_type:pm pairs


def _pm_value(pm: str, defs: GameDefs, market) -> float:
    flows = defs.pm_goods(pm)
    return value_goods(flows["input"], flows["output"], market, defs.good_base_price).value_added


def analyse_tech_priorities(snap: Snapshot, defs: GameDefs) -> list[TechPriority]:
    market = market_map(snap)
    researched = set(snap.tech.researched)

    # Player's operated building types, weighted by total levels.
    levels_by_type: dict[str, int] = defaultdict(int)
    for b in snap.buildings:
        levels_by_type[b.building_type] += max(b.level, 1)

    uplift: dict[str, float] = defaultdict(float)
    unlocks: dict[str, list[str]] = defaultdict(list)

    for btype, total_levels in levels_by_type.items():
        for group in defs.building_pm_groups(btype):
            pms = defs.group_pms(group)
            # Current best value among already-available PMs in this slot.
            available_vals = [
                _pm_value(pm, defs, market)
                for pm in pms
                if all(t in researched for t in defs.pm_unlocking_techs(pm))
            ]
            current_best = max(available_vals) if available_vals else 0.0

            for pm in pms:
                needed = defs.pm_unlocking_techs(pm)
                missing = [t for t in needed if t not in researched]
                if len(missing) != 1:
                    continue  # only credit single-tech unlocks (clear attribution)
                tech = missing[0]
                gain = _pm_value(pm, defs, market) - current_best
                if gain <= 0:
                    continue
                uplift[tech] += gain * total_levels
                unlocks[tech].append(f"{btype}:{pm}")

    priorities = [
        TechPriority(tech=t, potential_uplift=u, unlocks=unlocks[t])
        for t, u in uplift.items()
    ]
    priorities.sort(key=lambda p: p.potential_uplift, reverse=True)
    return priorities
