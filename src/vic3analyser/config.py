"""Configuration loading and path auto-detection.

Reads ``config.toml`` (path overridable via the ``VIC3ANALYSER_CONFIG`` env var)
and fills in sensible defaults by probing common install/save locations across
Linux, Windows and macOS.
"""

from __future__ import annotations

import os
import re
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
    # When true, continuously watch ``save_dir`` and ingest new saves. When
    # false, analysis is on-demand only: trigger it from the Settings page
    # (e.g. once at game start, or after a major event). See ``[server]
    # auto_watch`` in config.toml.
    auto_watch: bool = True
    # Which saves the watcher reacts to: "any" (every new .v3, autosaves and
    # manual saves alike) or "autosave" (only Vic3's autosave*.v3 files).
    watch_mode: str = "any"
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

# Victoria 3's Steam application id, used to locate the game under
# ``steamapps/common`` and its Proton prefix under ``steamapps/compatdata``.
VIC3_APP_ID = "529340"
GAME_FOLDER = "Victoria 3"
# Tail of the save-games path relative to a (Windows) "Documents" folder.
SAVE_TAIL = Path("Paradox Interactive/Victoria 3/save games")


def _home() -> Path:
    return Path.home()


def _steam_roots() -> list[Path]:
    """Base Steam install directories to probe, OS-dependent."""
    home = _home()
    if sys.platform.startswith("linux"):
        return [
            home / ".steam/steam",
            home / ".steam/root",
            home / ".local/share/Steam",
            home / ".var/app/com.valvesoftware.Steam/data/Steam",
        ]
    if sys.platform == "darwin":
        return [home / "Library/Application Support/Steam"]
    if sys.platform.startswith("win"):
        return [
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
        ]
    return []


def _steam_libraries() -> list[Path]:
    """All Steam library folders, including extra drives/dirs the user added.

    Each Steam install records every library folder in
    ``steamapps/libraryfolders.vdf``; games may live in any of them rather than
    the primary install. We parse the (loosely-structured) VDF for ``"path"``
    entries and always include the roots themselves as a fallback.
    """
    libs: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp not in seen:
            seen.add(rp)
            libs.append(p)

    for root in _steam_roots():
        add(root)
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        try:
            text = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Lines look like:   "path"   "/mnt/games/SteamLibrary"
        for match in re.finditer(r'"path"\s*"([^"]+)"', text):
            add(Path(match.group(1).replace("\\\\", "/").replace("\\", "/")))
    return libs


def _candidate_installs() -> list[Path]:
    cands: list[Path] = []
    for lib in _steam_libraries():
        cands.append(lib / "steamapps" / "common" / GAME_FOLDER)
    return cands


def _proton_documents() -> list[Path]:
    """`Documents` folders inside the Proton/Wine prefix for Victoria 3.

    When the Windows build runs through Proton on Linux, the game writes saves
    into its compatdata prefix rather than the native ``~/.local/share`` tree.
    """
    docs: list[Path] = []
    users = ("steamuser", os.environ.get("USER") or "")
    for lib in _steam_libraries():
        pfx = lib / "steamapps" / "compatdata" / VIC3_APP_ID / "pfx" / "drive_c" / "users"
        for user in users:
            if user:
                docs.append(pfx / user / "Documents")
    return docs


def _candidate_save_dirs() -> list[Path]:
    home = _home()
    cands: list[Path] = []
    if sys.platform.startswith("linux"):
        # Native Linux build writes here ...
        cands += [
            home / ".local/share" / SAVE_TAIL,
            home / "Documents" / SAVE_TAIL,
        ]
        # ... while the Windows build under Proton writes into its prefix.
        cands += [docs / SAVE_TAIL for docs in _proton_documents()]
    elif sys.platform == "darwin":
        cands += [home / "Documents" / SAVE_TAIL]
    elif sys.platform.startswith("win"):
        cands += [home / "Documents" / SAVE_TAIL]
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
        auto_watch=bool(server.get("auto_watch", True)),
        watch_mode=("autosave" if server.get("watch_mode") == "autosave" else "any"),
        root=root,
    )
