"""Adapter: parsed gamestate dict -> typed :class:`Snapshot`.

This is the **one** module tightly coupled to the raw save's key names. Every
field is read through :func:`_first`, which tries several candidate keys, so a
patch that renames a field degrades to ``None`` instead of crashing. The
candidate lists encode the SCHEMA.md map.

> Marked locations tagged ``# CONFIRM`` need verification against a real melted
> save (Phase 1/2 schema-discovery). Until then, extraction is best-effort:
> whatever can be resolved is filled in; the rest stays ``None`` and the
> dashboard shows it as unavailable rather than wrong.
"""

from __future__ import annotations

from typing import Any

from ..config import Config
from ..ingest.defs import GameDefs
from ..ingest.parser import as_list
from .models import (
    ActivePM,
    Building,
    ConstructionItem,
    ConstructionState,
    CountryEconomy,
    MarketGood,
    Snapshot,
    StateInfo,
    TechState,
)
from .visibility import resolve_player


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _db(node: Any) -> dict:
    """Unwrap a ``{database: {...}}`` manager node, or pass a dict through."""
    if isinstance(node, dict):
        if isinstance(node.get("database"), dict):
            return node["database"]
        return node
    return {}


def build_snapshot(
    gamestate: dict,
    defs: GameDefs,
    cfg: Config,
    source: str | None = None,
) -> Snapshot:
    player_id, player_tag = resolve_player(gamestate, cfg.player_tag)
    tag = player_tag or cfg.player_tag or "UNKNOWN"

    date = str(_first(gamestate, "date", "game_date", default="unknown"))
    version = _first(gamestate, "version", "save_game_version")

    country = _extract_country(gamestate, player_id, tag)
    market = _extract_market(gamestate, defs)
    buildings = _extract_buildings(gamestate, player_id)
    states = _extract_states(gamestate, player_id)
    tech = _extract_tech(gamestate, player_id)
    construction = _extract_construction(gamestate, player_id)

    return Snapshot(
        date=date,
        player_tag=tag,
        game_version=str(version) if version is not None else None,
        source=source,
        country=country,
        market=market,
        buildings=buildings,
        states=states,
        tech=tech,
        construction=construction,
    )


def _country_record(gamestate: dict, player_id: int | None) -> dict:
    countries = _db(_first(gamestate, "country_manager", "countries", default={}))
    if player_id is None:
        return {}
    return countries.get(str(player_id)) or countries.get(player_id) or {}


def _extract_country(gamestate: dict, player_id: int | None, tag: str) -> CountryEconomy:
    c = _country_record(gamestate, player_id)
    budget = _first(c, "budget", "finances", default={}) or {}
    return CountryEconomy(
        tag=tag,
        gdp=_num(_first(c, "gdp")),  # CONFIRM
        treasury=_num(_first(budget, "money", "treasury", "gold")),  # CONFIRM
        weekly_balance=_num(_first(budget, "weekly_net", "balance")),  # CONFIRM
        weekly_income=_num(_first(budget, "weekly_income", "income")),  # CONFIRM
        weekly_expense=_num(_first(budget, "weekly_expenses", "expenses")),  # CONFIRM
        credit_limit=_num(_first(budget, "credit", "credit_limit")),  # CONFIRM
        avg_sol=_num(_first(c, "avgsoltrend", "average_sol")),  # CONFIRM
        literacy=_num(_first(c, "literacy")),  # CONFIRM
    )


def _extract_market(gamestate: dict, defs: GameDefs) -> list[MarketGood]:
    markets = _db(_first(gamestate, "market_manager", "markets", default={}))
    goods: list[MarketGood] = []
    seen: set[str] = set()
    for _mid, market in markets.items():
        if not isinstance(market, dict):
            continue
        goods_node = _db(_first(market, "goods_data", "goods", default={}))  # CONFIRM
        for _gid, g in goods_node.items():
            if not isinstance(g, dict):
                continue
            name = _first(g, "goods", "good", "type")  # CONFIRM
            price = _num(_first(g, "price", "current_price"))
            if name is None or price is None or name in seen:
                continue
            seen.add(name)
            goods.append(
                MarketGood(
                    good=str(name),
                    price=price,
                    base_price=defs.good_base_price(str(name)),
                    supply=_num(_first(g, "supply", "sell_orders")),
                    demand=_num(_first(g, "demand", "buy_orders")),
                )
            )
    return goods


