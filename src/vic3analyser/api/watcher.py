"""Watchdog handler that fires on new/updated ``.v3`` saves.

Saves are large and written incrementally, so we debounce: wait until a file's
size has stopped changing before handing it to the ingest callback.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler


class SaveHandler(FileSystemEventHandler):
    def __init__(self, on_save: Callable[[str], None], settle_seconds: float = 2.0) -> None:
        self._on_save = on_save
        self._settle = settle_seconds
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._maybe(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._maybe(event)

    def _maybe(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = event.src_path
        if not path.endswith(".v3"):
            return
        with self._lock:
            already = path in self._pending
            self._pending[path] = time.time()
        if not already:
            threading.Thread(target=self._settle_and_fire, args=(path,), daemon=True).start()

    def _settle_and_fire(self, path: str) -> None:
        # Wait until the file size is stable and no newer event arrived.
        last_size = -1
        while True:
            time.sleep(self._settle)
            try:
                size = Path(path).stat().st_size
            except OSError:
                with self._lock:
                    self._pending.pop(path, None)
                return
            with self._lock:
                last_event = self._pending.get(path, 0)
            stable = size == last_size and (time.time() - last_event) >= self._settle
            last_size = size
            if stable:
                break
        with self._lock:
            self._pending.pop(path, None)
        self._on_save(path)
