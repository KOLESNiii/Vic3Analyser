"""The cascading-effects core: a price-feedback model of the player's market.

Every other analysis in this package values a change at the *current, frozen*
market price. That is locally correct but globally wrong: building eight steel
mills floods steel (its price falls, so the eighth mill earns far less than the
first) and drains iron and coal (their prices rise, so *those* become the next
best thing to build). This module models that feedback.

It works entirely from player-visible data:

* **Player footprint** — the net supply (output − input) the player's own
  buildings contribute to each good, summed from their active production methods
  and levels. The player can see all of this on their own building screens.
* **Observed prices** — the world-market prices already in the snapshot. Vic3's
  price is a clamped function of the market's supply/demand imbalance (the price
  multiplier lives in ``[0.25, 1.75]`` of base), so the *current* price tells us
  the *current* imbalance. We invert that.
* **Market depth** — how much added supply it takes to move a good's price. We
  anchor depth on the player's own observed scale in each good (sized by a
  configurable ``world_market_share``), with the goods' static
  ``traded_quantity`` as the relative yardstick for goods the player isn't in
  yet. When enough snapshot history exists, the share is *calibrated* from how
  the player's own prices actually moved as their own production changed.

Given that, :class:`PriceModel` answers the key counterfactual: *if the player's
net footprint of every good became X, what would prices settle at?* —
``model.prices(footprint)``. :func:`solve_equilibrium` then closes the loop:
changed prices change which PM is best in each slot, which changes the footprint,
which changes prices, iterated to a fixed point (so second-order chains — cheaper
steel → cheaper tools → cheaper construction — settle out).

Everything here is an *estimate* and is flagged as such upstream; absolute world
supply/demand volumes are not in the save, so depth is modeled, not measured.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import median

from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .pricing import guarded_capacity

# Vic3 clamps a good's price to ±75% of its base price.
MAX_DEVIATION = 0.75
# Tradeable goods deviate less than this ceiling, because the world market
# absorbs some of the player's supply/demand swing (imports cap price rises,
# exports cap falls). Non-tradeable goods get the full clamp.
_TRADEABLE_DEVIATION = 0.55
# Tradeable goods also have deeper effective markets (world depth on top of the
# player's own), so a given footprint change moves their price less.
_TRADEABLE_DEPTH_MULT = 1.5
# Depth (in goods units) assumed for a good with no observable scale at all.
_FALLBACK_DEPTH = 1000.0


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


# --- goods valuation at an arbitrary price vector ---------------------------

def price_of(good: str, prices: dict[str, float], defs: GameDefs) -> float:
    """Price of a good under a price vector, falling back to its base price."""
    p = prices.get(good)
    if p is not None:
        return p
    base = defs.good_base_price(good)
    return base if base is not None else 0.0


def value_flows(
    inputs: dict[str, float],
    outputs: dict[str, float],
    prices: dict[str, float],
    defs: GameDefs,
) -> float:
    """Value-added (revenue − input cost) of a goods flow at given prices."""
    rev = sum(price_of(g, prices, defs) * q for g, q in outputs.items())
    cost = sum(price_of(g, prices, defs) * q for g, q in inputs.items())
    return rev - cost


def _pm_factors(pm: str, defs: GameDefs, bonus: float) -> tuple[float, float]:
    """Output- and input-side scale factors for a PM under an external
    throughput ``bonus`` (economy of scale + tech/law), stacking the PM's own
    ``building_throughput_add`` / one-sided goods mults additively (Vic3 order)."""
    m = defs.pm_building_mults(pm)
    thr = bonus + m["throughput"]
    out_factor = max(0.0, 1.0 + thr + m["output_mult"])
    in_factor = max(0.0, 1.0 + thr + m["input_mult"])
    return out_factor, in_factor


def pm_value_at(pm: str, prices: dict[str, float], defs: GameDefs, bonus: float = 0.0) -> float:
    """Per-level value-added of a PM, scaled by a throughput ``bonus`` fraction.

    ``bonus`` is the external throughput (economy of scale + researched-tech +
    active-law) for the building running this PM; 0 reproduces the raw goods
    value. Throughput scales both sides, so value-added scales with it.
    """
    flows = defs.pm_goods(pm)
    out_factor, in_factor = _pm_factors(pm, defs, bonus)
    rev = sum(price_of(g, prices, defs) * q for g, q in flows["output"].items()) * out_factor
    cost = sum(price_of(g, prices, defs) * q for g, q in flows["input"].items()) * in_factor
    return rev - cost


def _capacity_dominated(pm: str, others: list[str], defs: GameDefs) -> bool:
    """True if another unlocked PM matches/beats ``pm`` on every guarded capacity
    and strictly beats it on one. Such a PM is never the right pick for a
    capacity building (e.g. an admin slot): choosing it only to save a goods
    input throws away bureaucracy / tax capacity the goods score can't see."""
    cap = guarded_capacity(pm, defs)
    if not cap:
        return False  # goods-only PMs are never capacity-dominated
    for other in others:
        if other == pm:
            continue
        ocap = guarded_capacity(other, defs)
        if all(ocap.get(k, 0.0) >= v for k, v in cap.items()) and any(
            ocap.get(k, 0.0) > v for k, v in cap.items()
        ):
            return True
    return False


