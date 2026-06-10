"""Load the static game-rule definitions from a Victoria 3 ``common/`` tree.

These rarely change (only on a game patch or mod update), so the parsed result
is cached to ``data_dir`` keyed by the source files' mtimes.

The categories the analyser needs:

* ``goods`` — base prices and categories (``common/goods``)
* ``production_methods`` — per-PM goods inputs/outputs, employment, tech gating
  (``common/production_methods``)
* ``production_method_groups`` — which PMs are mutually exclusive within a slot
  (``common/production_method_groups``)
* ``building_types`` — buildings and the PM groups they use
  (``common/building_types``)
* ``technologies`` — research and what it unlocks
  (``common/technology/technologies``)

Field names follow Victoria 3's modifier conventions
(``goods_input_<good>_add`` / ``goods_output_<good>_add``); the helpers below
read them defensively so a patch that renames a peripheral field degrades
gracefully rather than crashing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Config
from .parser import as_list, parse_file

# category -> path relative to the common/ dir. NB: building *types* are defined
# under common/buildings/ (not common/building_types/).
_CATEGORY_DIRS = {
    "goods": "goods",
    "production_methods": "production_methods",
    "production_method_groups": "production_method_groups",
    "building_types": "buildings",
    "technologies": "technology/technologies",
    "script_values": "script_values",
}

# Categories whose entries are scalars (named constants) rather than blocks.
_SCALAR_CATEGORIES = frozenset({"script_values"})

_CACHE_VERSION = 4


@dataclass
class GameDefs:
    goods: dict[str, dict] = field(default_factory=dict)
    production_methods: dict[str, dict] = field(default_factory=dict)
    production_method_groups: dict[str, dict] = field(default_factory=dict)
    building_types: dict[str, dict] = field(default_factory=dict)
    technologies: dict[str, dict] = field(default_factory=dict)
    # Named numeric constants from common/script_values (e.g. building costs are
    # given as aliases like ``construction_cost_very_high = 800``).
    script_values: dict[str, float] = field(default_factory=dict)
    # Static state-region definitions from map_data/state_regions, keyed by
    # region name (e.g. ``STATE_PROVENCE``). Source of land/resource capacity:
    # ``arable_land`` (total), ``arable_resources`` (building types that draw on
    # it), ``capped_resources`` (per-building-type level caps).
    state_regions: dict[str, dict] = field(default_factory=dict)

    # --- convenience accessors -------------------------------------------

    def good_base_price(self, good: str) -> float | None:
        g = self.goods.get(good)
        if not g:
            return None
        for key in ("cost", "base_price", "price"):
            if key in g:
                try:
                    return float(g[key])
                except (TypeError, ValueError):
                    return None
        return None

    def good_traded_quantity(self, good: str) -> float | None:
        """Reference market depth for a good (``goods.<g>.traded_quantity``).

        This is the per-trade-route volume the game uses to scale a good's
        market, so it is the natural anchor for how much added supply/demand
        moves the price. Player-derivable (it's a static game rule).
        """
        g = self.goods.get(good)
        if not g:
            return None
        try:
            return float(g["traded_quantity"])
        except (KeyError, TypeError, ValueError):
            return None

    def good_category(self, good: str) -> str | None:
        g = self.goods.get(good)
        return str(g["category"]) if isinstance(g, dict) and "category" in g else None

    def good_tradeable(self, good: str) -> bool:
        """Whether a good is tradeable (defaults to True, as most are)."""
        g = self.goods.get(good)
        if not isinstance(g, dict) or "tradeable" not in g:
            return True
        val = g["tradeable"]
        return not (val in (False, "no", "false", 0, "0"))

    def building_construction_cost(self, building: str) -> float | None:
        """Total construction points to build one level (``required_construction``).

        The value is usually a named alias (``construction_cost_very_high``)
        defined in ``common/script_values``; resolve it through there. A literal
        number is returned directly.
        """
        bt = self.building_types.get(building, {})
        for key in ("required_construction", "construction_cost", "cost"):
            if key not in bt:
                continue
            return self.resolve_value(bt[key])
        return None

    def resolve_value(self, value: Any) -> float | None:
        """Resolve a number or a script-value alias to a float."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            sv = self.script_values.get(value)
            if isinstance(sv, (int, float)) and not isinstance(sv, bool):
                return float(sv)
        return None

    def pm_employment(self, pm_name: str) -> dict[str, float]:
        """Per-level employment a PM adds, keyed by pop type.

        Reads ``building_employment_<poptype>_add`` modifiers (the same scopes
        as :meth:`pm_goods`). Used for labour demand and a standard-of-living
        proxy (more salaried jobs lifts SoL).
        """
        pm = self.production_methods.get(pm_name, {})
        out: dict[str, float] = {}
        mods = pm.get("building_modifiers", {})
        for scope_key in ("workforce_scaled", "level_scaled", "unscaled"):
            scope = mods.get(scope_key)
            if not isinstance(scope, dict):
                continue
            for mod_key, value in scope.items():
                if not isinstance(value, (int, float)):
                    continue
                pop = _good_from_modifier(mod_key, "building_employment_", "_add")
                if pop is not None:
                    out[pop] = out.get(pop, 0.0) + float(value)
        return out

    def pm_goods(self, pm_name: str) -> dict[str, dict[str, float]]:
        """Return ``{"input": {good: qty}, "output": {good: qty}}`` for a PM.

        Reads the ``workforce_scaled`` (and ``level_scaled``) goods modifiers,
        which express the per-level throughput before price/throughput
        multipliers are applied.
        """
        pm = self.production_methods.get(pm_name, {})
        inputs: dict[str, float] = {}
        outputs: dict[str, float] = {}
        mods = pm.get("building_modifiers", {})
        scopes = []
        for scope_key in ("workforce_scaled", "level_scaled", "unscaled"):
            scope = mods.get(scope_key)
            if isinstance(scope, dict):
                scopes.append(scope)
        for scope in scopes:
            for mod_key, value in scope.items():
                if not isinstance(value, (int, float)):
                    continue
                good = _good_from_modifier(mod_key, "goods_input_", "_add")
                if good is not None:
                    inputs[good] = inputs.get(good, 0.0) + float(value)
                    continue
                good = _good_from_modifier(mod_key, "goods_output_", "_add")
                if good is not None:
                    outputs[good] = outputs.get(good, 0.0) + float(value)
        return {"input": inputs, "output": outputs}

    def pm_unlocking_techs(self, pm_name: str) -> list[str]:
        """Technologies that unlock a PM (``unlocking_technologies``)."""
        pm = self.production_methods.get(pm_name, {})
        return [str(t) for t in as_list(pm.get("unlocking_technologies"))]

    def building_pm_groups(self, building: str) -> list[str]:
        bt = self.building_types.get(building, {})
        return [str(g) for g in as_list(bt.get("production_method_groups"))]

    def building_unlocking_techs(self, building: str) -> list[str]:
        """Technologies required before this building type can be built."""
        bt = self.building_types.get(building, {})
        return [str(t) for t in as_list(bt.get("unlocking_technologies"))]

    def group_pms(self, group: str) -> list[str]:
        grp = self.production_method_groups.get(group, {})
        return [str(p) for p in as_list(grp.get("production_methods"))]

    # --- state-region capacity (from map_data/state_regions) -------------

    def region_arable(self, region: str | None) -> float | None:
        r = self.state_regions.get(region or "")
        if not isinstance(r, dict) or "arable_land" not in r:
            return None
        try:
            return float(r["arable_land"])
        except (TypeError, ValueError):
            return None

    def region_arable_buildings(self, region: str | None) -> list[str]:
        r = self.state_regions.get(region or "", {})
        return [str(b) for b in as_list(r.get("arable_resources"))]

    def region_capped_resources(self, region: str | None) -> dict[str, float]:
        """Per-building-type level caps (mines/logging/fishing/…) in a region."""
        r = self.state_regions.get(region or "", {})
        capped = r.get("capped_resources") if isinstance(r, dict) else None
        out: dict[str, float] = {}
        if isinstance(capped, dict):
            for bt, n in capped.items():
                try:
                    out[str(bt)] = float(n)
                except (TypeError, ValueError):
                    continue
        return out


def _good_from_modifier(mod_key: str, prefix: str, suffix: str) -> str | None:
    if mod_key.startswith(prefix) and mod_key.endswith(suffix):
        return mod_key[len(prefix) : -len(suffix)]
    return None


# --- loading ----------------------------------------------------------------

def _common_roots(cfg: Config) -> list[Path]:
    roots: list[Path] = []
    if cfg.common_dir is not None:
        roots.append(cfg.common_dir)
    # Mod overlays: each mod_dir may itself contain a common/ subdir.
    for mod in cfg.paths.mod_dirs:
        for candidate in (mod / "common", mod):
            if candidate.is_dir():
                roots.append(candidate)
                break
    return roots


def _category_files(roots: list[Path], category: str) -> list[Path]:
    rel = _CATEGORY_DIRS[category]
    files: list[Path] = []
    for root in roots:
        cat_dir = root / rel
        if cat_dir.is_dir():
            files.extend(sorted(cat_dir.rglob("*.txt")))
    return files


def _state_region_dirs(cfg: Config) -> list[Path]:
    """`map_data/state_regions` dirs (base install + mod overlays).

    Unlike the other categories these live under ``map_data`` (a sibling of
    ``common``), not under ``common`` itself.
    """
    dirs: list[Path] = []
    if cfg.common_dir is not None:
        cand = cfg.common_dir.parent / "map_data" / "state_regions"
        if cand.is_dir():
            dirs.append(cand)
    for mod in cfg.paths.mod_dirs:
        for base in (mod, mod / "game"):
            cand = base / "map_data" / "state_regions"
            if cand.is_dir():
                dirs.append(cand)
                break
    return dirs


def _state_region_files(cfg: Config) -> list[Path]:
    files: list[Path] = []
    for d in _state_region_dirs(cfg):
        files.extend(sorted(d.rglob("*.txt")))
    return files


def _load_category(files: list[Path]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for f in files:
        try:
            parsed = parse_file(f)
        except Exception:  # noqa: BLE001 - skip an unparsable def file, keep going
            continue
        for key, value in parsed.items():
            if isinstance(value, dict):
                merged[key] = value  # later file / mod overlay wins
    return merged


def _load_scalars(files: list[Path]) -> dict[str, float]:
    """Load top-level numeric constants (script_values). Non-numeric (math
    expressions, blocks) are skipped — the analyser only needs plain numbers."""
    merged: dict[str, float] = {}
    for f in files:
        try:
            parsed = parse_file(f)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(parsed, dict):
            continue
        for key, value in parsed.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                merged[key] = float(value)
    return merged


def _manifest(roots: list[Path], extra_files: list[Path] | None = None) -> dict[str, float]:
    man: dict[str, float] = {}
    files = [f for category in _CATEGORY_DIRS for f in _category_files(roots, category)]
    files += extra_files or []
    for f in files:
        try:
            man[str(f)] = f.stat().st_mtime
        except OSError:
            pass
    return man


def load_defs(cfg: Config, use_cache: bool = True) -> GameDefs:
    """Load (and cache) the game definitions referenced by ``cfg``."""
    roots = _common_roots(cfg)
    if not roots:
        raise FileNotFoundError(
            "No Victoria 3 common/ directory found. Set paths.vic3_install in "
            "config.toml to the game install folder."
        )

    cache_path = cfg.paths.data_dir / "defs_cache.json"
    region_files = _state_region_files(cfg)
    manifest = _manifest(roots, region_files)

    if use_cache and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text("utf-8"))
            if (
                cached.get("version") == _CACHE_VERSION
                and cached.get("manifest") == manifest
            ):
                return GameDefs(**cached["defs"])
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    defs = GameDefs(
        goods=_load_category(_category_files(roots, "goods")),
        production_methods=_load_category(_category_files(roots, "production_methods")),
        production_method_groups=_load_category(
            _category_files(roots, "production_method_groups")
        ),
        building_types=_load_category(_category_files(roots, "building_types")),
        technologies=_load_category(_category_files(roots, "technologies")),
        script_values=_load_scalars(_category_files(roots, "script_values")),
        state_regions=_load_category(region_files),
    )

    if use_cache:
        _write_cache(cache_path, manifest, defs)
    return defs


def _write_cache(cache_path: Path, manifest: dict[str, float], defs: GameDefs) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "version": _CACHE_VERSION,
        "manifest": manifest,
        "defs": {
            "goods": defs.goods,
            "production_methods": defs.production_methods,
            "production_method_groups": defs.production_method_groups,
            "building_types": defs.building_types,
            "technologies": defs.technologies,
            "script_values": defs.script_values,
            "state_regions": defs.state_regions,
        },
    }
    tmp = cache_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload), "utf-8")
    tmp.replace(cache_path)
