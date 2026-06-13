# Graph Report - analyser  (2026-06-13)

## Corpus Check
- 59 files · ~41,615 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1005 nodes · 2957 edges · 45 communities (41 shown, 4 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 556 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `837e5c0d`
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
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 53|Community 53]]

## God Nodes (most connected - your core abstractions)
1. `GameDefs` - 71 edges
2. `Snapshot` - 66 edges
3. `PriceModel` - 49 edges
4. `_greedy()` - 47 edges
5. `CountryEconomy` - 42 edges
6. `MarketGood` - 41 edges
7. `ActivePM` - 41 edges
8. `simulate_plan()` - 39 edges
9. `Building` - 37 edges
10. `TechState` - 37 edges

## Surprising Connections (you probably didn't know these)
- `test_load_config_reads_solvency_defaults()` --calls--> `load_config()`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py
- `Config` --uses--> `Paths`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py
- `Path` --uses--> `Paths`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py

## Communities (45 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (85): BaseModel, Building, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState (+77 more)

### Community 1 - "Community 1"
Cohesion: 0.17
Nodes (13): analyse_construction(), ConstructionReport, QueueItemAnalysis, Construction focus: payback ranking of the queue and suggested additions.  Const, build_recommendations(), Synthesize all analyses into one prioritized, explained action list.  This is th, Recommendation, int (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (24): building_throughput_bonus(), economy_of_scale_bonus(), _modifier_throughput_for(), Throughput model: how much a building actually produces per level.  The base val, Throughput fraction a building gets from researched techs + active laws., Combined throughput *bonus fraction* for a building type (0 = none).      ``0.2`, Per-building-type throughput bonus fraction for a building multiset.      Thread, Throughput fraction from economy of scale at ``levels`` (0 if disabled).      Mo (+16 more)

### Community 3 - "Community 3"
Cohesion: 0.27
Nodes (7): analyse_market(), GoodSignal, MarketReport, Market analysis: which goods are in shortage (expensive) or glut (cheap).  A sho, Classify every traded good's price signal.      ``producible`` (goods the player, Snapshot, str

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (48): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _load_scalars(), _manifest() (+40 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (32): coerce_key(), coerce_scalar(), _MultiList, parse(), parse_file(), _Parser, A parser for the Clausewitz/Jomini text format used by Paradox files.  Handles t, A list produced by collapsing duplicate keys (vs an array literal). (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.16
Nodes (27): bytes, Config, _decode(), _looks_like_text(), _melt_cmd(), melt_save(), _melt_zip(), MeltError (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.26
Nodes (13): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), producible_goods(), What to build: rank building types by projected value-added at current prices, w, Goods the player can actually produce now.      A good is producible if some bui, market_map() (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (16): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.22
Nodes (27): $(), analyseSave(), drawGdp(), el(), fmt(), lineChart(), loadSaves(), loadSettings() (+19 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (19): Connection, int, Path, Snapshot, str, _date_key(), Recent snapshots oldest→newest (up to ``limit``) for calibration.          The o, Return denormalised headline metrics over time for charting.          ``metrics` (+11 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (14): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Known gaps, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`) (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.31
Nodes (8): analyse_tech_priorities(), _pm_value(), Research priorities: which technologies unlock the most economic value.  For the, TechPriority, float, GameDefs, Snapshot, str

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (129): BuildOption, Not-yet-researched technologies that unlock economic PMs or buildings., A candidate building type the plan may invest construction into., tech_options(), CapacityBudget, Free build capacity across the player's states, for the whole country., Free build capacity across the player's states, for the whole country., PriceModel (+121 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (10): code:bash (uv sync), code:bash (g++ -std=c++17 melter.cpp -I. -L. -lrakaly -o melter   # add), How it works, Melting binary/ironman saves, On-demand analysis, Setup, Status, Strategy & Forecast — system-level optimization (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.18
Nodes (17): GoodsValue, guarded_capacity(), price_of(), Shared economic helpers for valuing goods flows at current market prices.  All f, Current market price for a good, falling back to its base price., Value a set of input/output goods flows at current market prices.      ``base_pr, A signed signal: >0 means scarce/expensive (worth producing), <0 glut.      Uses, The PM's capacity outputs that should never be sacrificed for goods value. (+9 more)

### Community 26 - "Community 26"
Cohesion: 0.57
Nodes (6): _defs(), Buildings/goods the player can't act on must not be recommended.  Regression tes, _snap(), test_locked_good_not_an_actionable_shortage(), test_producible_goods_excludes_locked(), test_unbuildable_building_excluded_from_build_what()

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (37): allocate_build_levels(), best_construction_pm(), compute_capacity_budget(), _construction_add(), construction_cost_per_point(), construction_pm_upgrade(), construction_pms(), construction_points_per_level() (+29 more)

### Community 28 - "Community 28"
Cohesion: 0.21
Nodes (19): PathLike, Path, str, _candidate_installs(), _candidate_save_dirs(), _first_existing(), _home(), load_config() (+11 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (24): admin_capacity_per_level(), base_bureaucracy_demand(), gov_capacity(), GovCapacity, Government capacity: bureaucracy and tax capacity as modelled constraints.  A gr, Fraction of the *desired* tax on GDP growth the government can actually     coll, Economy-wide throughput penalty fraction from a bureaucracy deficit., ``(bureaucracy, tax_capacity)`` a government_administration level adds at     it (+16 more)

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (9): Watchdog handler that fires on new/updated ``.v3`` saves.  Saves are large and w, SaveHandler, FileSystemEvent, FileSystemEventHandler, float, bool, float, Path (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.23
Nodes (13): Any, Run the advanced optimizer/forecaster on demand (it's not cheap, so         it's, Any, float, int, Any, str, analyse_all() (+5 more)

### Community 32 - "Community 32"
Cohesion: 0.11
Nodes (22): The action space the optimizer searches over.  An economic plan is built out of, analyse_where_to_build(), _free_arable(), _norm(), Where to build: rank the player's states by capacity to host new economic buildi, StateCapacity, analyse_profitability(), BuildingProfit (+14 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (60): add_flows(), best_pm_in_group(), build_price_model(), calibrate_share(), _capacity_dominated(), clamp(), demand_shift_for(), _depth_map() (+52 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (43): economic_build_options(), _produces_priced_good(), Estimated game-weeks to research a tech, from its era (coarse)., Whether any PM of the building outputs a good with a known base price., All economic building types the plan could invest in (gating deferred).      "Ec, Preferred state ids to place a building in, best capacity first.      Reuses the, True when the player's tech allows building it and running every slot., A researchable technology and what it unlocks for the economy. (+35 more)

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (15): AppState, is_autosave(), All ``.v3`` saves in ``save_dir``, newest first.          Autosaves and manual s, Begin watching ``save_dir`` for new saves. Returns whether it ran., Toggle continuous watching at runtime. Returns the effective state.          Ena, Set which saves the watcher reacts to ("any"/"autosave").          Restarts the, Ingest the newest save in ``save_dir`` on demand. Returns its date.          Wit, On startup, ingest the newest save already in the folder.          Honours ``wat (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.50
Nodes (8): _defs(), _market(), _snap(), test_construction_payback_and_suggestions(), test_tech_priorities_uplift(), test_what_to_build_demand_weighting(), test_what_to_build_ranks_and_filters(), test_where_to_build_ranking()

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (23): _cfg(), _make_install(), Config, Path, test_defs_cache_roundtrip(), test_load_defs_and_helpers(), test_mod_overlay_overrides(), _cfg() (+15 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (18): _allocation_mult(), private_construction_money_week(), private_construction_points_week(), Private construction: the investment pool builds in parallel, for free.  Governm, Money/week the investment pool puts toward private construction.      Anchored o, Construction points/week the pool funds, at the given basket price., float, GameDefs (+10 more)

### Community 40 - "Community 40"
Cohesion: 0.29
Nodes (9): SnapshotStore, Config, GameDefs, Path, Snapshot, Config, The active game ``common/`` directory (base game)., process_save() (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.35
Nodes (11): _defs(), _gov_defs(), A government_administration whose PMs trade paper for bureaucracy/tax     capaci, _snap(), test_market_shortage_detection(), test_pm_switch_does_not_downgrade_capacity_building(), test_pm_switch_not_recommended_when_current_is_best(), test_pm_switch_not_recommended_when_tech_locked() (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (15): LabourPool, Labour supply: buildings need workers, and there are only so many.  The base mod, The player's labour supply, as a ratio basis for the staffing penalty., Available labour at ``month`` as a multiple of the base workforce., Fraction of demanded labour that's actually staffed (``1.0`` = full).      ``emp, staffing_factor(), float, int (+7 more)

### Community 44 - "Community 44"
Cohesion: 0.27
Nodes (14): _as_int(), _country_database(), _find_country_by_tag(), _is_int(), _player_from_manager(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf, First played country id from ``player_manager.database.<n>.country``. (+6 more)

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (9): _cfg(), _make_install(), Config, Path, End-to-end API test: synthetic install + crafted plaintext save through the full, Settings/saves endpoints: list saves and analyse the latest on demand., test_full_api_flow(), test_load_config_reads_solvency_defaults() (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.47
Nodes (5): create_app(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, FastAPI, Config

## Knowledge Gaps
- **64 isolated node(s):** `PathLike`, `bool`, `bool`, `int`, `Any` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GameDefs` connect `Community 4` to `Community 32`, `Community 1`, `Community 33`, `Community 2`, `Community 0`, `Community 38`, `Community 7`, `Community 8`, `Community 39`, `Community 12`, `Community 13`, `Community 47`, `Community 27`, `Community 29`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `Snapshot` connect `Community 0` to `Community 32`, `Community 1`, `Community 33`, `Community 3`, `Community 2`, `Community 7`, `Community 8`, `Community 39`, `Community 42`, `Community 10`, `Community 12`, `Community 13`, `Community 15`, `Community 27`, `Community 29`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `parse()` connect `Community 5` to `Community 32`, `Community 40`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `GameDefs` (e.g. with `StepTrace` and `GameDefs`) actually correct?**
  _`GameDefs` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `Snapshot` (e.g. with `Building` and `ConstructionState`) actually correct?**
  _`Snapshot` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `PriceModel` (e.g. with `OptimizeResult` and `StepTrace`) actually correct?**
  _`PriceModel` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `CountryEconomy` (e.g. with `Building` and `ConstructionState`) actually correct?**
  _`CountryEconomy` has 38 INFERRED edges - model-reasoned connections that need verification._