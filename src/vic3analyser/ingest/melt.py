"""Turn a Victoria 3 ``.v3`` save into plaintext we can parse.

A ``.v3`` save can be:

* **plaintext** (``save_file_format = "text"`` in ``pdx_settings.json``) — read
  directly, no external tool needed;
* a **zip** container holding ``meta`` + ``gamestate`` members, which may
  themselves be plaintext or binary-tokenised;
* a **binary** save (default ``zip_binary_all``, including ironman) — needs the
  `rakaly <https://github.com/rakaly/cli>`_ melter to convert tokens to text.

This module decides which case applies and returns plaintext for the gamestate
(and, when available, the meta block).

.. note::
   The exact byte layout of the ``.v3`` header is version-specific and best
   confirmed against a real save (see the Phase 1 schema-discovery task). The
   heuristics here are conservative: anything that doesn't clearly look like
   text is handed to ``rakaly``, which understands the container and binary
   tokens natively.
"""

from __future__ import annotations

import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..config import Config

# Tokens that strongly indicate we're looking at melted/plaintext PDX content.
_TEXT_MARKERS = (b"=", b"{")


class MeltError(RuntimeError):
    """Raised when a save cannot be converted to plaintext."""


@dataclass
class MeltResult:
    gamestate: str
    meta: str | None
    source: str  # "plaintext" | "zip-text" | "rakaly"


def _looks_like_text(sample: bytes) -> bool:
    """Heuristic: does this byte sample look like plaintext PDX script?"""
    if not sample:
        return False
    if b"\x00" in sample:
        return False
    # Require both an assignment and a block to avoid false positives.
    if not all(m in sample for m in _TEXT_MARKERS):
        return False
    # Mostly printable / whitespace?
    printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126)
    return printable / len(sample) > 0.85


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _run_rakaly(path: Path, cfg: Config) -> str:
    rakaly = cfg.paths.rakaly_bin
    if rakaly is None:
        raise MeltError(
            "Save appears to be binary/ironman but the `rakaly` melter was not "
            "found. Install it (https://github.com/rakaly/cli) and put it on "
            "PATH or set paths.rakaly_bin in config.toml — or set "
            'save_file_format = "text" in your Victoria 3 pdx_settings.json.'
        )
    cmd = [
        str(rakaly),
        "melt",
        "--to-stdout",
        "--format",
        "vic3",
        "--unknown-key",
        "stringify",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
    except FileNotFoundError as exc:  # rakaly path invalid
        raise MeltError(f"Could not execute rakaly at {rakaly}: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "replace")[:2000]
        raise MeltError(f"rakaly melt failed (exit {exc.returncode}): {stderr}") from exc
    return _decode(proc.stdout)


def melt_save(path: str | Path, cfg: Config) -> MeltResult:
    """Return plaintext gamestate (and meta if present) for a ``.v3`` save."""
    p = Path(path)
    if not p.exists():
        raise MeltError(f"Save file not found: {p}")

    with p.open("rb") as fh:
        head = fh.read(8192)

    # Case 1: zip container (default binary saves are zips of meta+gamestate).
    if head[:2] == b"PK":
        return _melt_zip(p, cfg)

    # Case 2: already-plaintext save (possibly with a short textual header).
    if _looks_like_text(head):
        text = _decode(p.read_bytes())
        return MeltResult(gamestate=text, meta=None, source="plaintext")

    # Case 3: binary, hand to rakaly.
    return MeltResult(gamestate=_run_rakaly(p, cfg), meta=None, source="rakaly")


def _melt_zip(p: Path, cfg: Config) -> MeltResult:
    with zipfile.ZipFile(p) as zf:
        names = set(zf.namelist())
        gamestate_name = _pick(names, "gamestate")
        meta_name = _pick(names, "meta")
        if gamestate_name is None:
            # Unexpected layout; let rakaly try the whole file.
            return MeltResult(gamestate=_run_rakaly(p, cfg), meta=None, source="rakaly")

        gs_bytes = zf.read(gamestate_name)
        meta_bytes = zf.read(meta_name) if meta_name else b""

    if _looks_like_text(gs_bytes[:8192]):
        return MeltResult(
            gamestate=_decode(gs_bytes),
            meta=_decode(meta_bytes) if meta_bytes else None,
            source="zip-text",
        )

    # Binary members inside the zip: rakaly understands the .v3 container.
    return MeltResult(gamestate=_run_rakaly(p, cfg), meta=None, source="rakaly")


def _pick(names: set[str], wanted: str) -> str | None:
    if wanted in names:
        return wanted
    for n in names:
        if n.rsplit("/", 1)[-1] == wanted:
            return n
    return None
