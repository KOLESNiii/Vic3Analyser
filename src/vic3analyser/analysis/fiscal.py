"""Government capacity: bureaucracy and tax capacity as modelled constraints.

A growing economy isn't free for the government. Two player-visible capacities
gate it, and the base model ignored both:

* **Bureaucracy.** ``building_government_administration`` produces it
  (``country_bureaucracy_add`` on its automation PM); incorporated states and a
  growing population consume it (``base_pop_bureaucracy_cost``). Run a deficit
  and the whole economy takes a throughput penalty — so expansion has to be
  *administered*, not just built. This generalises the earlier capacity guard:
  administration is now a thing the optimiser builds when it's the bottleneck,
  not just something it refuses to downgrade.

* **Tax capacity.** The same building's ``state_tax_capacity_add`` (scaled by the
  economic-system law's ``state_tax_capacity_mult``) caps how much tax the
  government can actually collect. Grow GDP past it and the marginal tax capture
  falls — which is exactly why trading away tax capacity wrecks solvency.

Everything is derived from the player's own buildings, states, active laws and
the static defs. Each effect is gated by ``cfg.model_bureaucracy``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from ..ingest.defs import GameDefs
from .econ_model import best_pm_in_group, clamp

ADMIN_BUILDING = "building_government_administration"

# How much of a bureaucracy deficit (as a fraction of demand) translates into a
# throughput penalty, and the worst-case cap on that penalty.
_BUREAUCRACY_PENALTY_GAIN = 0.5
_BUREAUCRACY_PENALTY_CAP = 0.30


@dataclass
class GovCapacity:
    bureaucracy_produced: float
    bureaucracy_demand: float
    tax_capacity: float

    @property
    def bureaucracy_balance(self) -> float:
        return self.bureaucracy_produced - self.bureaucracy_demand

    @property
    def bureaucracy_penalty(self) -> float:
        """Economy-wide throughput penalty fraction from a bureaucracy deficit."""
        if self.bureaucracy_demand <= 0 or self.bureaucracy_balance >= 0:
            return 0.0
        deficit_frac = -self.bureaucracy_balance / self.bureaucracy_demand
        return clamp(deficit_frac * _BUREAUCRACY_PENALTY_GAIN, 0.0, _BUREAUCRACY_PENALTY_CAP)


def admin_capacity_per_level(
    researched: set[str], prices: dict[str, float], defs: GameDefs
) -> tuple[float, float]:
    """``(bureaucracy, tax_capacity)`` a government_administration level adds at
    its best researched automation PM."""
    bur = tax = 0.0
    for group in defs.building_pm_groups(ADMIN_BUILDING):
        pm = best_pm_in_group(group, researched, prices, defs)
        if pm is None:
            continue
        caps = defs.pm_capacity_outputs(pm)
        bur += caps.get("country_bureaucracy_add", 0.0)
        tax += caps.get("state_tax_capacity_add", 0.0)
    return bur, tax


def tax_capacity_law_mult(active_laws: list[str], defs: GameDefs) -> float:
    """Law multiplier on tax capacity (``state_tax_capacity_mult``)."""
    mult = 1.0
    for law in active_laws:
        mult += defs.law_modifiers(law).get("state_tax_capacity_mult", 0.0)
    return max(0.0, mult)


def base_bureaucracy_demand(snap: Snapshot) -> float:
    """Bureaucracy the player's states currently consume (Σ pop cost)."""
    return sum(s.bureaucracy_cost or 0.0 for s in snap.states)


def gov_capacity(
    holdings: dict[str, float],
    snap: Snapshot,
    researched: set[str],
    prices: dict[str, float],
    defs: GameDefs,
    active_laws: list[str],
    base_total_levels: float,
) -> GovCapacity:
    """Government capacity for a building multiset.

    Bureaucracy demand scales with economic size (total building levels) as a
    proxy for the pops/institutions that consume it: building more without more
    administration eats the surplus and eventually penalises throughput.
    """
    per_bur, per_tax = admin_capacity_per_level(researched, prices, defs)
    admin_levels = holdings.get(ADMIN_BUILDING, 0.0)
    produced = admin_levels * per_bur
    tax_cap = admin_levels * per_tax * tax_capacity_law_mult(active_laws, defs)

    base_demand = base_bureaucracy_demand(snap)
    total_levels = sum(holdings.values()) or 1.0
    scale = (total_levels / base_total_levels) if base_total_levels > 0 else 1.0
    demand = base_demand * scale
    return GovCapacity(bureaucracy_produced=produced, bureaucracy_demand=demand, tax_capacity=tax_cap)


def tax_capture_factor(gov: GovCapacity, gdp: float, gdp0: float, base_tax_capacity: float) -> float:
    """Fraction of the *desired* tax on GDP growth the government can actually
    collect, throttled when tax demand outgrows tax capacity.

    Tax demand is taken to grow with GDP; capacity grows only as the player
    builds administration. ``1.0`` means fully collected, ``<1`` means the
    economy has outrun its tax capacity (the solvency trap).
    """
    if base_tax_capacity <= 0 or gdp0 <= 0:
        return 1.0
    demand_ratio = gdp / gdp0  # tax demand grows with the economy
    capacity_ratio = (gov.tax_capacity / base_tax_capacity) if base_tax_capacity else 1.0
    if demand_ratio <= 0:
        return 1.0
    return clamp(capacity_ratio / demand_ratio, 0.0, 1.0)
