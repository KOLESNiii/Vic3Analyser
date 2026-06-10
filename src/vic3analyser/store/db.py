"""SQLite time-series store for extracted snapshots.

Each snapshot is stored whole (as JSON) keyed by ``(player_tag, date)`` so the
dashboard can replay history, plus a few headline scalars are denormalised into
columns for fast trend queries without rehydrating every snapshot.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from ..extract.models import Snapshot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    player_tag     TEXT NOT NULL,
    date           TEXT NOT NULL,
    gdp            REAL,
    treasury       REAL,
    weekly_balance REAL,
    payload        TEXT NOT NULL,
    PRIMARY KEY (player_tag, date)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_tag ON snapshots(player_tag);
"""


def _date_key(date: str) -> tuple[int, int, int, str]:
    """Sortable key for Vic3 dates like ``1836.10.1``.

    SQLite only sees the date as text, which makes ``1836.8.1`` sort after
    ``1836.10.1``. Parse the numeric parts in Python; keep the raw string as a
    final tie-breaker for defensive handling of unusual date formats.
    """
    parts = str(date).split(".")
    nums: list[int] = []
    for part in parts[:3]:
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(-1)
    while len(nums) < 3:
        nums.append(-1)
    return nums[0], nums[1], nums[2], str(date)


class SnapshotStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "snapshots.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con:
            con.executescript(_SCHEMA)
            con.commit()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def save(self, snap: Snapshot) -> None:
        """Insert or replace a snapshot (idempotent on player_tag+date)."""
        with closing(self._connect()) as con:
            con.execute(
                """
                INSERT OR REPLACE INTO snapshots
                    (player_tag, date, gdp, treasury, weekly_balance, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snap.player_tag,
                    snap.date,
                    snap.country.gdp,
                    snap.country.treasury,
                    snap.country.weekly_balance,
                    snap.model_dump_json(),
                ),
            )
            con.commit()

    def dates(self, player_tag: str) -> list[str]:
        with closing(self._connect()) as con:
            rows = con.execute(
                "SELECT date FROM snapshots WHERE player_tag = ?",
                (player_tag,),
            ).fetchall()
        return sorted((r["date"] for r in rows), key=_date_key)

    def latest(self, player_tag: str | None = None) -> Snapshot | None:
        with closing(self._connect()) as con:
            if player_tag is None:
                row = con.execute(
                    "SELECT date, payload FROM snapshots"
                ).fetchall()
            else:
                row = con.execute(
                    "SELECT date, payload FROM snapshots WHERE player_tag = ?",
                    (player_tag,),
                ).fetchall()
        if not row:
            return None
        latest = max(row, key=lambda r: _date_key(r["date"]))
        return Snapshot.model_validate_json(latest["payload"])

    def history(self, player_tag: str, limit: int = 24) -> list[Snapshot]:
        """Recent snapshots oldest→newest (up to ``limit``) for calibration.

        The optimizer uses this to learn how the player's own market responded
        to their own production over time. Rehydrates full snapshots from the
        stored JSON payloads.
        """
        with closing(self._connect()) as con:
            rows = con.execute(
                "SELECT payload FROM snapshots WHERE player_tag = ? "
                "ORDER BY date",
                (player_tag,),
            ).fetchall()
        snaps = [Snapshot.model_validate_json(r["payload"]) for r in rows]
        snaps.sort(key=lambda s: _date_key(s.date))
        return snaps[-limit:]

    def get(self, player_tag: str, date: str) -> Snapshot | None:
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT payload FROM snapshots WHERE player_tag = ? AND date = ?",
                (player_tag, date),
            ).fetchone()
        return Snapshot.model_validate_json(row["payload"]) if row else None

    def series(self, player_tag: str, metrics: list[str]) -> list[dict]:
        """Return denormalised headline metrics over time for charting.

        ``metrics`` is a subset of {"gdp", "treasury", "weekly_balance"}.
        """
        allowed = {"gdp", "treasury", "weekly_balance"}
        cols = [m for m in metrics if m in allowed]
        select = ", ".join(["date", *cols]) if cols else "date"
        with closing(self._connect()) as con:
            rows = con.execute(
                f"SELECT {select} FROM snapshots WHERE player_tag = ?",
                (player_tag,),
            ).fetchall()
        out = [dict(r) for r in rows]
        out.sort(key=lambda r: _date_key(r["date"]))
        return out

    def tags(self) -> list[str]:
        with closing(self._connect()) as con:
            rows = con.execute(
                "SELECT DISTINCT player_tag FROM snapshots ORDER BY player_tag"
            ).fetchall()
        return [r["player_tag"] for r in rows]
