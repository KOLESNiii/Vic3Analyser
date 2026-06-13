"""Phase 3 — labour: supply pool, peasant mobilisation, understaffing penalty."""

from vic3analyser.config import OptimizeConfig
from vic3analyser.extract.models import CountryEconomy, Snapshot
from vic3analyser.analysis.labour import LabourPool, labour_pool, staffing_factor

CFG = OptimizeConfig()


def _snap(workforce, unemployed, population) -> Snapshot:
    return Snapshot(
        date="1836.1.1",
        player_tag="SAR",
        country=CountryEconomy(
            tag="SAR",
            workforce=workforce,
            unemployed_workforce=unemployed,
            population=population,
        ),
    )


def test_labour_pool_from_snapshot():
    pool = labour_pool(_snap(100_000, 5_000, 1_100_000))
    assert pool is not None
    assert pool.base_workforce == 100_000
    assert pool.slack_fraction == 0.05  # 5k unemployed / 100k
    assert pool.peasant_ratio == 10.0  # (1.1M - 100k)/100k

    # No workforce data -> no pool (labour modelling degrades to unconstrained).
    assert labour_pool(_snap(None, None, None)) is None


def test_available_ratio_grows_with_time_and_peasants():
    pool = LabourPool(base_workforce=100_000, slack_fraction=0.05, peasant_ratio=10.0)
    now = pool.available_ratio(0, CFG, sol=10.0)
    assert round(now, 3) == 1.05  # just the unemployed slack at t=0
    later = pool.available_ratio(60, CFG, sol=10.0)  # 5 years on
    assert later > now  # organic growth + mobilised peasants


def test_staffing_factor_throttles_when_demand_exceeds_supply():
    pool = LabourPool(base_workforce=100_000, slack_fraction=0.0, peasant_ratio=0.0)
    # At t=0 available ratio is 1.0; demanding 2x the workforce -> half-staffed.
    assert staffing_factor(pool, employment_ratio=2.0, month=0, cfg=CFG, sol=10.0) == 0.5
    # Demanding within the pool -> fully staffed.
    assert staffing_factor(pool, employment_ratio=0.8, month=0, cfg=CFG, sol=10.0) == 1.0
    # No pool / flag off -> never throttles.
    assert staffing_factor(None, 5.0, 0, CFG, 10.0) == 1.0
    off = OptimizeConfig(model_labour=False)
    assert staffing_factor(pool, 5.0, 0, off, 10.0) == 1.0


def test_peasant_mobilisation_relaxes_constraint_over_time():
    # A big peasant reserve lets a 2x build-out become feasible later even with
    # no organic growth.
    pool = LabourPool(base_workforce=100_000, slack_fraction=0.0, peasant_ratio=10.0)
    early = staffing_factor(pool, employment_ratio=2.0, month=0, cfg=CFG, sol=10.0)
    late = staffing_factor(pool, employment_ratio=2.0, month=120, cfg=CFG, sol=10.0)
    assert early == 0.5
    assert late == 1.0  # 10 yrs: mobilised peasants cover the 2x demand
