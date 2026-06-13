"""Production-method optimisation — the counterfactual core.

For each of the player's buildings, look at every PM group it has. Within a
group only one PM is active. Enumerate the alternative PMs in that group,
**gated by researched technology**, value each one's goods flow at current
market prices, and recommend switching to the highest value-added PM.

This is exactly the "which automations / developments are best right now"
question, and it's something in-game scripting can't compute because it
requires evaluating PMs the building is *not* currently running.

Value-added here is per workforce-scaled unit (see ``pricing``), so it is a
sound *relative* signal between PMs in the same slot. Labour-mix changes
(e.g. automation swapping laborers for machinists, or adding engines that burn
coal) are captured to the extent they appear as goods in/out modifiers; a note
flags PMs that change which goods are consumed.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..extract.models import Building, Snapshot
from ..ingest.defs import GameDefs
from .pricing import market_map, reduces_capacity, value_goods


@dataclass
class PMOption:
    pm: str
    value_added: float
    available: bool  # unlocked by researched tech
    locked_by: list[str]  # techs needed if not available
    missing_prices: list[str]


@dataclass
class PMRecommendation:
    building_id: int | None
    building_type: str
    state_id: int | None
    group: str
    current_pm: str | None
    current_value: float | None
    best_pm: str
    best_value: float
    delta_per_level: float
    delta_total: float  # scaled by building level
    options: list[PMOption]


def _pm_value(pm: str, defs: GameDefs, market) -> tuple[float, list[str]]:
    flows = defs.pm_goods(pm)
    gv = value_goods(flows["input"], flows["output"], market, defs.good_base_price)
    return gv.value_added, gv.missing_prices


def _is_available(pm: str, researched: set[str], defs: GameDefs) -> tuple[bool, list[str]]:
    needed = defs.pm_unlocking_techs(pm)
    missing = [t for t in needed if t not in researched]
    return (len(missing) == 0), missing


def _active_pm_in_group(b: Building, group_pms: set[str]) -> str | None:
    for apm in b.active_pms:
        if apm.pm in group_pms:
            return apm.pm
    return None


def optimise_building(b: Building, snap: Snapshot, defs: GameDefs) -> list[PMRecommendation]:
    market = market_map(snap)
    researched = set(snap.tech.researched)
    recs: list[PMRecommendation] = []

    for group in defs.building_pm_groups(b.building_type):
        pms = defs.group_pms(group)
        if not pms:
            continue
        group_set = set(pms)
        current = _active_pm_in_group(b, group_set)

        options: list[PMOption] = []
        for pm in pms:
            value, missing = _pm_value(pm, defs, market)
            avail, locked_by = _is_available(pm, researched, defs)
            options.append(
                PMOption(
                    pm=pm,
                    value_added=value,
                    available=avail,
                    locked_by=locked_by,
                    missing_prices=missing,
                )
            )

        current_value = next(
            (o.value_added for o in options if o.pm == current), None
        )
        # Best switchable option is among currently-available PMs — but never one
        # that sacrifices a non-goods capacity (bureaucracy, tax capacity, …) the
        # current PM provides. Those have no market price, so the goods-only score
        # would otherwise "improve" a government_administration by dropping to a
        # paper-free PM, collapsing administration and the tax revenue it backs.
        available_opts = [
            o
            for o in options
            if o.available and not reduces_capacity(o.pm, current, defs)
        ]
        if not available_opts:
            continue
        best = max(available_opts, key=lambda o: o.value_added)
        if current is not None and best.pm == current:
            continue  # already optimal among available
        base = current_value if current_value is not None else 0.0
        delta = best.value_added - base
        if delta <= 0:
            continue
        recs.append(
            PMRecommendation(
                building_id=b.id,
                building_type=b.building_type,
                state_id=b.state_id,
                group=group,
                current_pm=current,
                current_value=current_value,
                best_pm=best.pm,
                best_value=best.value_added,
                delta_per_level=delta,
                delta_total=delta * max(b.level, 1),
                options=sorted(options, key=lambda o: o.value_added, reverse=True),
            )
        )
    return recs


def analyse_pm_switches(snap: Snapshot, defs: GameDefs) -> list[PMRecommendation]:
    """All profitable PM switches for the player, biggest total gain first."""
    recs: list[PMRecommendation] = []
    for b in snap.buildings:
        recs.extend(optimise_building(b, snap, defs))
    recs.sort(key=lambda r: r.delta_total, reverse=True)
    return recs