def _extract_buildings(gamestate: dict, player_id: int | None) -> list[Building]:
    bdb = _db(_first(gamestate, "building_manager", "buildings", default={}))
    out: list[Building] = []
    for bid, b in bdb.items():
        if not isinstance(b, dict):
            continue
        owner = _first(b, "country", "owner")  # CONFIRM
        if player_id is not None and owner is not None and int_or(owner) != player_id:
            continue
        btype = _first(b, "building_type", "type", "building")
        if btype is None:
            continue
        pms = [
            ActivePM(pm=str(p))
            for p in as_list(_first(b, "production_methods", "pms", default=[]))
        ]
        out.append(
            Building(
                id=int_or(bid),
                building_type=str(btype),
                state_id=int_or(_first(b, "state", "state_id")),
                level=int(_num(_first(b, "level", default=0)) or 0),
                active_pms=pms,
                cash_reserves=_num(_first(b, "cash_reserves")),
                weekly_income=_num(_first(b, "income", "weekly_income")),
                weekly_expense=_num(_first(b, "expense", "weekly_expense")),
                employment=int_or(_first(b, "employment", "total_employees")),
            )
        )
    return out


def _extract_states(gamestate: dict, player_id: int | None) -> list[StateInfo]:
    sdb = _db(_first(gamestate, "state_manager", "states", default={}))
    out: list[StateInfo] = []
    for sid, s in sdb.items():
        if not isinstance(s, dict):
            continue
        owner = _first(s, "country", "owner")  # CONFIRM
        if player_id is not None and owner is not None and int_or(owner) != player_id:
            continue
        out.append(
            StateInfo(
                id=int_or(sid),
                name=_first(s, "name", "region"),
                population=int_or(_first(s, "population", "pop")),
                workforce=int_or(_first(s, "workforce")),
                unemployment=int_or(_first(s, "unemployment")),
                infrastructure=_num(_first(s, "infrastructure")),
                infrastructure_used=_num(_first(s, "infrastructure_usage", "infrastructure_used")),
                arable_land=int_or(_first(s, "arable_land")),
                arable_used=int_or(_first(s, "arable_used")),
            )
        )
    return out


def _extract_tech(gamestate: dict, player_id: int | None) -> TechState:
    c = _country_record(gamestate, player_id)
    tnode = _first(c, "technology", "tech", default={}) or {}
    researched = [str(t) for t in as_list(_first(tnode, "acquired_technologies", "researched", default=[]))]
    available = [str(t) for t in as_list(_first(tnode, "can_research", "available", default=[]))]
    return TechState(researched=researched, available=available)


def _extract_construction(gamestate: dict, player_id: int | None) -> ConstructionState:
    c = _country_record(gamestate, player_id)
    cnode = _first(c, "construction", "government_queue", default={}) or {}
    points = _num(_first(cnode, "construction_points", "points_per_week"))
    queue: list[ConstructionItem] = []
    for item in as_list(_first(cnode, "queue", "elements", default=[])):
        if not isinstance(item, dict):
            continue
        btype = _first(item, "building_type", "type", "building")
        if btype is None:
            continue
        queue.append(
            ConstructionItem(
                building_type=str(btype),
                state_id=int_or(_first(item, "state", "state_id")),
                levels=int(_num(_first(item, "levels", default=1)) or 1),
                remaining_cost=_num(_first(item, "remaining_cost", "cost")),
            )
        )
    return ConstructionState(points_per_week=points, queue=queue)


def int_or(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
