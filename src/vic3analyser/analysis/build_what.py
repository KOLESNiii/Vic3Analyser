"""What to build: rank building types by projected value-added at current
prices, weighted by how scarce their outputs are.

For each building type the player can build (at least one tech-unlocked PM per
group), pick the best available PM in each group, value its goods flow at
current market prices, and bias the score toward buildings whose outputs are in
shortage (and against those whose inputs are scarce). Buildings that produce no
priced goods (e.g. purely military) score zero and are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .pricing import market_map, shortage_score, value_goods


@dataclass
class BuildCandidate:
    building_type: str
    score: float  # demand-weighted value-added per level
    raw_value_added: float  # unweighted, per level
    best_pms: list[str]
    key_outputs: list[str]
    output_shortage: float  # mean shortage signal of outputs (>0 scarce)
    input_shortage: float  # mean shortage signal of inputs (>0 scarce/costly)
    notes: list[str] = field(default_factory=list)


def _best_available_pm(group_pms: list[str], researched: set[str], defs: GameDefs, market):
    best = None
    best_val = None
    for pm in group_pms:
        if any(t not in researched for t in defs.pm_unlocking_techs(pm)):
            continue
        flows = defs.pm_goods(pm)
        gv = value_goods(flows["input"], flows["output"], market, defs.good_base_price)
        if best_val is None or gv.value_added > best_val:
            best, best_val = pm, gv.value_added
    return best


def analyse_what_to_build(snap: Snapshot, defs: GameDefs) -> list[BuildCandidate]:
    market = market_map(snap)
    researched = set(snap.tech.researched)
    candidates: list[BuildCandidate] = []

    for btype in defs.building_types:
        groups = defs.building_pm_groups(btype)
        if not groups:
            continue
        # Gate on the building's *own* unlocking techs — not just its PMs'. A
        # building the player can't build yet is not an actionable suggestion.
        if any(t not in researched for t in defs.building_unlocking_techs(btype)):
            continue
        total_value = 0.0
        best_pms: list[str] = []
        all_outputs: dict[str, float] = {}
        all_inputs: dict[str, float] = {}
        buildable = True
        for group in groups:
            pm = _best_available_pm(defs.group_pms(group), researched, defs, market)
            if pm is None:
                buildable = False
                break
            best_pms.append(pm)
            flows = defs.pm_goods(pm)
            gv = value_goods(flows["input"], flows["output"], market, defs.good_base_price)
            total_value += gv.value_added
            for g, q in flows["output"].items():
                all_outputs[g] = all_outputs.get(g, 0.0) + q
            for g, q in flows["input"].items():
                all_inputs[g] = all_inputs.get(g, 0.0) + q

        if not buildable or not all_outputs:
            continue

        out_short = _mean_signal(all_outputs, market)
        in_short = _mean_signal(all_inputs, market)
        # Reward scarce outputs, penalise scarce/expensive inputs.
        score = total_value * (1.0 + out_short - 0.5 * in_short)

        notes: list[str] = []
        if out_short > 0.1:
            notes.append("outputs in shortage — strong demand")
        if in_short > 0.1:
            notes.append("inputs are scarce/expensive — may compete for supply")

        candidates.append(
            BuildCandidate(
                building_type=btype,
                score=score,
                raw_value_added=total_value,
                best_pms=best_pms,
                key_outputs=sorted(all_outputs, key=lambda g: all_outputs[g], reverse=True),
                output_shortage=out_short,
                input_shortage=in_short,
                notes=notes,
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _mean_signal(goods: dict[str, float], market) -> float:
    signals = []
    for g in goods:
        mg = market.get(g)
        if mg is not None:
            signals.append(shortage_score(mg))
    return sum(signals) / len(signals) if signals else 0.0


def producible_goods(snap: Snapshot, defs: GameDefs) -> set[str]:
    """Goods the player can actually produce now.

    A good is producible if some building the player can build (its unlocking
    techs are researched) has an available PM that outputs it. This is what
    separates a real shortage ("build a factory and cash in") from a fake one
    (aeroplanes in 1836 — pegged at the price ceiling because *nobody* can make
    them yet).
    """
    market = market_map(snap)
    researched = set(snap.tech.researched)
    out: set[str] = set()
    for btype in defs.building_types:
        if any(t not in researched for t in defs.building_unlocking_techs(btype)):
            continue
        for group in defs.building_pm_groups(btype):
            pm = _best_available_pm(defs.group_pms(group), researched, defs, market)
            if pm is None:
                continue
            out.update(defs.pm_goods(pm)["output"])
    return out
