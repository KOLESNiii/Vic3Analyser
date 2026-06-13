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

from dataclasses import replace

from ..analysis.strategy import build_strategy
from ..config import Config, load_config
from ..ingest.defs import GameDefs, load_defs
from ..pipeline import _ser, analyse_all, process_save
from ..store.db import SnapshotStore

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def is_autosave(path: Path) -> bool:
    """Vic3 names its autosaves ``autosave*.v3`` (e.g. ``autosave.v3``)."""
    return path.name.lower().startswith("autosave")


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

    def strategy(
        self,
        player_tag: str | None = None,
        horizon: int | None = None,
        capacity: float | None = None,
        objective: str | None = None,
        effort: int | None = None,
        solvency_policy: str | None = None,
        solvency_buffer_weeks: float | None = None,
    ) -> dict[str, Any] | None:
        """Run the advanced optimizer/forecaster on demand (it's not cheap, so
        it's separate from the per-refresh ``analyse_all``)."""
        snap = self.store.latest(player_tag)
        if snap is None or self.defs is None:
            return None
        history = self.store.history(snap.player_tag)
        opt = self.cfg.optimize
        if objective:
            opt = replace(opt, objective=objective)
        if effort is not None:
            opt = replace(opt, search_effort=max(0, effort))
        if horizon is not None:
            opt = replace(opt, horizon_months=max(6, horizon))
        if solvency_policy:
            opt = replace(opt, solvency_policy=solvency_policy)
        if solvency_buffer_weeks is not None:
            opt = replace(opt, solvency_buffer_weeks=max(0.0, solvency_buffer_weeks))
        with self._lock:
            report = build_strategy(
                snap, self.defs, opt, history=history, capacity=capacity
            )
        return _ser(report)

    # --- save discovery ----------------------------------------------------

    def list_saves(self) -> list[dict[str, Any]]:
        """All ``.v3`` saves in ``save_dir``, newest first.

        Autosaves and manual saves are both included; ``is_autosave`` flags the
        former (Vic3 names them ``autosave*.v3``) so the UI can tell them apart.
        """
        save_dir = self.cfg.paths.save_dir
        if save_dir is None or not Path(save_dir).is_dir():
            return []
        saves = []
        for p in Path(save_dir).rglob("*.v3"):
            try:
                st = p.stat()
            except OSError:
                continue
            saves.append(
                {
                    "path": str(p),
                    "name": p.name,
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                    "is_autosave": is_autosave(p),
                }
            )
        saves.sort(key=lambda s: s["mtime"], reverse=True)
        return saves

    def latest_save_path(self, autosave_only: bool = False) -> str | None:
        saves = self.list_saves()
        if autosave_only:
            saves = [s for s in saves if s["is_autosave"]]
        return saves[0]["path"] if saves else None

    # --- save watching -----------------------------------------------------

    @property
    def watching(self) -> bool:
        return self._observer is not None

    def start_watcher(self) -> bool:
        """Begin watching ``save_dir`` for new saves. Returns whether it ran."""
        if self._observer is not None:
            return True
        save_dir = self.cfg.paths.save_dir
        if save_dir is None or not Path(save_dir).is_dir():
            return False
        try:
            from watchdog.observers import Observer

            from .watcher import SaveHandler
        except Exception:  # noqa: BLE001
            return False
        accept = is_autosave if self.cfg.watch_mode == "autosave" else None
        handler = SaveHandler(self._on_new_save, accept=accept)
        obs = Observer()
        obs.schedule(handler, str(save_dir), recursive=True)
        obs.daemon = True
        obs.start()
        self._observer = obs
        return True

    def stop_watcher(self) -> None:
        obs = self._observer
        if obs is not None:
            self._observer = None
            obs.stop()

    def set_auto_watch(self, enabled: bool) -> bool:
        """Toggle continuous watching at runtime. Returns the effective state.

        Enabling also seeds from the newest save already in the folder, since
        the observer itself only reacts to saves created/modified afterwards.
        """
        self.cfg.auto_watch = enabled
        if enabled:
            if self.start_watcher():
                self.ingest_latest_existing()
        else:
            self.stop_watcher()
        return self.watching

    def set_watch_mode(self, mode: str) -> str:
        """Set which saves the watcher reacts to ("any"/"autosave").

        Restarts the watcher if it is running so the new filter takes effect.
        """
        self.cfg.watch_mode = "autosave" if mode == "autosave" else "any"
        if self.watching:
            self.stop_watcher()
            self.start_watcher()
        return self.cfg.watch_mode

    def _on_new_save(self, path: str) -> None:
        try:
            self.ingest(path)
        except Exception:  # noqa: BLE001
            self.last_error = traceback.format_exc(limit=3)

    def analyse_latest(self, autosave_only: bool = False) -> str:
        """Ingest the newest save in ``save_dir`` on demand. Returns its date.

        With ``autosave_only`` it picks the newest autosave rather than the
        newest save of any kind.
        """
        path = self.latest_save_path(autosave_only=autosave_only)
        if path is None:
            kind = "autosaves" if autosave_only else ".v3 saves"
            raise RuntimeError(
                f"No {kind} found in {self.cfg.paths.save_dir or '(no save_dir set)'}."
            )
        return self.ingest(path)

    def ingest_latest_existing(self) -> None:
        """On startup, ingest the newest save already in the folder.

        Honours ``watch_mode`` so an autosave-only watcher seeds from the
        latest autosave rather than a stray manual save.
        """
        path = self.latest_save_path(autosave_only=self.cfg.watch_mode == "autosave")
        if path is not None:
            self._on_new_save(path)


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or load_config()
    state = AppState(cfg)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if cfg.auto_watch:
            state.ingest_latest_existing()
            state.start_watcher()
        yield
        state.stop_watcher()

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
            "auto_watch": state.cfg.auto_watch,
            "watching": state.watching,
            "watch_mode": state.cfg.watch_mode,
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

    @app.get("/api/strategy")
    def strategy(
        player_tag: str | None = Query(default=None),
        horizon: int | None = Query(default=None),
        capacity: float | None = Query(default=None),
        objective: str | None = Query(default=None),
        effort: int | None = Query(default=None),
        solvency_policy: str | None = Query(default=None),
        solvency_buffer_weeks: float | None = Query(default=None),
    ) -> Any:
        """Growth-maximizing build plan + forecast for the latest snapshot.

        Parameters override the ``[optimize]`` config for this run so the
        dashboard can re-plan with a different horizon, capacity, objective,
        solvency policy or search effort.
        """
        try:
            data = state.strategy(
                player_tag,
                horizon,
                capacity,
                objective,
                effort,
                solvency_policy,
                solvency_buffer_weeks,
            )
        except Exception as exc:  # noqa: BLE001 - surface optimizer errors to UI
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if data is None:
            raise HTTPException(
                status_code=503,
                detail=state.defs_error or "No snapshot yet. Ingest a save first.",
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

    @app.get("/api/saves")
    def saves() -> Any:
        """List available .v3 saves (newest first) for on-demand analysis."""
        return JSONResponse(state.list_saves())

    @app.post("/api/analyse-latest")
    def analyse_latest(autosave_only: bool = Query(default=False)) -> dict[str, str]:
        """Analyse the most recent save now (game start, major event, …).

        With ``autosave_only=true`` it analyses the latest autosave instead of
        the latest save of any kind.
        """
        try:
            date = state.analyse_latest(autosave_only=autosave_only)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ingested": date}

    @app.get("/api/settings")
    def get_settings() -> dict[str, Any]:
        return {
            "auto_watch": state.cfg.auto_watch,
            "watching": state.watching,
            "watch_mode": state.cfg.watch_mode,
            "save_dir": str(cfg.paths.save_dir) if cfg.paths.save_dir else None,
        }

    @app.post("/api/settings")
    def set_settings(
        auto_watch: bool | None = Query(default=None),
        watch_mode: str | None = Query(default=None),
    ) -> dict[str, Any]:
        if watch_mode is not None:
            state.set_watch_mode(watch_mode)
        if auto_watch is not None:
            state.set_auto_watch(auto_watch)
        return {
            "auto_watch": state.cfg.auto_watch,
            "watching": state.watching,
            "watch_mode": state.cfg.watch_mode,
        }

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
