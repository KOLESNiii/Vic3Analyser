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


# Non-goods outputs the optimiser must not let a goods-only score trade away.
# These are *capacities* — the entire point of the buildings that make them — and
# have no market price, so a PM that trims a goods input while slashing one of
# them looks like a pure win to the goods scorer but wrecks the run (e.g.
# government_administration dropping bureaucracy / tax capacity to save paper,
# which collapses administration and the tax revenue that rides on it). Matched
# as substrings so mod-renamed variants (``*_tax_capacity_*``) are still caught.
GUARDED_CAPACITY_TOKENS = ("bureaucracy", "tax_capacity", "influence", "infrastructure")


def guarded_capacity(pm: str, defs) -> dict[str, float]:
    """The PM's capacity outputs that should never be sacrificed for goods value."""
    return {
        k: v
        for k, v in defs.pm_capacity_outputs(pm).items()
        if any(tok in k for tok in GUARDED_CAPACITY_TOKENS)
    }


def reduces_capacity(candidate_pm: str, baseline_pm: str | None, defs) -> bool:
    """True if switching to ``candidate_pm`` would drop a guarded capacity below
    what ``baseline_pm`` provides (so the switch is unsafe to recommend)."""
    if baseline_pm is None:
        return False
    base = guarded_capacity(baseline_pm, defs)
    if not base:
        return False
    cand = guarded_capacity(candidate_pm, defs)
    return any(cand.get(k, 0.0) < v for k, v in base.items())


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
