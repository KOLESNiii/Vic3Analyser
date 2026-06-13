"""Phase 4 — investment pool & laws: private construction stream, law
modifiers, and economic-system scenarios."""

from vic3analyser.config import OptimizeConfig
from vic3analyser.extract.models import CountryEconomy, Snapshot
from vic3analyser.ingest.defs import GameDefs
from vic3analyser.analysis.private_construction import (
    private_construction_money_week,
    private_construction_points_week,
)
from vic3analyser.analysis.production import effective_active_laws


def _law_defs() -> GameDefs:
    return GameDefs(
        laws={
            "law_interventionism": {
                "group": "lawgroup_economic_system",
                "modifier": {"country_private_construction_allocation_mult": 0.5},
            },
            "law_laissez_faire": {
                "group": "lawgroup_economic_system",
                "modifier": {"country_private_construction_allocation_mult": 0.75},
            },
            "law_traditionalism": {
                "group": "lawgroup_economic_system",
                "modifier": {"country_private_construction_allocation_mult": -0.5},
            },
        }
    )


def _snap(pool=10_000.0, laws=("law_interventionism",)) -> Snapshot:
    return Snapshot(
        date="1836.1.1",
        player_tag="SAR",
        country=CountryEconomy(tag="SAR", investment_pool_weekly=pool, active_laws=list(laws)),
    )


def test_private_construction_money_from_pool():
    d = _law_defs()
    cfg = OptimizeConfig()
    assert private_construction_money_week(_snap(), d, cfg) == 10_000.0
    # No pool data -> nothing.
    assert private_construction_money_week(_snap(pool=0.0), d, cfg) == 0.0
    # Feature off -> nothing.
    assert private_construction_money_week(_snap(), d, OptimizeConfig(model_investment_pool=False)) == 0.0


def test_law_scenario_rescales_pool_by_allocation():
    d = _law_defs()
    snap = _snap(pool=10_000.0, laws=("law_interventionism",))  # actual alloc 1.5
    # Laissez-faire (alloc 1.75) -> more private construction than interventionism.
    cfg_lf = OptimizeConfig(assumed_economic_law="law_laissez_faire")
    money_lf = private_construction_money_week(snap, d, cfg_lf)
    assert round(money_lf, 2) == round(10_000.0 * 1.75 / 1.5, 2)
    assert money_lf > 10_000.0
    # Traditionalism (alloc 0.5) -> far less.
    cfg_tr = OptimizeConfig(assumed_economic_law="law_traditionalism")
    assert private_construction_money_week(snap, d, cfg_tr) < 10_000.0


def test_private_points_scale_with_basket_price():
    d = _law_defs()
    cfg = OptimizeConfig()
    # 10k/wk at 50/point -> 200 points/week.
    assert private_construction_points_week(_snap(), d, cfg, cost_per_point=50.0) == 200.0
    assert private_construction_points_week(_snap(), d, cfg, cost_per_point=0.0) == 0.0


def test_effective_active_laws_swaps_economic_system():
    d = _law_defs()
    snap = _snap(laws=("law_interventionism", "law_monarchy"))
    cfg = OptimizeConfig(assumed_economic_law="law_laissez_faire")
    laws = effective_active_laws(snap, d, cfg)
    assert "law_laissez_faire" in laws
    assert "law_interventionism" not in laws  # economic-system law replaced
    assert "law_monarchy" in laws  # other laws untouched
