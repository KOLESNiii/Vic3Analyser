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

    meta = _first(gamestate, "meta_data", default={}) or {}
    date = str(_first(gamestate, "date", "game_date", default=None)
               or _first(meta, "game_date", "date", default="unknown"))
    version = _first(gamestate, "version", "save_game_version") or _first(meta, "version")

    country = _extract_country(gamestate, player_id, tag)
    market = _extract_market(gamestate, defs)
    buildings = _extract_buildings(gamestate, player_id)
    states = _extract_states(gamestate, player_id, defs)
    tech = _extract_tech(gamestate, player_id)
    construction = _extract_construction(gamestate, player_id, buildings)

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


def _sum_array(value: Any) -> float | None:
    """Sum a Vic3 category array (e.g. ``weekly_income={ 0 2599 7576 ... }``)."""
    nums = [n for n in (_num(x) for x in as_list(value)) if n is not None]
    return sum(nums) if nums else None


def _trend_current(node: Any) -> float | None:
    """Read ``.current`` from a Vic3 ``*_trend={ current=N }`` block."""
    if isinstance(node, dict):
        return _num(node.get("current"))
    return None


def _graph_latest(node: Any) -> float | None:
    """Latest value of a Vic3 "GraphData" block.

    Shape: ``{ sample_rate, count, channels={ <n>={ date, index,
    values={ <v> ... } } } }``. The current reading is the last value of the
    highest-indexed channel. Used for gdp, literacy, avgsoltrend, prices.
    """
    if not isinstance(node, dict):
        return None
    channels = node.get("channels")
    if not isinstance(channels, dict) or not channels:
        return None
    last_key = max(channels, key=lambda k: int_or(k, -1) or -1)
    return _channel_latest(channels[last_key])


def _channel_latest(channel: Any) -> float | None:
    """Last value in a GraphData channel's ``values={ ... }`` block."""
    values = channel.get("values") if isinstance(channel, dict) else None
    nums = [n for n in (_num(x) for x in as_list(values)) if n is not None]
    return nums[-1] if nums else None


def _active_laws(gamestate: dict, player_id: int | None) -> list[str]:
    """Names of laws currently enacted for the player country.

    ``laws.database[]`` holds every law slot for every country; the player's
    enacted ones are those with ``country == player_id`` and ``active == yes``.
    """
    if player_id is None:
        return []
    ldb = _db(_first(gamestate, "laws", "law_manager", default={}))
    out: list[str] = []
    for entry in ldb.values():
        if not isinstance(entry, dict):
            continue
        if int_or(_first(entry, "country")) != player_id:
            continue
        if _first(entry, "active") in (True, "yes"):
            name = _first(entry, "law")
            if name is not None:
                out.append(str(name))
    return out


def _extract_country(gamestate: dict, player_id: int | None, tag: str) -> CountryEconomy:
    c = _country_record(gamestate, player_id)
    budget = _first(c, "budget", "finances", default={}) or {}
    income = _sum_array(_first(budget, "weekly_income"))
    expense = _sum_array(_first(budget, "weekly_expenses"))
    balance = _trend_current(budget.get("balance_trend"))
    if balance is None and income is not None and expense is not None:
        balance = income - expense
    stats = _first(c, "pop_statistics", default={}) or {}
    return CountryEconomy(
        tag=tag,
        gdp=_graph_latest(c.get("gdp")),
        treasury=_num(_first(budget, "money", "treasury", "gold")),
        weekly_balance=balance,
        weekly_income=income,
        weekly_expense=expense,
        credit_limit=_num(_first(budget, "credit", "credit_limit")),
        avg_sol=_graph_latest(c.get("avgsoltrend")),
        literacy=_graph_latest(c.get("literacy")),
        population=int_or(_graph_latest(stats.get("trend_population"))),
        workforce=int_or(_first(stats, "population_salaried_workforce")),
        unemployed_workforce=int_or(_first(stats, "population_unemployed_workforce")),
        investment_pool_weekly=_num(
            _first(budget, "weekly_investment_pool_change_from_investment")
        ),
        active_laws=_active_laws(gamestate, player_id),
    )


