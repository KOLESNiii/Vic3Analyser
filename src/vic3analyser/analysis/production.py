"""Throughput model: how much a building actually produces per level.

The base value-added model treats a PM's ``goods_*_add`` quantities as the flat
per-level flow. The game then scales that flow by a building's **throughput**
multiplier, which is the sum of several player-visible bonuses:

* **Economy of scale** — a per-level concentration bonus (``+1%`` throughput per
  building level above the start level, capped) that applies only to building
  groups flagged ``economy_of_scale`` (manufacturing, industry, agriculture …),
  never subsistence. Source: the ``economy_of_scale`` static modifier
  (``building_throughput_add = 0.01``) + ``ECONOMY_OF_SCALE_*`` defines.
* **Technology throughput** — researched techs that grant
  ``building_<type>_throughput_add`` or ``building_group_<group>_throughput_add``
  (and the global ``building_throughput_add``).
* **Law throughput** — the same modifier families coming from enacted laws.
* **PM throughput** — a PM's own ``building_throughput_add`` (and the one-sided
  ``building_goods_input_mult`` / ``building_goods_output_mult``).

Everything here is static-defs + the player's own researched techs / active
laws / building levels — nothing hidden. Each contribution is feature-flagged in
:class:`OptimizeConfig` so the model can be simplified or sped up.
"""

from __future__ import annotations

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs

_ECONOMIC_SYSTEM_GROUP = "lawgroup_economic_system"


def effective_active_laws(snap: Snapshot, defs: GameDefs, cfg: OptimizeConfig) -> list[str]:
    """The player's enacted laws, with the economic-system law swapped for
    ``cfg.assumed_economic_law`` when a scenario override is set.

    Lets the report answer "what if I switched to laissez-faire?" by replacing
    just the one law whose modifiers the model consumes.
    """
    laws = list(snap.country.active_laws or [])
    override = cfg.assumed_economic_law
    if not override:
        return laws
    laws = [l for l in laws if defs.law_group(l) != _ECONOMIC_SYSTEM_GROUP]
    laws.append(override)
    return laws

# economy_of_scale static modifier: building_throughput_add = 0.01 per qualifying
# level above the start level. Base level cap ~20 (code static modifier), which
# techs/principles extend; we approximate with the base cap (conservative).
_EOS_PER_LEVEL = 0.01
_EOS_BASE_CAP = 20.0

# Modifier-name fragments that denote a building throughput bonus.
_THROUGHPUT_GLOBAL = "building_throughput_add"


def economy_of_scale_bonus(
    building_type: str, levels: float, defs: GameDefs, cfg: OptimizeConfig
) -> float:
    """Throughput fraction from economy of scale at ``levels`` (0 if disabled).

    Modelled on a representative concentrated building of size ``levels`` capped
    at the scale cap — optimistic about concentration, which is the behaviour
    economy of scale rewards. Applied consistently to base and projected economy
    so the GDP *ratio* stays fair.
    """
    if not cfg.model_economy_of_scale or levels <= 0:
        return 0.0
    if not defs.building_has_economy_of_scale(building_type):
        return 0.0
    start = defs.define("NEconomy", "ECONOMY_OF_SCALE_START_LEVEL", 1.0) or 1.0
    effective = min(levels, _EOS_BASE_CAP) - start
    return max(0.0, effective) * _EOS_PER_LEVEL


def _modifier_throughput_for(
    building_type: str, mods: dict[str, float], defs: GameDefs
) -> float:
    """Sum throughput-add modifiers in ``mods`` that hit ``building_type``.

    Matches the global ``building_throughput_add``, the per-type
    ``building_<type>_throughput_add``, and per-group
    ``building_group_<group>_throughput_add`` for the type's group ancestry.
    """
    if not mods:
        return 0.0
    total = mods.get(_THROUGHPUT_GLOBAL, 0.0)
    # building_<type>_throughput_add — building_type already carries the
    # ``building_`` prefix, so the key is f"{building_type}_throughput_add".
    total += mods.get(f"{building_type}_throughput_add", 0.0)
    for group in defs.building_group_chain(building_type):
        total += mods.get(f"building_group_{group}_throughput_add", 0.0)
    return total


def tech_law_throughput_bonus(
    building_type: str,
    researched: set[str],
    active_laws: list[str],
    defs: GameDefs,
    cfg: OptimizeConfig,
) -> float:
    """Throughput fraction a building gets from researched techs + active laws."""
    if not cfg.model_throughput:
        return 0.0
    bonus = 0.0
    for tech in researched:
        mods = defs.tech_modifiers(tech)
        if mods:
            bonus += _modifier_throughput_for(building_type, mods, defs)
    if cfg.model_laws:
        for law in active_laws:
            mods = defs.law_modifiers(law)
            if mods:
                bonus += _modifier_throughput_for(building_type, mods, defs)
    return bonus


def building_throughput_bonus(
    building_type: str,
    levels: float,
    researched: set[str],
    active_laws: list[str],
    defs: GameDefs,
    cfg: OptimizeConfig,
) -> float:
    """Combined throughput *bonus fraction* for a building type (0 = none).

    ``0.2`` means +20%. Throughput scales a PM's whole flow (inputs *and*
    outputs), so this stacks additively with a PM's own throughput inside
    :func:`econ_model.pm_value_at`. Returned as a fraction (not ``1+``) so the
    consumers can add it to PM-level modifiers the Vic3 way.
    """
    bonus = economy_of_scale_bonus(building_type, levels, defs, cfg)
    bonus += tech_law_throughput_bonus(building_type, researched, active_laws, defs, cfg)
    return bonus


def throughput_bonus_by_type(
    holdings: dict[str, float],
    researched: set[str],
    active_laws: list[str],
    defs: GameDefs,
    cfg: OptimizeConfig,
) -> dict[str, float]:
    """Per-building-type throughput bonus fraction for a building multiset.

    Threaded cheaply through the equilibrium solve and value computation; a type
    absent from the map (or a ``None`` map) is treated as ``0.0`` by consumers.
    """
    return {
        btype: building_throughput_bonus(
            btype, levels, researched, active_laws, defs, cfg
        )
        for btype, levels in holdings.items()
    }
