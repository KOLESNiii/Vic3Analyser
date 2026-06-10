"""Where to build: rank the player's states by capacity to host new economic
buildings.

Combines player-visible state metrics into a 0..1 capacity score:

* **free infrastructure** — building consumes infrastructure; headroom is good;
* **unemployment** — idle workers staff new buildings faster, with less wage
  pressure;
* **free arable land / resources** — caps on agriculture and extraction.

Each component contributes only when its data is present, so partial saves
still produce a usable ranking. The score is relative across the player's
states, not an absolute measure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..extract.models import Snapshot, StateInfo


@dataclass
class StateCapacity:
    state_id: int | None
    name: str | None
    score: float
    free_infrastructure: float | None
    unemployment: int | None
    free_arable: int | None
    reasons: list[str] = field(default_factory=list)


def _norm(value: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return max(0.0, min(1.0, value / scale))


def analyse_where_to_build(snap: Snapshot) -> list[StateCapacity]:
    states = snap.states
    if not states:
        return []

    # Scales for normalisation: use the max observed so the ranking is relative.
    max_infra = max((s.infrastructure_free or 0.0) for s in states) or 1.0
    max_unemp = max((s.unemployment or 0) for s in states) or 1
    max_arable = max(_free_arable(s) or 0 for s in states) or 1

    out: list[StateCapacity] = []
    for s in states:
        free_infra = s.infrastructure_free
        free_arable = _free_arable(s)
        components: list[float] = []
        reasons: list[str] = []

        if free_infra is not None:
            c = _norm(free_infra, max_infra)
            components.append(c)
            if c > 0.5:
                reasons.append("ample free infrastructure")
            elif c < 0.15:
                reasons.append("low infrastructure headroom")
        if s.unemployment is not None:
            c = _norm(s.unemployment, max_unemp)
            components.append(c)
            if c > 0.5:
                reasons.append("large idle workforce")
        if free_arable is not None:
            c = _norm(free_arable, max_arable)
            components.append(c)
            if c > 0.5:
                reasons.append("free arable land")

        score = sum(components) / len(components) if components else 0.0
        out.append(
            StateCapacity(
                state_id=s.id,
                name=s.name,
                score=score,
                free_infrastructure=free_infra,
                unemployment=s.unemployment,
                free_arable=free_arable,
                reasons=reasons,
            )
        )

    out.sort(key=lambda x: x.score, reverse=True)
    return out


def _free_arable(s: StateInfo) -> int | None:
    if s.arable_total is not None:
        used = s.arable_used if s.arable_used is not None else s.arable_land or 0
        return max(0, int(s.arable_total - used))
    if s.arable_land is None:
        return None
    used = s.arable_used or 0
    return max(0, s.arable_land - used)
