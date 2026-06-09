"""Synthesize all analyses into one prioritized, explained action list.

This is the "actionable points" layer. It pulls from every analysis module and
emits :class:`Recommendation` items with a comparable ``impact`` (estimated
value-added per week, in the market's money units) so they can be ranked
together. Each item carries a human-readable rationale and an ``estimated``
flag so the dashboard can be honest about confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .build_what import analyse_what_to_build
from .build_where import analyse_where_to_build
from .construction import analyse_construction
from .market import analyse_market
from .pm_optimizer import analyse_pm_switches
from .tech import analyse_tech_priorities


@dataclass
class Recommendation:
    category: str  # "pm" | "build" | "where" | "construction" | "tech" | "market"
    title: str
    detail: str
    impact: float  # estimated value-added/week; used for ranking
    estimated: bool = True
    refs: dict = field(default_factory=dict)


def build_recommendations(
    snap: Snapshot,
    defs: GameDefs,
    limit_per_category: int = 5,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    # 1. PM switches — concrete, high-signal, often the biggest quick wins.
    for r in analyse_pm_switches(snap, defs)[:limit_per_category]:
        loc = f" in state {r.state_id}" if r.state_id is not None else ""
        cur = r.current_pm or "(none)"
        recs.append(
            Recommendation(
                category="pm",
                title=f"Switch {r.building_type}{loc}: {cur} → {r.best_pm}",
                detail=(
                    f"+{r.delta_per_level:,.0f}/level value-added at current prices "
                    f"(~+{r.delta_total:,.0f} total for this building)."
                ),
                impact=r.delta_total,
                refs={"building_id": r.building_id, "group": r.group},
            )
        )

    # 2. What to build (paired with the best state to put it in).
    where = analyse_where_to_build(snap)
    best_state = where[0] if where else None
    for c in analyse_what_to_build(snap, defs)[:limit_per_category]:
        loc = ""
        if best_state is not None:
            loc = f" Best location: {best_state.name or best_state.state_id}."
        recs.append(
            Recommendation(
                category="build",
                title=f"Build {c.building_type}",
                detail=(
                    f"~{c.raw_value_added:,.0f}/level value-added; "
                    + (", ".join(c.notes) if c.notes else "solid return at current prices")
                    + "."
                    + loc
                ),
                impact=c.score,
                refs={"best_pms": c.best_pms, "state_id": getattr(best_state, "state_id", None)},
            )
        )

    # 3. Construction queue: surface slow-payback items to reconsider.
    cons = analyse_construction(snap, defs)
    for q in cons.queue_by_payback:
        if q.payback_weeks is None:
            continue
        recs.append(
            Recommendation(
                category="construction",
                title=f"Queued {q.building_type}: payback ~{q.payback_weeks:,.0f} wk",
                detail=(
                    f"{q.levels} level(s), est. +{q.est_weekly_profit or 0:,.0f}/wk."
                    if q.est_weekly_profit
                    else f"{q.levels} level(s)."
                ),
                impact=(q.est_weekly_profit or 0.0),
                refs={"state_id": q.state_id},
            )
        )

    # 4. Tech priorities for the economy.
    for t in analyse_tech_priorities(snap, defs)[:limit_per_category]:
        recs.append(
            Recommendation(
                category="tech",
                title=f"Research {t.tech}",
                detail=(
                    f"Unlocks better PMs ({', '.join(t.unlocks[:3])}"
                    + ("…" if len(t.unlocks) > 3 else "")
                    + f"); ~+{t.potential_uplift:,.0f}/wk across your buildings."
                ),
                impact=t.potential_uplift,
                refs={"unlocks": t.unlocks},
            )
        )

    # 5. Market context: most acute shortages (lower direct impact weight).
    market = analyse_market(snap)
    for g in market.shortages[:3]:
        recs.append(
            Recommendation(
                category="market",
                title=f"{g.good} in shortage (price {g.price:,.0f}, "
                f"{(g.price_ratio or 1) * 100 - 100:+.0f}% vs base)",
                detail="Producing this good is currently lucrative; see What to Build.",
                impact=0.0,  # contextual, not a direct money figure
                refs={},
            )
        )

    recs.sort(key=lambda r: r.impact, reverse=True)
    return recs
