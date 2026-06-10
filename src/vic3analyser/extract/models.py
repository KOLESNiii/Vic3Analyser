"""Typed, player-visible economic state — the stable interface all analysis
consumes.

These models are deliberately decoupled from the raw save's key names. The
brittle, version-specific mapping from a parsed gamestate dict into these
models lives in one place (`extract/snapshot.py`); everything downstream
(analysis, API, dashboard) depends only on this shape.

Every field here corresponds to something the player can see in-game. No AI
plans, no hidden state.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MarketGood(BaseModel):
    good: str
    price: float
    base_price: float | None = None
    category: str | None = None  # defs category (e.g. staple/luxury/industrial)
    supply: float | None = None
    demand: float | None = None

    @property
    def price_ratio(self) -> float | None:
        """Current price relative to base price (>1 = shortage, <1 = glut)."""
        if self.base_price in (None, 0):
            return None
        return self.price / self.base_price


class ActivePM(BaseModel):
    group: str | None = None
    pm: str


class Building(BaseModel):
    id: int | None = None
    building_type: str
    state_id: int | None = None
    level: int = 0
    active_pms: list[ActivePM] = Field(default_factory=list)
    cash_reserves: float | None = None
    # Weekly figures as shown in the building tooltip, if available.
    weekly_income: float | None = None
    weekly_expense: float | None = None
    employment: int | None = None

    @property
    def weekly_profit(self) -> float | None:
        if self.weekly_income is None or self.weekly_expense is None:
            return None
        return self.weekly_income - self.weekly_expense


class StateInfo(BaseModel):
    id: int | None = None
    name: str | None = None
    population: int | None = None
    workforce: int | None = None
    unemployment: int | None = None
    infrastructure: float | None = None
    infrastructure_used: float | None = None
    arable_land: int | None = None
    arable_used: int | None = None
    # capped resources (coal, iron, oil, ...) discovered/exploitable
    resources: dict[str, int] = Field(default_factory=dict)
    resources_used: dict[str, int] = Field(default_factory=dict)
    # Static land/resource capacity from the state-region definition (the player
    # sees this on the state's resource panel):
    #   arable_total      — total arable land levels the state can host
    #   arable_buildings  — building types that draw on that shared arable pool
    #   capped_resources  — per-building-type maximum levels (mines, logging, …)
    arable_total: float | None = None
    arable_buildings: list[str] = Field(default_factory=list)
    capped_resources: dict[str, float] = Field(default_factory=dict)

    @property
    def infrastructure_free(self) -> float | None:
        if self.infrastructure is None or self.infrastructure_used is None:
            return None
        return self.infrastructure - self.infrastructure_used


class TechState(BaseModel):
    researched: list[str] = Field(default_factory=list)
    # Techs whose prerequisites are met and can be researched now.
    available: list[str] = Field(default_factory=list)

    def has(self, tech: str) -> bool:
        return tech in self.researched


class ConstructionItem(BaseModel):
    building_type: str
    state_id: int | None = None
    levels: int = 1
    remaining_cost: float | None = None


class ConstructionState(BaseModel):
    points_per_week: float | None = None
    queue: list[ConstructionItem] = Field(default_factory=list)
    # Construction sector levels and the points each level contributes, so the
    # forecaster can model expanding construction (the key growth lever).
    sector_levels: int | None = None
    points_per_sector_level: float | None = None


class CountryEconomy(BaseModel):
    tag: str
    gdp: float | None = None
    treasury: float | None = None
    weekly_balance: float | None = None
    weekly_income: float | None = None
    weekly_expense: float | None = None
    credit_limit: float | None = None
    # Standard of living / literacy as headline indicators, if available.
    avg_sol: float | None = None
    literacy: float | None = None


class Snapshot(BaseModel):
    """One game-month's worth of player-visible economic state."""

    date: str
    player_tag: str
    game_version: str | None = None
    source: str | None = None  # how the save was read (plaintext/rakaly/...)

    country: CountryEconomy
    market: list[MarketGood] = Field(default_factory=list)
    buildings: list[Building] = Field(default_factory=list)
    states: list[StateInfo] = Field(default_factory=list)
    tech: TechState = Field(default_factory=TechState)
    construction: ConstructionState = Field(default_factory=ConstructionState)

    def market_index(self) -> dict[str, MarketGood]:
        return {g.good: g for g in self.market}

    def state_index(self) -> dict[int, StateInfo]:
        return {s.id: s for s in self.states if s.id is not None}