def _extract_market(gamestate: dict, defs: GameDefs) -> list[MarketGood]:
    """Current goods prices from the world market.

    Per-market goods data isn't persisted (each ``market_manager.database``
    entry is just ``{owner=...}``); the only stored price series is
    ``world_market.price_trend``, a GraphData block whose channels are keyed by
    the good's numeric id — i.e. its position in the game's good load order,
    which equals ``defs.goods`` iteration order. Non-tradable goods (services,
    transportation, electricity, gold) simply have no channel.

    Supply/demand are not stored at world-market level, so they stay ``None``.
    """
    mm = _first(gamestate, "market_manager", default={}) or {}
    world = mm.get("world_market") if isinstance(mm, dict) else None
    channels = {}
    if isinstance(world, dict):
        pt = world.get("price_trend")
        if isinstance(pt, dict) and isinstance(pt.get("channels"), dict):
            channels = pt["channels"]

    goods: list[MarketGood] = []
    for idx, good_name in enumerate(defs.goods):
        price = _channel_latest(channels.get(str(idx)))
        if price is None:
            continue
        goods.append(
            MarketGood(
                good=good_name,
                price=price,
                base_price=defs.good_base_price(good_name),
                category=defs.good_category(good_name),
            )
        )
    return goods


def _player_state_ids(gamestate: dict, player_id: int | None) -> set[int]:
    """State ids owned by ``player_id`` (``states.<id>.country``)."""
    if player_id is None:
        return set()
    sdb = _db(_first(gamestate, "state_manager", "states", default={}))
    out: set[int] = set()
    for sid, s in sdb.items():
        if isinstance(s, dict) and int_or(_first(s, "country", "owner")) == player_id:
            sid_int = int_or(sid)
            if sid_int is not None:
                out.add(sid_int)
    return out


def _extract_buildings(gamestate: dict, player_id: int | None) -> list[Building]:
    bdb = _db(_first(gamestate, "building_manager", "buildings", default={}))
    # Buildings carry no owner id; they belong to a state, which a country owns.
    player_states = _player_state_ids(gamestate, player_id)
    out: list[Building] = []
    for bid, b in bdb.items():
        if not isinstance(b, dict):
            continue
        state_id = int_or(_first(b, "state", "state_id"))
        if player_id is not None and player_states and state_id not in player_states:
            continue
        btype = _first(b, "building", "building_type", "type")
        if btype is None:
            continue
        pms = [
            ActivePM(pm=str(p))
            for p in as_list(_first(b, "production_methods", "pms", default=[]))
        ]
        # Operating economics: expense = wages + input goods; income = goods
        # sold (absent for non-selling cost centres, where it defaults to 0 so
        # the building's operating loss still shows).
        salary = _num(_first(b, "salary_rate"))
        goods_cost = _num(_first(b, "goods_cost"))
        expense = None
        if salary is not None or goods_cost is not None:
            expense = (salary or 0.0) + (goods_cost or 0.0)
        sales = _num(_first(b, "goods_sales"))
        income = sales if sales is not None else (0.0 if expense is not None else None)
        out.append(
            Building(
                id=int_or(bid),
                building_type=str(btype),
                state_id=state_id,
                level=int(_num(_first(b, "levels", "level", default=0)) or 0),
                active_pms=pms,
                cash_reserves=_num(_first(b, "cash_reserves")),
                weekly_income=income,
                weekly_expense=expense,
                # No per-building headcount is stored (``staffing`` is the number
                # of staffed levels, not pops), so employment stays None.
                employment=int_or(_first(b, "employment", "total_employees")),
            )
        )
    return out