def best_pm_in_group(
    group: str, researched: set[str], prices: dict[str, float], defs: GameDefs
) -> str | None:
    """Highest value-added PM in a group that the player's tech unlocks.

    Capacity-dominated PMs are dropped first, so a capacity building keeps the
    best researched tier rather than collapsing to the cheapest-input PM (whose
    bureaucracy / tax capacity the goods value cannot account for)."""
    unlocked = [
        pm
        for pm in defs.group_pms(group)
        if not any(t not in researched for t in defs.pm_unlocking_techs(pm))
    ]
    candidates = [pm for pm in unlocked if not _capacity_dominated(pm, unlocked, defs)]
    best: str | None = None
    best_val = None
    for pm in candidates:
        val = pm_value_at(pm, prices, defs)
        if best_val is None or val > best_val:
            best, best_val = pm, val
    return best


# --- footprints -------------------------------------------------------------

def add_flows(into: dict[str, float], pm: str, levels: float, defs: GameDefs, bonus: float = 0.0) -> None:
    """Accumulate a PM's net supply (output − input) × levels into ``into``.

    ``bonus`` is the building's external throughput fraction; it scales the
    flows the same way it scales value, so price feedback sees the real volumes.
    """
    flows = defs.pm_goods(pm)
    out_factor, in_factor = _pm_factors(pm, defs, bonus)
    for g, q in flows["output"].items():
        into[g] = into.get(g, 0.0) + q * levels * out_factor
    for g, q in flows["input"].items():
        into[g] = into.get(g, 0.0) - q * levels * in_factor


def snapshot_footprint(
    snap: Snapshot, defs: GameDefs, throughput: dict[str, float] | None = None
) -> dict[str, float]:
    """Net supply per good from the player's buildings' *currently active* PMs."""
    fp: dict[str, float] = {}
    for b in snap.buildings:
        levels = max(b.level, 0)
        if not levels:
            continue
        bonus = throughput.get(b.building_type, 0.0) if throughput else 0.0
        for apm in b.active_pms:
            add_flows(fp, apm.pm, levels, defs, bonus)
    return fp


