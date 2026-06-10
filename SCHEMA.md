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
| Construction queue | _not found_ | empty at turn 0; no stored points/queue scalar located — still unmapped |

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
  resource capacity (`*_resource` caps), local unemployment, building slots.

### Construction (`analysis/construction.py`)
* construction points/week, queue contents, per-item cost → ROI ordering.

### Tech (`analysis/tech.py`)
* researched set + available techs → which unlock high-margin PMs or throughput
  bonuses for buildings the player operates.

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

* **Construction** (`points/week`, queue): not located in the save. The turn-0
  autosave has an empty queue, so the structure couldn't be observed. Revisit
  with a save that has buildings under construction.
* **State unemployment** and **per-building employment headcount**: not stored
  as scalars; would need to be derived from pops. Left `None`.
* **Market supply/demand**: not persisted at world-market level (only price).
