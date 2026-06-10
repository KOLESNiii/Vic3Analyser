"""End-to-end ingestion: a ``.v3`` save in, a stored :class:`Snapshot` out.

    melt -> parse -> build_snapshot (player-visible) -> persist

Also bundles all analyses into one JSON-able payload for the API/dashboard.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .analysis.build_what import analyse_what_to_build, producible_goods
from .analysis.build_where import analyse_where_to_build
from .analysis.construction import analyse_construction
from .analysis.market import analyse_market
from .analysis.pm_optimizer import analyse_pm_switches
from .analysis.profitability import analyse_profitability
from .analysis.recommend import build_recommendations
from .analysis.tech import analyse_tech_priorities
from .config import Config
from .extract.models import Snapshot
from .extract.snapshot import build_snapshot
from .ingest.defs import GameDefs
from .ingest.melt import melt_save
from .ingest.parser import parse
from .store.db import SnapshotStore


def process_save(
    path: str | Path,
    cfg: Config,
    defs: GameDefs,
    store: SnapshotStore | None = None,
) -> Snapshot:
    """Melt, parse, extract and (optionally) persist a save."""
    melted = melt_save(path, cfg)
    gamestate = parse(melted.gamestate)
    snap = build_snapshot(gamestate, defs, cfg, source=melted.source)
    if store is not None:
        store.save(snap)
    return snap


def _ser(obj: Any) -> Any:
    """Recursively convert dataclasses/pydantic/containers to JSON-able data."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _ser(v) for k, v in asdict(obj).items()}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _ser(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_ser(v) for v in obj]
    return obj


def _ser_good(g: Any) -> dict[str, Any]:
    """Serialise a GoodSignal including its computed ``status`` (asdict drops
    properties, and the dashboard's market table renders ``status``)."""
    d = _ser(g)
    d["status"] = g.status
    return d


def analyse_all(snap: Snapshot, defs: GameDefs) -> dict[str, Any]:
    """Run every analysis and return one JSON-able payload."""
    producible = producible_goods(snap, defs)
    market = analyse_market(snap, producible)
    return {
        "date": snap.date,
        "player_tag": snap.player_tag,
        "game_version": snap.game_version,
        "source": snap.source,
        "country": snap.country.model_dump(),
        "market": {
            "goods": [_ser_good(g) for g in market.goods],
            "shortages": [_ser_good(g) for g in market.shortages],
            "gluts": [_ser_good(g) for g in market.gluts],
        },
        "profitability": _ser(analyse_profitability(snap, defs)),
        "pm_switches": _ser(analyse_pm_switches(snap, defs)),
        "build_what": _ser(analyse_what_to_build(snap, defs)),
        "build_where": _ser(analyse_where_to_build(snap)),
        "construction": _ser(analyse_construction(snap, defs)),
        "tech": _ser(analyse_tech_priorities(snap, defs)),
        "recommendations": _ser(build_recommendations(snap, defs)),
    }
