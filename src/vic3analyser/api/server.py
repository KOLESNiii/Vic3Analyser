"""FastAPI server: serves the dashboard and analysis API, and watches the
autosave folder so the data refreshes itself each game-month.

Run with ``uv run vic3analyser`` (see ``[project.scripts]``).
"""

from __future__ import annotations

import threading
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..config import Config, load_config
from ..ingest.defs import GameDefs, load_defs
from ..pipeline import analyse_all, process_save
from ..store.db import SnapshotStore

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class AppState:
    """Holds shared, mutable server state behind a lock."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.store = SnapshotStore(cfg.paths.data_dir)
        self.defs: GameDefs | None = None
        self.defs_error: str | None = None
        self.last_ingest: str | None = None
        self.last_error: str | None = None
        self._lock = threading.Lock()
        self._observer = None
        self._load_defs()

    def _load_defs(self) -> None:
        try:
            self.defs = load_defs(self.cfg)
            self.defs_error = None
        except Exception as exc:  # noqa: BLE001 - surface to status endpoint
            self.defs = None
            self.defs_error = str(exc)

    def reload_defs(self) -> None:
        with self._lock:
            self._load_defs()

    def ingest(self, path: str | Path) -> str:
        """Process one save (thread-safe). Returns the snapshot date."""
        if self.defs is None:
            raise RuntimeError(self.defs_error or "Game definitions not loaded.")
        with self._lock:
            snap = process_save(path, self.cfg, self.defs, self.store)
            self.last_ingest = snap.date
            self.last_error = None
            return snap.date

    def analysis(self, player_tag: str | None = None) -> dict[str, Any] | None:
        snap = self.store.latest(player_tag)
        if snap is None or self.defs is None:
            return None
        with self._lock:
            return analyse_all(snap, self.defs)

    # --- autosave watching -------------------------------------------------

    def start_watcher(self) -> None:
        save_dir = self.cfg.paths.save_dir
        if save_dir is None or not Path(save_dir).is_dir():
            return
        try:
            from watchdog.observers import Observer

            from .watcher import SaveHandler
        except Exception:  # noqa: BLE001
            return
        handler = SaveHandler(self._on_new_save)
        obs = Observer()
        obs.schedule(handler, str(save_dir), recursive=True)
        obs.daemon = True
        obs.start()
        self._observer = obs

    def _on_new_save(self, path: str) -> None:
        try:
            self.ingest(path)
        except Exception:  # noqa: BLE001
            self.last_error = traceback.format_exc(limit=3)

    def ingest_latest_existing(self) -> None:
        """On startup, ingest the newest save already in the folder."""
        save_dir = self.cfg.paths.save_dir
        if save_dir is None or not Path(save_dir).is_dir():
            return
        saves = sorted(Path(save_dir).rglob("*.v3"), key=lambda p: p.stat().st_mtime)
        if saves:
            self._on_new_save(str(saves[-1]))


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or load_config()
    state = AppState(cfg)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        state.ingest_latest_existing()
        state.start_watcher()
        yield

    app = FastAPI(title="Vic3 Economic Analyser", lifespan=lifespan)
    app.state.app_state = state

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        tags = state.store.tags()
        return {
            "install": str(cfg.paths.vic3_install) if cfg.paths.vic3_install else None,
            "common_dir": str(cfg.common_dir) if cfg.common_dir else None,
            "save_dir": str(cfg.paths.save_dir) if cfg.paths.save_dir else None,
            "rakaly": str(cfg.paths.rakaly_bin) if cfg.paths.rakaly_bin else None,
            "defs_loaded": state.defs is not None,
            "defs_error": state.defs_error,
            "player_tags": tags,
            "last_ingest": state.last_ingest,
            "last_error": state.last_error,
        }

    @app.get("/api/analysis")
    def analysis(player_tag: str | None = Query(default=None)) -> Any:
        data = state.analysis(player_tag)
        if data is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    state.defs_error
                    or "No snapshot yet. Ingest a save (autosave watcher, or "
                    "POST /api/ingest?path=...)."
                ),
            )
        return JSONResponse(data)

    @app.get("/api/snapshot")
    def snapshot(player_tag: str | None = Query(default=None)) -> Any:
        snap = state.store.latest(player_tag)
        if snap is None:
            raise HTTPException(status_code=404, detail="No snapshot stored yet.")
        return JSONResponse(snap.model_dump())

    @app.get("/api/dates")
    def dates(player_tag: str) -> list[str]:
        return state.store.dates(player_tag)

    @app.get("/api/series")
    def series(player_tag: str, metrics: str = "gdp,treasury,weekly_balance") -> Any:
        wanted = [m.strip() for m in metrics.split(",") if m.strip()]
        return JSONResponse(state.store.series(player_tag, wanted))

    @app.post("/api/ingest")
    def ingest(path: str) -> dict[str, str]:
        try:
            date = state.ingest(path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ingested": date}

    @app.post("/api/reload-defs")
    def reload_defs() -> dict[str, Any]:
        state.reload_defs()
        return {"defs_loaded": state.defs is not None, "defs_error": state.defs_error}

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

    return app


def main() -> None:
    import uvicorn

    cfg = load_config()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