def holdings_footprint(
    holdings: dict[str, float],
    researched: set[str],
    prices: dict[str, float],
    defs: GameDefs,
    throughput: dict[str, float] | None = None,
) -> tuple[dict[str, float], dict[str, list[str]]]:
    """Footprint of a building multiset, each running its best available PM.

    ``holdings`` maps building_type → total levels. Returns the net footprint
    and the PM chosen per building type (for reporting/cascade narration).
    """
    fp: dict[str, float] = {}
    chosen: dict[str, list[str]] = {}
    for btype, levels in holdings.items():
        if levels <= 0:
            continue
        bonus = throughput.get(btype, 0.0) if throughput else 0.0
        pms: list[str] = []
        for group in defs.building_pm_groups(btype):
            pm = best_pm_in_group(group, researched, prices, defs)
            if pm is None:
                continue
            pms.append(pm)
            add_flows(fp, pm, levels, defs, bonus)
        chosen[btype] = pms
    return fp, chosen


def player_gross(
    snap: Snapshot, defs: GameDefs, throughput: dict[str, float] | None = None
) -> dict[str, dict[str, float]]:
    """Gross production and consumption per good across the player's buildings.

    Used to size market depth on the player's own observed scale. Returns
    ``{good: {"prod": x, "cons": y}}``.
    """
    out: dict[str, dict[str, float]] = defaultdict(lambda: {"prod": 0.0, "cons": 0.0})
    for b in snap.buildings:
        levels = max(b.level, 0)
        if not levels:
            continue
        bonus = throughput.get(b.building_type, 0.0) if throughput else 0.0
        for apm in b.active_pms:
            flows = defs.pm_goods(apm.pm)
            out_factor, in_factor = _pm_factors(apm.pm, defs, bonus)
            for g, q in flows["output"].items():
                out[g]["prod"] += q * levels * out_factor
            for g, q in flows["input"].items():
                out[g]["cons"] += q * levels * in_factor
    return out


# --- the price model --------------------------------------------------------

@dataclass
class PriceModel:
    """Maps any player footprint to an equilibrium price vector.

    ``base_gap`` is the inferred net demand−supply (in goods units) implied by
    the *observed* price at calibration; ``base_footprint`` is the player's net
    supply at that same moment. A new footprint shifts the gap by the change in
    the player's own net supply, which moves the price along Vic3's clamped
    supply/demand curve.
    """

    base_price: dict[str, float]
    depth: dict[str, float]
    base_gap: dict[str, float]
    base_footprint: dict[str, float]
    share: float
    calibrated: bool = False
    max_dev: float = MAX_DEVIATION
    # Per-good price-deviation ceiling. Tradeable goods deviate less (world trade
    # absorbs the imbalance); non-tradeable (services/transportation/electricity/
    # gold) get the full clamp. Falls back to ``max_dev`` for unknown goods.
    max_dev_by_good: dict[str, float] = field(default_factory=dict)

    def _dev(self, good: str) -> float:
        return self.max_dev_by_good.get(good, self.max_dev)

    def price(
        self,
        good: str,
        footprint: dict[str, float],
        demand_shift: dict[str, float] | None = None,
    ) -> float:
        base = self.base_price.get(good)
        if base is None:
            return 0.0
        depth = self.depth.get(good) or _FALLBACK_DEPTH
        df = footprint.get(good, 0.0) - self.base_footprint.get(good, 0.0)
        # More own supply ⇒ smaller gap; extra domestic demand ⇒ larger gap.
        gap = self.base_gap.get(good, 0.0) - df
        if demand_shift:
            gap += demand_shift.get(good, 0.0)
        imb = clamp(gap / depth, -1.0, 1.0)
        return base * (1.0 + self._dev(good) * imb)

    def prices(
        self, footprint: dict[str, float], demand_shift: dict[str, float] | None = None
    ) -> dict[str, float]:
        return {g: self.price(g, footprint, demand_shift) for g in self.base_price}

    def imbalance(self, good: str, footprint: dict[str, float]) -> float:
        """Signed supply/demand imbalance under a footprint (>0 shortage)."""
        depth = self.depth.get(good) or _FALLBACK_DEPTH
        df = footprint.get(good, 0.0) - self.base_footprint.get(good, 0.0)
        gap = self.base_gap.get(good, 0.0) - df
        return clamp(gap / depth, -1.0, 1.0)


