# Victoria 3 save schema — extraction map

This is the map the extraction layer (`extract/snapshot.py`) targets: which
**player-visible** values we pull from a melted gamestate, and where they live.

> **Status: confirmed against a real melted save — Vic3 1.13.8** (SAR /
> Sardinia-Piedmont, 1836.1.1 autosave). The paths below are what the extractor
> actually reads; it still uses defensive fallbacks where a patch might rename a
> peripheral field.

## Conventions

* Paths use `a.b.c` for nested maps and `[]` for "list / id-keyed map of these".
* "Player country" = the country whose `tag` matches `game.player_tag`, or the
  human-controlled country recorded in the save when the tag is blank.
* **Visibility rule:** only the player country's own data + globally-visible
  market/price data. Never read `ai_strategy`, AI plans, or other countries'
  internal ledgers beyond what the in-game diplomacy/market UI exposes.

## Top-level gamestate nodes (confirmed, Vic3 1.13.8)

| Need | Node | Notes |
|------|------|-------|
| In-game date | `date` (also `meta_data.game_date`) | time-series key |
| Game version | `meta_data.version` | e.g. `"1.13.8"` |
| Player country | `player_manager.database[].country` | id of each played seat → resolve tag in `country_manager` |
| Countries | `country_manager.database[]` | id-keyed; `definition` = tag, `budget`, `market`, GraphData trends |
| Markets | `market_manager.database[]` | **only `{owner=<id>}`** — no per-market goods data persisted |
| Goods prices | `market_manager.world_market.price_trend.channels[]` | channel id = good's numeric id (its index in `defs.goods` load order); latest channel value = world price. Non-tradable goods (services, transportation, electricity, gold) have no channel |
| States | `state_manager.database[]` | `country` = owner; `region` = name; `infrastructure(_usage)`, `arable_land`, `pop_statistics` |
| State population | `<state>.pop_statistics.population_{lower,middle,upper}_strata` | sum = total; `population_salaried_workforce` = workforce |
| Buildings | `building_manager.database[]` | `building` = type, `levels`, `state`; **no owner id** — owned via `state` → `states[].country` |
| Building economics | `goods_sales` (income), `salary_rate`+`goods_cost` (expense), `cash_reserves`, `profit_after_reserves` | no per-building pop headcount (`staffing` = staffed levels, not pops) |
| Active PMs | `<building>.production_methods[]` | array of PM name strings |
| Technology | top-level `technology.database[]` | each entry `{country=<id>, acquired_technologies={...}}`; researchable set is derived, not stored |
| Country trends | `<country>.{gdp,literacy,avgsoltrend}` | GraphData blocks (`channels[].values`); latest value is current |
| Budget | `<country>.budget` | `money` (treasury), `credit`, `weekly_income`/`weekly_expenses` (category arrays, summed), `balance_trend.current` |
| Construction queue | `<country>.government_queue.construction_elements[]` | queued type/state/cost; `construction_speed` on elements gives current country construction points/week when a queue exists |
| Static state regions | `map_data/state_regions/*.txt` | `arable_land`, `arable_resources`, `capped_resources` define visible land/deposit limits for state placement |

## Fields the analysis needs (per area)

### Market (`analysis/market.py`)
* per good: current price, base price (from defs `goods.cost`), buy/sell orders
  or supply/demand → shortage (price > base) / surplus (price < base).

### Building profitability (`analysis/profitability.py`)
* per player building: `building_type`, `level`, active PMs, `cash_reserves`,
  weekly `income`/`expense` or balance, employment numbers.

### PM optimisation (`analysis/pm_optimizer.py`)
* active PM per slot + the building's PM groups (defs) → enumerate alternative
  PMs in each group, gate by researched techs (`unlocking_technologies`),
  value each PM's goods flow (defs `pm_goods`) at current market prices.

### What to build (`analysis/build_what.py`)
* candidate building types (defs) + their best available PM → projected margin
  at current prices, weighted by market shortage of outputs and availability of
  inputs.

### Where to build (`analysis/build_where.py`)
* per state: infrastructure (used vs available), market access, arable land /
  resource capacity (`map_data/state_regions.capped_resources`), local
  unemployment, building slots.

### Construction (`analysis/construction.py`)
* construction points/week from active queue element `construction_speed`, queue
  contents from `government_queue.construction_elements[]`, per-item cost → ROI
  ordering. If no queue exists, the save may not expose a points/week scalar and
  the strategy engine falls back to a user-overridable estimate.

### Tech (`analysis/tech.py`)
* researched set + available techs → which unlock high-margin PMs or throughput
  bonuses for buildings the player operates.

### Strategy & forecast (`analysis/econ_model.py`, `simulate.py`, `optimize.py`, `strategy.py`)
System-level optimization/forecasting. Static game-rule inputs it relies on, all
from `common/` (loaded by `ingest/defs.py`):

* **`goods.<g>.traded_quantity`** — reference market depth, the relative
  yardstick for how much added supply/demand moves a good's price.
* **`goods.<g>.category`** — to detect consumer goods (`staple`/`luxury`) for the
  standard-of-living proxy.
* **`building_types.<b>.required_construction`** — construction points per level.
  Usually a *named alias* (e.g. `construction_cost_very_high`) resolved through
  `common/script_values` (newly loaded into `GameDefs.script_values`).
* **`building_types.<b>.building_group`** — classifies resource/land-gated
  buildings (`bg_mining`, `bg_agriculture`, …) vs urban industry.
* **`map_data/state_regions.<state>.arable_land`** and
  **`capped_resources`** — hard state capacity for farms/plantations/ranches and
  extractive buildings. The optimizer enforces country-level remaining capacity;
  the report allocates levels back to feasible state slices.
* **PM `building_employment_<poptype>_add` modifiers** — per-level headcount,
  used for labour demand and the SoL proxy.
* **Construction-sector PM goods basket** — valued at current forecast prices to
  estimate the treasury cost per construction point. New construction-sector
  levels increase future points/week while raising demand for their input goods.

Dynamic inputs are all already-extracted, player-visible `Snapshot` fields
(buildings + active PMs, market prices, budget, tech, and the SQLite snapshot
**history** for price-elasticity calibration). The engine reads nothing else —
structurally it cannot see AI plans or other countries' ledgers.

**Estimation caveats (flagged in the report's assumptions block):** absolute
world supply/demand volumes and the exact in-game GDP/SoL formulas are not in
saves. GDP is tracked as a scale-invariant ratio of modeled value-added
(value-added × ~52 ≈ Vic3 GDP, confirmed within ~16% on a real save); market
depth is anchored on the player's own scale × an assumed/ calibrated market
share; construction capacity falls back to a GDP-based estimate when no active
queue exposes `construction_speed`.

## How to (re)confirm this map

1. Save a game (ideally set `save_file_format = "text"` in `pdx_settings.json`,
   or have `rakaly` installed).
2. `melt_save()` it and dump top-level keys:
   `python -c "from vic3analyser.ingest.melt import melt_save; ..."`.
3. Walk into `building_manager`, `market_manager`, etc., note the real key names
   and update this table + `extract/snapshot.py`.
4. Record the game version this was confirmed against here:

   **Confirmed against version:** 1.13.8 (SAR, 1836.1.1 autosave)

## Known gaps

* **State unemployment** and **per-building employment headcount**: not stored
  as scalars; would need to be derived from pops. Left `None`.
* **Market supply/demand**: not persisted at world-market level (only price).
* **Urban building slots**: no hard per-state slot limit is currently extracted,
  so urban industry placement remains a soft ranking by infrastructure and
  workforce rather than a hard cap.
