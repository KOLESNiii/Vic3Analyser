# Victoria 3 save schema — extraction map

This is the map the extraction layer (`extract/snapshot.py`) targets: which
**player-visible** values we pull from a melted gamestate, and where they live.

> **Status: needs confirmation against a real melted save.** The Vic3 gamestate
> is large and version-specific. The node paths below are the community-known
> structure (cross-referenced with tools like Garibaldi / pdx-tools) but exact
> key names drift between patches. Phase 2 finalises this against a real save;
> until then the extractor reads each field defensively with fallbacks.

## Conventions

* Paths use `a.b.c` for nested maps and `[]` for "list / id-keyed map of these".
* "Player country" = the country whose `tag` matches `game.player_tag`, or the
  human-controlled country recorded in the save when the tag is blank.
* **Visibility rule:** only the player country's own data + globally-visible
  market/price data. Never read `ai_strategy`, AI plans, or other countries'
  internal ledgers beyond what the in-game diplomacy/market UI exposes.

## Top-level gamestate nodes (to confirm)

| Need | Likely node | Confidence | Notes |
|------|-------------|-----------|-------|
| In-game date | `date` / `game_date` | med | for time-series key |
| Player country | `played_country` / `human` flag in `country_manager` | low | resolve to a country id |
| Countries | `country_manager.database[]` | high | id-keyed; each has tag, market, budget |
| Markets | `market_manager.database[]` | med | goods prices, supply/demand |
| Goods in market | `<market>.goods_data[]` or `mg:*` | low | price vs base price |
| States | `state_manager.database[]` | med | per-state infra, pops, buildings |
| Buildings | `building_manager.database[]` | high | type, level, PMs, cash, profit |
| Production methods active | `<building>.production_methods[]` | med | currently-selected PMs |
| Pops | `pop_manager.database[]` | med | employment, wages, SoL |
| Technology | `<country>.technology` / `technology_manager` | med | researched + researchable |
| Construction queue | `<country>.government_queue` / `construction` | low | points, queued buildings |

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

   **Confirmed against version:** _(none yet)_
