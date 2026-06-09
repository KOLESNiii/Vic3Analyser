"""Shared economic helpers for valuing goods flows at current market prices.

All figures are derived from player-visible data: the market prices in the
snapshot and the static goods/PM definitions. Quantities come from a PM's
``workforce_scaled`` goods modifiers, so values are expressed *per unit of
workforce-scaled throughput* — a sound basis for *relative* comparison between
PMs/buildings at the same scale, which is what the recommendations need.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..extract.models import MarketGood, Snapshot


@dataclass
class GoodsValue:
    revenue: float  # value of outputs
    input_cost: float  # value of inputs
    missing_prices: list[str]  # goods with no known market price

    @property
    def value_added(self) -> float:
        return self.revenue - self.input_cost


def price_of(good: str, market: dict[str, MarketGood], defs_base: float | None) -> float | None:
    """Current market price for a good, falling back to its base price."""
    mg = market.get(good)
    if mg is not None:
        return mg.price
    return defs_base


def value_goods(
    inputs: dict[str, float],
    outputs: dict[str, float],
    market: dict[str, MarketGood],
    base_price,
) -> GoodsValue:
    """Value a set of input/output goods flows at current market prices.

    ``base_price`` is a callable ``good -> float | None`` (e.g.
    ``GameDefs.good_base_price``) used when a good isn't traded in the snapshot.
    """
    revenue = 0.0
    cost = 0.0
    missing: list[str] = []
    for good, qty in outputs.items():
        p = price_of(good, market, base_price(good))
        if p is None:
            missing.append(good)
            continue
        revenue += p * qty
    for good, qty in inputs.items():
        p = price_of(good, market, base_price(good))
        if p is None:
            missing.append(good)
            continue
        cost += p * qty
    return GoodsValue(revenue=revenue, input_cost=cost, missing_prices=missing)


def shortage_score(mg: MarketGood) -> float:
    """A signed signal: >0 means scarce/expensive (worth producing), <0 glut.

    Uses price relative to base price; 0 when base price is unknown.
    """
    ratio = mg.price_ratio
    if ratio is None:
        return 0.0
    return ratio - 1.0


def market_map(snap: Snapshot) -> dict[str, MarketGood]:
    return snap.market_index()
