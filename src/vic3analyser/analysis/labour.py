"""Labour supply: buildings need workers, and there are only so many.

The base model assumed infinite labour — so it would happily recommend hundreds
of farms a country could never staff. In reality a building only produces in
proportion to how staffed it is, and the staffing comes from a finite, slowly
growing pool:

* **Now:** the salaried ``workforce`` already employed plus the ``unemployed``
  slack (both extracted from the country's ``pop_statistics``).
* **Over time:** the pool grows with population/migration, faster when the
  standard of living is high (people have more children and immigrate to a
  thriving economy).

When the employment a plan demands outgrows that pool, the whole economy runs
understaffed and its output is scaled down — which both caps unrealistic
build-outs and rewards the standard-of-living growth that unlocks more labour.
Gated by ``cfg.model_labour``; degrades to "unconstrained" when pop data is
missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import OptimizeConfig
from ..extract.models import Snapshot
from .econ_model import clamp

# Months per year, for annualised growth.
_MONTHS_PER_YEAR = 12.0
# Standard-of-living reference and sensitivity: above this SoL the labour pool
# grows faster than the configured baseline, below it slower.
_SOL_REFERENCE = 10.0
_SOL_GROWTH_SENSITIVITY = 0.04
# Fraction of the non-workforce population (peasants/dependents) that can be
# pulled into employment as the player industrialises, and how long full
# mobilisation takes. This is the large early-game slack that lets an agrarian
# country grow fast before labour genuinely binds.
_MOBILISABLE_FRACTION = 0.20
_MOBILISE_YEARS = 10.0
# Cap on the peasant ratio so a tiny extracted workforce can't imply absurd slack.
_MAX_PEASANT_RATIO = 12.0


@dataclass
class LabourPool:
    """The player's labour supply, as a ratio basis for the staffing penalty."""

    base_workforce: float  # employed now (the unit basis: 1.0 = current economy)
    slack_fraction: float  # extra idle labour available immediately (unemployed)
    peasant_ratio: float  # non-workforce pops, mobilisable into jobs over time

    def available_ratio(self, month: int, cfg: OptimizeConfig, sol: float) -> float:
        """Available labour at ``month`` as a multiple of the base workforce."""
        years = month / _MONTHS_PER_YEAR
        sol_bonus = _SOL_GROWTH_SENSITIVITY * ((sol or 0.0) - _SOL_REFERENCE)
        growth = max(0.0, cfg.labour_growth_annual + sol_bonus)
        organic = (1.0 + self.slack_fraction) * (1.0 + growth * years)
        # Peasants urbanise gradually (ramped to full over _MOBILISE_YEARS).
        mobilised = (
            self.peasant_ratio
            * _MOBILISABLE_FRACTION
            * clamp(years / _MOBILISE_YEARS, 0.0, 1.0)
        )
        return organic + mobilised


def labour_pool(snap: Snapshot) -> LabourPool | None:
    """Build a :class:`LabourPool` from the snapshot, or ``None`` if the save
    doesn't expose the workforce numbers."""
    wf = snap.country.workforce
    if not wf or wf <= 0:
        return None
    unemployed = snap.country.unemployed_workforce or 0.0
    pop = snap.country.population or wf
    peasant_ratio = clamp(max(0.0, pop - wf) / wf, 0.0, _MAX_PEASANT_RATIO)
    return LabourPool(
        base_workforce=float(wf),
        slack_fraction=unemployed / wf,
        peasant_ratio=peasant_ratio,
    )


def staffing_factor(
    pool: LabourPool | None,
    employment_ratio: float,
    month: int,
    cfg: OptimizeConfig,
    sol: float,
) -> float:
    """Fraction of demanded labour that's actually staffed (``1.0`` = full).

    ``employment_ratio`` is the plan's total employment relative to the current
    economy's (so ``2.0`` means it wants twice today's workforce). When demand
    outruns the available pool, output scales by the shortfall.
    """
    if pool is None or not cfg.model_labour or employment_ratio <= 0:
        return 1.0
    available = pool.available_ratio(month, cfg, sol)
    return clamp(available / employment_ratio, 0.0, 1.0)
