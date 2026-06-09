"""Construction focus: payback ranking of the queue and suggested additions.

Construction capacity is the player's scarcest economic resource. This values
each queued item by payback time (cost ÷ projected weekly profit) and flags
high-return building types (from :mod:`build_what`) that aren't queued yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .build_what import analyse_what_to_build


@dataclass
class QueueItemAnalysis:
    building_type: str
    state_id: int | None
    levels: int
    remaining_cost: float | None
    est_weekly_profit: float | None
    payback_weeks: float | None


@dataclass
class ConstructionReport:
    points_per_week: float | None
    queue: list[QueueItemAnalysis]
    suggested_additions: list[str] = field(default_factory=list)

    @property
    def queue_by_payback(self) -> list[QueueItemAnalysis]:
        known = [q for q in self.queue if q.payback_weeks is not None]
        unknown = [q for q in self.queue if q.payback_weeks is None]
        known.sort(key=lambda q: q.payback_weeks)  # fastest payback first
        return known + unknown


def analyse_construction(snap: Snapshot, defs: GameDefs) -> ConstructionReport:
    # Per-level value-added estimate per building type, from current prices.
    candidates = analyse_what_to_build(snap, defs)
    profit_per_level = {c.building_type: c.raw_value_added for c in candidates}

    items: list[QueueItemAnalysis] = []
    for q in snap.construction.queue:
        per_level = profit_per_level.get(q.building_type)
        est_profit = per_level * q.levels if per_level is not None else None
        payback = (
            q.remaining_cost / est_profit
            if (q.remaining_cost is not None and est_profit and est_profit > 0)
            else None
        )
        items.append(
            QueueItemAnalysis(
                building_type=q.building_type,
                state_id=q.state_id,
                levels=q.levels,
                remaining_cost=q.remaining_cost,
                est_weekly_profit=est_profit,
                payback_weeks=payback,
            )
        )

    queued_types = {q.building_type for q in snap.construction.queue}
    suggestions = [c.building_type for c in candidates[:5] if c.building_type not in queued_types]

    return ConstructionReport(
        points_per_week=snap.construction.points_per_week,
        queue=items,
        suggested_additions=suggestions,
    )