def _depth_map(
    gross: dict[str, dict[str, float]], defs: GameDefs, share: float
) -> dict[str, float]:
    """Market depth (goods units) per good.

    For goods the player produces/consumes, depth = own scale ÷ share (so the
    player's footprint is ``share`` of the market). For goods the player isn't
    in, scale by the good's ``traded_quantity`` using the player's own typical
    depth-per-traded-quantity ratio as the yardstick.
    """
    share = clamp(share, 0.01, 1.0)
    own: dict[str, float] = {}
    ratios: list[float] = []
    for g, gc in gross.items():
        involvement = max(gc["prod"], gc["cons"])
        if involvement <= 0:
            continue
        own[g] = involvement / share
        tq = defs.good_traded_quantity(g)
        if tq and tq > 0:
            ratios.append(own[g] / tq)
    depth_per_tq = median(ratios) if ratios else (_FALLBACK_DEPTH)

    depth: dict[str, float] = {}
    for g in defs.goods:
        if g in own:
            depth[g] = own[g]
        else:
            tq = defs.good_traded_quantity(g)
            depth[g] = (tq * depth_per_tq) if (tq and tq > 0) else _FALLBACK_DEPTH
        # Tradeable goods have extra world-market depth on top of the player's
        # own, so the same footprint change moves their price less.
        if defs.good_tradeable(g):
            depth[g] *= _TRADEABLE_DEPTH_MULT
    return depth


def build_price_model(
    snap: Snapshot,
    defs: GameDefs,
    share: float = 0.25,
    history: list[Snapshot] | None = None,
    throughput: dict[str, float] | None = None,
) -> PriceModel:
    """Construct a :class:`PriceModel` calibrated to a snapshot.

    When ``history`` holds enough snapshots, the effective ``share`` is
    calibrated from how the player's own prices moved as their own production
    changed; otherwise the supplied ``share`` is used. ``throughput`` (per-type
    bonus) makes the base footprint reflect the economy's real output volumes,
    keeping it consistent with the throughput-scaled counterfactual solves.
    """
    calibrated = False
    if history:
        est = calibrate_share(history, defs)
        if est is not None:
            share, calibrated = est, True

    gross = player_gross(snap, defs, throughput)
    depth = _depth_map(gross, defs, share)
    base_footprint = snapshot_footprint(snap, defs, throughput)

    base_price: dict[str, float] = {}
    base_gap: dict[str, float] = {}
    max_dev_by_good: dict[str, float] = {}
    market = snap.market_index()
    for g in defs.goods:
        base = defs.good_base_price(g)
        if base is None or base <= 0:
            continue
        base_price[g] = base
        dev = _TRADEABLE_DEVIATION if defs.good_tradeable(g) else MAX_DEVIATION
        max_dev_by_good[g] = dev
        mg = market.get(g)
        if mg is not None and mg.price_ratio is not None:
            # Invert the *observed* deviation through this good's own ceiling.
            imb = clamp((mg.price_ratio - 1.0) / dev, -1.0, 1.0)
        else:
            imb = 0.0
        base_gap[g] = imb * (depth.get(g) or _FALLBACK_DEPTH)

    return PriceModel(
        base_price=base_price,
        depth=depth,
        base_gap=base_gap,
        base_footprint=base_footprint,
        share=share,
        calibrated=calibrated,
        max_dev_by_good=max_dev_by_good,
    )


def demand_shift_for(
    growth_fraction: float,
    model: PriceModel,
    defs: GameDefs,
    elasticity: float,
    categories: frozenset[str] | None = None,
) -> dict[str, float]:
    """Extra demand (in goods units) on consumer goods as the economy grows.

    Richer, more populous countries buy more staples/luxuries, bidding their
    prices up — so producing them gets *more* valuable as the plan succeeds, a
    feedback the supply-only model otherwise misses. The shift is sized as
    ``elasticity × growth_fraction × depth`` so it's comparable to the supply
    gap the price model already works in.
    """
    if not growth_fraction or elasticity <= 0:
        return {}
    cats = categories or _CONSUMER_CATEGORIES
    out: dict[str, float] = {}
    for g in model.base_price:
        if defs.good_category(g) in cats:
            depth = model.depth.get(g) or _FALLBACK_DEPTH
            out[g] = elasticity * growth_fraction * depth
    return out


