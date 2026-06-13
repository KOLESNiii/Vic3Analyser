"""Private construction: the investment pool builds in parallel, for free.

Government construction (the build queue) is paid from the treasury. But under
most economic systems capitalists also build — funded by the **investment
pool**, not the state. The save exposes the pool's weekly inflow
(``weekly_investment_pool_change_from_investment``); the economic-system law
scales how much of it goes to construction
(``country_private_construction_allocation_mult``). Converting that money to
construction points at the current basket price gives a *second* build stream
that grows GDP without draining the treasury.

This is also the lever behind the laissez-faire / interventionism scenarios: a
more pro-market law raises the allocation, so the same pool funds more private
building. Gated by ``cfg.model_investment_pool``; zero when the save lacks the
pool data and no fallback share is configured.
"""

from __future__ import annotations

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs

_ALLOC_MOD = "country_private_construction_allocation_mult"
_ECONOMIC_SYSTEM_GROUP = "lawgroup_economic_system"


def _allocation_mult(laws: list[str], defs: GameDefs) -> float:
    return 1.0 + sum(defs.law_modifiers(law).get(_ALLOC_MOD, 0.0) for law in laws)


def private_construction_money_week(snap: Snapshot, defs: GameDefs, cfg: OptimizeConfig) -> float:
    """Money/week the investment pool puts toward private construction.

    Anchored on the observed pool inflow; for a law scenario it's rescaled by the
    ratio of the assumed law's private-construction allocation to the actual
    one, so "what if laissez-faire?" shows the extra private building it unlocks.
    """
    if not cfg.model_investment_pool:
        return 0.0
    base = snap.country.investment_pool_weekly or 0.0
    if base <= 0.0:
        return 0.0
    if cfg.assumed_economic_law:
        actual = [
            l for l in (snap.country.active_laws or [])
            if defs.law_group(l) == _ECONOMIC_SYSTEM_GROUP
        ]
        cur = _allocation_mult(actual, defs)
        new = _allocation_mult([cfg.assumed_economic_law], defs)
        if cur > 0:
            base *= new / cur
    return max(0.0, base)


def private_construction_points_week(
    snap: Snapshot, defs: GameDefs, cfg: OptimizeConfig, cost_per_point: float
) -> float:
    """Construction points/week the pool funds, at the given basket price."""
    money = private_construction_money_week(snap, defs, cfg)
    if money <= 0.0 or cost_per_point <= 0.0:
        return 0.0
    return money / cost_per_point
