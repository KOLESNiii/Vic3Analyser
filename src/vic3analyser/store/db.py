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
                "SELECT date FROM snapshots WHERE player_tag = ? ORDER BY date",
                (player_tag,),
            ).fetchall()
        return [r["date"] for r in rows]

    def latest(self, player_tag: str | None = None) -> Snapshot | None:
        with closing(self._connect()) as con:
            if player_tag is None:
                row = con.execute(
                    "SELECT payload FROM snapshots ORDER BY date DESC LIMIT 1"
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT payload FROM snapshots WHERE player_tag = ? "
                    "ORDER BY date DESC LIMIT 1",
                    (player_tag,),
                ).fetchone()
        return Snapshot.model_validate_json(row["payload"]) if row else None

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
                f"SELECT {select} FROM snapshots WHERE player_tag = ? ORDER BY date",
                (player_tag,),
            ).fetchall()
        return [dict(r) for r in rows]

    def tags(self) -> list[str]:
        with closing(self._connect()) as con:
            rows = con.execute(
                "SELECT DISTINCT player_tag FROM snapshots ORDER BY player_tag"
            ).fetchall()
        return [r["player_tag"] for r in rows]
