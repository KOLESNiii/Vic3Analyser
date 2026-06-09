"""Configuration loading and path auto-detection.

Reads ``config.toml`` (path overridable via the ``VIC3ANALYSER_CONFIG`` env var)
and fills in sensible defaults by probing common install/save locations across
Linux, Windows and macOS.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    import tomli as tomllib

from pathlib import Path

DEFAULT_CONFIG_NAME = "config.toml"


@dataclass
class Paths:
    vic3_install: Path | None
    save_dir: Path | None
    mod_dirs: list[Path]
    rakaly_bin: Path | None
    data_dir: Path


@dataclass
class Config:
    paths: Paths
    player_tag: str | None
    host: str = "127.0.0.1"
    port: int = 8000
    # Directory the config file lives in; relative paths resolve against it.
    root: Path = field(default_factory=Path.cwd)

    @property
    def common_dir(self) -> Path | None:
        """The active game ``common/`` directory (base game)."""
        if self.paths.vic3_install is None:
            return None
        # Steam layout: <install>/game/common ; some layouts: <install>/common
        for candidate in (
            self.paths.vic3_install / "game" / "common",
            self.paths.vic3_install / "common",
        ):
            if candidate.is_dir():
                return candidate
        return None


# --- auto-detection ---------------------------------------------------------

def _home() -> Path:
    return Path.home()


def _candidate_installs() -> list[Path]:
    home = _home()
    cands: list[Path] = []
    if sys.platform.startswith("linux"):
        cands += [
            home / ".steam/steam/steamapps/common/Victoria 3",
            home / ".local/share/Steam/steamapps/common/Victoria 3",
            home / ".var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/Victoria 3",
        ]
    elif sys.platform == "darwin":
        cands += [
            home / "Library/Application Support/Steam/steamapps/common/Victoria 3",
        ]
    elif sys.platform.startswith("win"):
        cands += [
            Path("C:/Program Files (x86)/Steam/steamapps/common/Victoria 3"),
            Path("C:/Program Files/Steam/steamapps/common/Victoria 3"),
        ]
    return cands


def _candidate_save_dirs() -> list[Path]:
    home = _home()
    pdx = "Paradox Interactive/Victoria 3/save games"
    cands: list[Path] = []
    if sys.platform.startswith("linux"):
        cands += [
            home / ".local/share" / pdx,
            home / "Documents" / pdx,
            # Proton / Steam compatdata path is install-specific; skip auto-probe.
        ]
    elif sys.platform == "darwin":
        cands += [home / "Documents" / pdx]
    elif sys.platform.startswith("win"):
        cands += [home / "Documents" / pdx]
    return cands


def _first_existing(cands: list[Path]) -> Path | None:
    for c in cands:
        if c.exists():
            return c
    return None


# --- loading ----------------------------------------------------------------

def _resolve(root: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (root / p)


def load_config(config_path: str | os.PathLike[str] | None = None) -> Config:
    """Load configuration, applying auto-detection for any blank paths."""
    if config_path is None:
        config_path = os.environ.get("VIC3ANALYSER_CONFIG", DEFAULT_CONFIG_NAME)
    cfg_file = Path(config_path).expanduser()
    root = cfg_file.parent.resolve() if cfg_file.exists() else Path.cwd()

    data: dict = {}
    if cfg_file.exists():
        with cfg_file.open("rb") as fh:
            data = tomllib.load(fh)

    p = data.get("paths", {})
    game = data.get("game", {})
    server = data.get("server", {})

    install = p.get("vic3_install") or ""
    install_path = _resolve(root, install) if install else _first_existing(_candidate_installs())

    save = p.get("save_dir") or ""
    save_path = _resolve(root, save) if save else _first_existing(_candidate_save_dirs())

    rakaly = p.get("rakaly_bin") or ""
    if rakaly:
        rakaly_path: Path | None = _resolve(root, rakaly)
    else:
        found = shutil.which("rakaly")
        rakaly_path = Path(found) if found else None

    mod_dirs = [_resolve(root, m) for m in p.get("mod_dirs", [])]
    data_dir = _resolve(root, p.get("data_dir") or ".vic3analyser")

    return Config(
        paths=Paths(
            vic3_install=install_path,
            save_dir=save_path,
            mod_dirs=mod_dirs,
            rakaly_bin=rakaly_path,
            data_dir=data_dir,
        ),
        player_tag=(game.get("player_tag") or None),
        host=server.get("host", "127.0.0.1"),
        port=int(server.get("port", 8000)),
        root=root,
    )
