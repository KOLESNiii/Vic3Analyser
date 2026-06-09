"""Per-building profitability ranking for the player's buildings.

Prefers the real weekly figures the game reports (``weekly_income``/
``weekly_expense`` from the building tooltip). When those aren't present in the
save, falls back to estimating value-added from the building's active PMs'
goods flows valued at current market prices (a relative estimate, not the exact
in-game number — flagged via ``estimated``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..extract.models import Building, Snapshot
from ..ingest.defs import GameDefs
from .pricing import market_map, value_goods


@dataclass
class BuildingProfit:
    id: int | None
    building_type: str
    state_id: int | None
    level: int
    weekly_profit: float | None
    per_level_profit: float | None
    estimated: bool
    active_pms: list[str]


def _estimate_value_added(b: Building, defs: GameDefs, market) -> float | None:
    """Sum value-added across the building's active PMs, scaled by level."""
    if not b.active_pms:
        return None
    total = 0.0
    any_priced = False
    for apm in b.active_pms:
        flows = defs.pm_goods(apm.pm)
        gv = value_goods(flows["input"], flows["output"], market, defs.good_base_price)
        if gv.revenue or gv.input_cost:
            any_priced = True
        total += gv.value_added
    if not any_priced:
        return None
    return total * max(b.level, 1)


def analyse_profitability(snap: Snapshot, defs: GameDefs) -> list[BuildingProfit]:
    market = market_map(snap)
    out: list[BuildingProfit] = []
    for b in snap.buildings:
        profit = b.weekly_profit
        estimated = False
        if profit is None:
            profit = _estimate_value_added(b, defs, market)
            estimated = profit is not None
        per_level = (profit / b.level) if (profit is not None and b.level) else profit
        out.append(
            BuildingProfit(
                id=b.id,
                building_type=b.building_type,
                state_id=b.state_id,
                level=b.level,
                weekly_profit=profit,
                per_level_profit=per_level,
                estimated=estimated,
                active_pms=[p.pm for p in b.active_pms],
            )
        )
    # Worst performers first surfaces problems; callers can reverse for winners.
    out.sort(key=lambda x: (x.per_level_profit is None, x.per_level_profit or 0.0))
    return out
