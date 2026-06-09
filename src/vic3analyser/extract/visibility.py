"""Enforce the player-visibility rule and resolve which country is the player.

The analyser must only ever surface data the player can see in-game. Two
mechanisms:

* `resolve_player` finds the human/played country and returns its id + tag.
* `DISALLOWED_NODES` documents gamestate branches we must never read into a
  snapshot (AI strategy/plans, other countries' internal ledgers). The
  extractor is written to touch only allowed fields; this list is the explicit
  guard and is asserted in tests.
"""

from __future__ import annotations

from typing import Any

from ..ingest.parser import as_list

# Branches that contain non-player-visible or AI-only information. The extractor
# must not pull values out of these into a Snapshot.
DISALLOWED_NODES = frozenset(
    {
        "ai",
        "ai_strategy",
        "ai_manager",
        "strategic_region_ai",
        "diplomatic_ai",
    }
)


def resolve_player(gamestate: dict, configured_tag: str | None) -> tuple[int | None, str | None]:
    """Return ``(country_id, tag)`` for the player country.

    Resolution order: configured tag → explicit played/human marker in the
    save. Returns ``(None, configured_tag)`` if the id can't be resolved yet
    (the country database key name is confirmed in Phase 2).
    """
    countries = _country_database(gamestate)

    if configured_tag:
        cid = _find_country_by_tag(countries, configured_tag)
        return cid, configured_tag

    # Explicit markers seen across PDX saves; confirm exact key for Vic3.
    for key in ("played_country", "human_countries", "human", "player"):
        marker = gamestate.get(key)
        if marker is None:
            continue
        ids = [int(x) for x in as_list(marker) if _is_int(x)]
        if ids:
            cid = ids[0]
            return cid, _tag_of(countries, cid)

    return None, None


def _country_database(gamestate: dict) -> dict:
    mgr = gamestate.get("country_manager")
    if isinstance(mgr, dict):
        db = mgr.get("database")
        if isinstance(db, dict):
            return db
    db = gamestate.get("countries")
    return db if isinstance(db, dict) else {}


def _find_country_by_tag(countries: dict, tag: str) -> int | None:
    for cid, c in countries.items():
        if isinstance(c, dict) and (c.get("definition") == tag or c.get("tag") == tag):
            return _as_int(cid)
    return None


def _tag_of(countries: dict, cid: int | None) -> str | None:
    if cid is None:
        return None
    c = countries.get(str(cid)) or countries.get(cid)
    if isinstance(c, dict):
        return c.get("definition") or c.get("tag")
    return None


def _is_int(x: Any) -> bool:
    try:
        int(x)
        return True
    except (TypeError, ValueError):
        return False


def _as_int(x: Any) -> int | None:
    try:
        return int(x)
    except (TypeError, ValueError):
        return None
