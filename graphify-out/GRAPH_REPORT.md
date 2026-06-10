# Graph Report - analyser  (2026-06-10)

## Corpus Check
- 49 files · ~30,975 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 775 nodes · 2267 edges · 38 communities (35 shown, 3 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 431 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `587b076f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 41|Community 41]]

## God Nodes (most connected - your core abstractions)
1. `Snapshot` - 51 edges
2. `GameDefs` - 48 edges
3. `PriceModel` - 44 edges
4. `MarketGood` - 34 edges
5. `CountryEconomy` - 31 edges
6. `ActivePM` - 30 edges
7. `Building` - 29 edges
8. `TechState` - 29 edges
9. `_greedy()` - 28 edges
10. `optimize_growth()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `test_economic_build_options_gating_and_cost()` --calls--> `economic_build_options()`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/analysis/actions.py
- `test_optimizer_respects_budget()` --calls--> `economic_build_options()`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/analysis/actions.py
- `test_economic_build_options_gating_and_cost()` --calls--> `tech_options()`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/analysis/actions.py
- `test_where_to_build_ranking()` --calls--> `analyse_where_to_build()`  [INFERRED]
  tests/test_analysis_extra.py → src/vic3analyser/analysis/build_where.py
- `test_capacity_budget_and_state_allocation_respect_caps()` --calls--> `compute_capacity_budget()`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/analysis/capacity.py

## Communities (38 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (76): BaseModel, Building, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState (+68 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (35): _produces_priced_good(), The action space the optimizer searches over.  An economic plan is built out of, Whether any PM of the building outputs a good with a known base price., True when the player's tech allows building it and running every slot., A researchable technology and what it unlocks for the economy., TechOption, analyse_where_to_build(), _free_arable() (+27 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (13): Run the advanced optimizer/forecaster on demand (it's not cheap, so         it's, Watchdog handler that fires on new/updated ``.v3`` saves.  Saves are large and w, SaveHandler, FileSystemEvent, FileSystemEventHandler, float, Any, float (+5 more)

### Community 3 - "Community 3"
Cohesion: 0.31
Nodes (6): analyse_market(), GoodSignal, MarketReport, Classify every traded good's price signal.      ``producible`` (goods the player, Snapshot, str

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (33): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _load_scalars(), _manifest() (+25 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (29): coerce_key(), coerce_scalar(), _MultiList, parse(), _Parser, A parser for the Clausewitz/Jomini text format used by Paradox files.  Handles t, A list produced by collapsing duplicate keys (vs an array literal)., Parse Clausewitz text into a nested dict. (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (31): _cfg(), _make_install(), Config, Path, End-to-end API test: synthetic install + crafted plaintext save through the full, Settings/saves endpoints: list saves and analyse the latest on demand., test_full_api_flow(), test_on_demand_analysis() (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (27): bytes, Config, _decode(), _looks_like_text(), _melt_cmd(), melt_save(), _melt_zip(), MeltError (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.24
Nodes (15): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.22
Nodes (27): $(), analyseSave(), drawGdp(), el(), fmt(), lineChart(), loadSaves(), loadSettings() (+19 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (17): Connection, int, Path, Snapshot, str, _date_key(), Recent snapshots oldest→newest (up to ``limit``) for calibration.          The o, Return denormalised headline metrics over time for charting.          ``metrics` (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (14): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Known gaps, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`) (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.27
Nodes (14): _as_int(), _country_database(), _find_country_by_tag(), _is_int(), _player_from_manager(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf, First played country id from ``player_manager.database.<n>.country``. (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.21
Nodes (19): PathLike, Path, str, _candidate_installs(), _candidate_save_dirs(), _first_existing(), _home(), load_config() (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (10): code:bash (uv sync), code:bash (g++ -std=c++17 melter.cpp -I. -L. -lrakaly -o melter   # add), How it works, Melting binary/ironman saves, On-demand analysis, Setup, Status, Strategy & Forecast — system-level optimization (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (12): Market analysis: which goods are in shortage (expensive) or glut (cheap).  A sho, GoodsValue, price_of(), Shared economic helpers for valuing goods flows at current market prices.  All f, Current market price for a good, falling back to its base price., Value a set of input/output goods flows at current market prices.      ``base_pr, A signed signal: >0 means scarce/expensive (worth producing), <0 glut.      Uses, shortage_score() (+4 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (114): BuildOption, economic_build_options(), Estimated game-weeks to research a tech, from its era (coarse)., All economic building types the plan could invest in (gating deferred).      "Ec, Not-yet-researched technologies that unlock economic PMs or buildings., Preferred state ids to place a building in, best capacity first.      Reuses the, A candidate building type the plan may invest construction into., state_assignment() (+106 more)

### Community 26 - "Community 26"
Cohesion: 0.26
Nodes (13): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), producible_goods(), What to build: rank building types by projected value-added at current prices, w, Goods the player can actually produce now.      A good is producible if some bui, market_map() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.57
Nodes (6): _defs(), Buildings/goods the player can't act on must not be recommended.  Regression tes, _snap(), test_locked_good_not_an_actionable_shortage(), test_producible_goods_excludes_locked(), test_unbuildable_building_excluded_from_build_what()

### Community 28 - "Community 28"
Cohesion: 0.16
Nodes (16): build_recommendations(), Synthesize all analyses into one prioritized, explained action list.  This is th, Recommendation, analyse_tech_priorities(), _pm_value(), Research priorities: which technologies unlock the most economic value.  For the, TechPriority, int (+8 more)

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (8): _defs(), _market(), _snap(), test_construction_payback_and_suggestions(), test_tech_priorities_uplift(), test_what_to_build_demand_weighting(), test_what_to_build_ranks_and_filters(), test_where_to_build_ranking()

### Community 30 - "Community 30"
Cohesion: 0.36
Nodes (6): analyse_construction(), ConstructionReport, QueueItemAnalysis, Construction focus: payback ranking of the queue and suggested additions.  Const, GameDefs, Snapshot

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (18): Any, SnapshotStore, Any, Config, GameDefs, Path, Snapshot, str (+10 more)

### Community 32 - "Community 32"
Cohesion: 0.27
Nodes (9): analyse_profitability(), BuildingProfit, _estimate_value_added(), Per-building profitability ranking for the player's buildings.  Prefers the real, Sum value-added across the building's active PMs, scaled by level., Building, float, GameDefs (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (31): add_flows(), best_pm_in_group(), build_price_model(), calibrate_share(), clamp(), _depth_map(), holdings_footprint(), player_gross() (+23 more)

### Community 34 - "Community 34"
Cohesion: 0.27
Nodes (19): _cfg(), _defs(), Tests for the system-level optimizer / forecaster.  Uses a small synthetic econo, The engine consumes only the player-visible Snapshot — no gamestate, so     it s, _snap(), test_build_strategy_report_shape_and_jsonable(), test_calibrate_share_from_history(), test_capacity_budget_and_state_allocation_respect_caps() (+11 more)

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (15): AppState, is_autosave(), All ``.v3`` saves in ``save_dir``, newest first.          Autosaves and manual s, Begin watching ``save_dir`` for new saves. Returns whether it ran., Toggle continuous watching at runtime. Returns the effective state.          Ena, Set which saves the watcher reacts to ("any"/"autosave").          Restarts the, Ingest the newest save in ``save_dir`` on demand. Returns its date.          Wit, On startup, ingest the newest save already in the folder.          Honours ``wat (+7 more)

### Community 36 - "Community 36"
Cohesion: 0.32
Nodes (6): create_app(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, FastAPI, Config, SQLite time-series store for extracted snapshots.  Each snapshot is stored whole

### Community 41 - "Community 41"
Cohesion: 0.53
Nodes (8): _defs(), _snap(), test_market_shortage_detection(), test_pm_switch_not_recommended_when_current_is_best(), test_pm_switch_not_recommended_when_tech_locked(), test_pm_switch_recommended_when_tech_available(), test_profitability_estimates_when_figures_absent(), test_profitability_uses_real_figures_when_present()

## Knowledge Gaps
- **58 isolated node(s):** `Strategy & Forecast — system-level optimization`, `Watch mode`, `On-demand analysis`, `code:bash (uv sync)`, `code:bash (g++ -std=c++17 melter.cpp -I. -L. -lrakaly -o melter   # add)` (+53 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GameDefs` connect `Community 4` to `Community 32`, `Community 1`, `Community 33`, `Community 0`, `Community 36`, `Community 6`, `Community 8`, `Community 16`, `Community 26`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `Snapshot` connect `Community 0` to `Community 32`, `Community 1`, `Community 33`, `Community 36`, `Community 8`, `Community 15`, `Community 16`, `Community 26`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `SnapshotStore` connect `Community 10` to `Community 0`, `Community 35`, `Community 36`, `Community 28`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `Snapshot` (e.g. with `Building` and `ConstructionState`) actually correct?**
  _`Snapshot` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `GameDefs` (e.g. with `GameDefs` and `Snapshot`) actually correct?**
  _`GameDefs` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `PriceModel` (e.g. with `OptimizeResult` and `StepTrace`) actually correct?**
  _`PriceModel` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `MarketGood` (e.g. with `Building` and `ConstructionState`) actually correct?**
  _`MarketGood` has 27 INFERRED edges - model-reasoned connections that need verification._