# Consumer-goods categories whose demand grows with the economy.
_CONSUMER_CATEGORIES = frozenset({"staple", "luxury"})


def solve_equilibrium(
    holdings: dict[str, float],
    researched: set[str],
    model: PriceModel,
    defs: GameDefs,
    iters: int = 16,
    damping: float = 0.5,
    tol: float = 1e-3,
    throughput: dict[str, float] | None = None,
    demand_shift: dict[str, float] | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, list[str]]]:
    """Fixed-point solve for prices given a building multiset.

    Re-picks the best PM per slot at the evolving prices each iteration, so the
    second-order cascades settle. ``throughput`` scales each type's flows;
    ``demand_shift`` adds endogenous domestic demand. Returns
    ``(prices, footprint, chosen_pms)``.
    """
    prices = model.prices(model.base_footprint, demand_shift)
    fp: dict[str, float] = {}
    chosen: dict[str, list[str]] = {}
    for _ in range(max(1, iters)):
        fp, chosen = holdings_footprint(holdings, researched, prices, defs, throughput)
        target = model.prices(fp, demand_shift)
        max_diff = 0.0
        blended: dict[str, float] = {}
        for g, base in model.base_price.items():
            new = (1 - damping) * prices.get(g, target[g]) + damping * target[g]
            blended[g] = new
            denom = base or 1.0
            max_diff = max(max_diff, abs(new - prices.get(g, new)) / denom)
        prices = blended
        if max_diff < tol:
            break
    return prices, fp, chosen


# --- calibration from history ----------------------------------------------

def calibrate_share(history: list[Snapshot], defs: GameDefs) -> float | None:
    """Estimate the effective market share from observed price responses.

    Between consecutive snapshots we know how the player's own net footprint of
    each good changed (Δf) and how its price changed (Δp). Vic3's curve gives
    ``Δimbalance = Δp/base ÷ 0.75`` and our model says ``Δimbalance = −Δf /
    depth`` with ``depth = own_scale / share``. Solving per good and taking the
    median yields a robust share estimate; returns ``None`` when history is too
    thin or too quiet to say anything.
    """
    usable = [s for s in history if s.buildings and s.market]
    if len(usable) < 2:
        return None

    shares: list[float] = []
    for prev, cur in zip(usable, usable[1:]):
        fp_prev = snapshot_footprint(prev, defs)
        fp_cur = snapshot_footprint(cur, defs)
        gross_cur = player_gross(cur, defs)
        m_prev = prev.market_index()
        m_cur = cur.market_index()
        for g, base in ((g, defs.good_base_price(g)) for g in defs.goods):
            if not base or base <= 0:
                continue
            mp, mc = m_prev.get(g), m_cur.get(g)
            if mp is None or mc is None:
                continue
            d_imb = ((mc.price / base) - (mp.price / base)) / MAX_DEVIATION
            df = fp_cur.get(g, 0.0) - fp_prev.get(g, 0.0)
            involvement = max(gross_cur[g]["prod"], gross_cur[g]["cons"]) if g in gross_cur else 0.0
            # Need a real own-supply change and a real price response, same sign
            # expectation (more supply ⇒ lower price ⇒ d_imb negative).
            if abs(df) < 1e-6 or abs(d_imb) < 1e-3 or involvement <= 0:
                continue
            # depth = own/share ; d_imb = -df/depth ⇒ share = -df / (d_imb*own)
            est = -df / (d_imb * involvement)
            if 0.01 <= est <= 1.0:
                shares.append(est)

    if not shares:
        return None
    return float(median(shares))