def _extract_states(gamestate: dict, player_id: int | None, defs: GameDefs) -> list[StateInfo]:
    sdb = _db(_first(gamestate, "state_manager", "states", default={}))
    out: list[StateInfo] = []
    for sid, s in sdb.items():
        if not isinstance(s, dict):
            continue
        owner = _first(s, "country", "owner")
        if player_id is not None and owner is not None and int_or(owner) != player_id:
            continue
        stats = _first(s, "pop_statistics", default={}) or {}
        # Total population = sum of the three strata; workforce = salaried pops.
        pop = _sum_array(
            [
                _first(stats, "population_lower_strata"),
                _first(stats, "population_middle_strata"),
                _first(stats, "population_upper_strata"),
            ]
        )
        region = _first(s, "region", "name")
        incorporation = _first(s, "incorporation")
        out.append(
            StateInfo(
                id=int_or(sid),
                name=region,
                population=int_or(pop),
                workforce=int_or(_first(stats, "population_salaried_workforce")),
                # Unemployed salaried pops — the state's idle labour the optimiser
                # can staff new buildings with before it must wait for pop growth.
                unemployment=int_or(
                    _first(stats, "population_unemployed_workforce")
                    or _first(s, "unemployment")
                ),
                infrastructure=_num(_first(s, "infrastructure")),
                infrastructure_used=_num(_first(s, "infrastructure_usage", "infrastructure_used")),
                # The save's ``arable_land`` is land already in use; the total
                # capacity comes from the static state-region definition.
                arable_land=int_or(_first(s, "arable_land")),
                arable_used=int_or(_first(s, "arable_land")),
                arable_total=defs.region_arable(region),
                arable_buildings=defs.region_arable_buildings(region),
                capped_resources=defs.region_capped_resources(region),
                bureaucracy_cost=_num(_first(s, "base_pop_bureaucracy_cost")),
                incorporated=(int_or(incorporation) not in (None, 0))
                if incorporation is not None
                else None,
            )
        )
    return out


def _extract_tech(gamestate: dict, player_id: int | None) -> TechState:
    # Researched techs live in the top-level ``technology`` manager, keyed by an
    # opaque record id; each entry maps a ``country`` id to its acquired list.
    tdb = _db(_first(gamestate, "technology", default={}))
    researched: list[str] = []
    for entry in tdb.values():
        if isinstance(entry, dict) and int_or(_first(entry, "country")) == player_id:
            researched = [str(t) for t in as_list(_first(entry, "acquired_technologies", default=[]))]
            break
    # "Available to research now" isn't stored — it's derived from the tech tree
    # at runtime — so it stays empty here.
    return TechState(researched=researched, available=[])


def _extract_construction(
    gamestate: dict, player_id: int | None, buildings: list[Building]
) -> ConstructionState:
    c = _country_record(gamestate, player_id)
    cnode = _first(c, "government_queue", "construction", default={}) or {}
    elements = as_list(
        _first(cnode, "construction_elements", "queue", "elements", default=[])
    )

    queue: list[ConstructionItem] = []
    # The country's construction throughput is the rate applied to the queue —
    # every element reports the same country-wide ``construction_speed``; the
    # max is the pool. (No standalone points/week scalar is stored.)
    speed = 0.0
    for item in as_list(elements):
        if not isinstance(item, dict):
            continue
        spd = _num(_first(item, "construction_speed", "base_construction_speed"))
        if spd is not None:
            speed = max(speed, spd)
        btype = _first(item, "type", "building_type", "building")
        if btype is None:
            continue
        queue.append(
            ConstructionItem(
                building_type=str(btype),
                state_id=int_or(_first(item, "state", "state_id")),
                levels=int(_num(_first(item, "levels", default=1)) or 1),
                remaining_cost=_num(
                    _first(item, "construction_left", "remaining_cost", "cost")
                ),
            )
        )

    points = speed if speed > 0 else _num(_first(cnode, "construction_points"))

    # Construction-sector levels (for modelling capacity expansion). One level
    # contributes roughly the whole current pool ÷ levels.
    sector_levels = sum(
        max(b.level, 0)
        for b in buildings
        if b.building_type == "building_construction_sector"
    )
    per_level = (
        (points / sector_levels) if (points and sector_levels) else None
    )

    return ConstructionState(
        points_per_week=points,
        queue=queue,
        sector_levels=sector_levels or None,
        points_per_sector_level=per_level,
    )


def int_or(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
