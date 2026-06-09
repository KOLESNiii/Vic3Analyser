from vic3analyser.extract.models import CountryEconomy, MarketGood, Snapshot
from vic3analyser.store.db import SnapshotStore


def _snap(date: str, gdp: float) -> Snapshot:
    return Snapshot(
        date=date,
        player_tag="GBR",
        country=CountryEconomy(tag="GBR", gdp=gdp, treasury=1000.0, weekly_balance=5.0),
        market=[MarketGood(good="steel", price=80.0, base_price=70.0)],
    )


def test_save_and_retrieve(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap("1836.1.1", 100.0))
    store.save(_snap("1836.2.1", 110.0))

    assert store.dates("GBR") == ["1836.1.1", "1836.2.1"]
    latest = store.latest("GBR")
    assert latest is not None and latest.country.gdp == 110.0
    assert latest.market[0].good == "steel"


def test_idempotent_replace(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap("1836.1.1", 100.0))
    store.save(_snap("1836.1.1", 999.0))  # same key, new value
    assert store.dates("GBR") == ["1836.1.1"]
    assert store.latest("GBR").country.gdp == 999.0


def test_series_and_tags(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap("1836.1.1", 100.0))
    store.save(_snap("1836.2.1", 110.0))
    series = store.series("GBR", ["gdp", "treasury"])
    assert [r["gdp"] for r in series] == [100.0, 110.0]
    assert series[0]["treasury"] == 1000.0
    assert store.tags() == ["GBR"]


def test_get_specific_date(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(_snap("1836.5.1", 123.0))
    got = store.get("GBR", "1836.5.1")
    assert got is not None and got.country.gdp == 123.0
    assert store.get("GBR", "1999.1.1") is None
