"""Market analysis: which goods are in shortage (expensive) or glut (cheap).

A shortage (price above base) signals an opportunity to *produce* that good; a
glut (price below base) warns against building more of it. This is the same
read a player gets from the market screen, computed for every traded good and
ranked.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..extract.models import Snapshot
from .pricing import shortage_score


@dataclass
class GoodSignal:
    good: str
    price: float
    base_price: float | None
    price_ratio: float | None
    supply: float | None
    demand: float | None
    signal: float  # >0 shortage, <0 glut

    @property
    def status(self) -> str:
        if self.price_ratio is None:
            return "unknown"
        if self.price_ratio >= 1.10:
            return "shortage"
        if self.price_ratio <= 0.90:
            return "glut"
        return "balanced"


@dataclass
class MarketReport:
    goods: list[GoodSignal]

    @property
    def shortages(self) -> list[GoodSignal]:
        return [g for g in self.goods if g.status == "shortage"]

    @property
    def gluts(self) -> list[GoodSignal]:
        return [g for g in self.goods if g.status == "glut"]


def analyse_market(snap: Snapshot) -> MarketReport:
    signals: list[GoodSignal] = []
    for mg in snap.market:
        signals.append(
            GoodSignal(
                good=mg.good,
                price=mg.price,
                base_price=mg.base_price,
                price_ratio=mg.price_ratio,
                supply=mg.supply,
                demand=mg.demand,
                signal=shortage_score(mg),
            )
        )
    # Most acute shortages first, then gluts.
    signals.sort(key=lambda g: g.signal, reverse=True)
    return MarketReport(goods=signals)
