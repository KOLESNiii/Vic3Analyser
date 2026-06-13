# Graph Report - analyser  (2026-06-13)

## Corpus Check
- 59 files · ~42,340 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1011 nodes · 2965 edges · 42 communities (38 shown, 4 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 560 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `49ed3ba8`
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
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 53|Community 53]]

## God Nodes (most connected - your core abstractions)
1. `GameDefs` - 71 edges
2. `Snapshot` - 66 edges
3. `PriceModel` - 50 edges
4. `_greedy()` - 47 edges
5. `CountryEconomy` - 42 edges
6. `MarketGood` - 41 edges
7. `ActivePM` - 41 edges
8. `simulate_plan()` - 39 edges
9. `Building` - 37 edges
10. `TechState` - 37 edges

## Surprising Connections (you probably didn't know these)
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `test_load_config_reads_solvency_defaults()` --calls--> `load_config()`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py
- `test_build_strategy_report_shape_and_jsonable()` --calls--> `_ser()`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/pipeline.py
- `test_build_snapshot_basic()` --calls--> `build_snapshot()`  [INFERRED]
  tests/test_snapshot.py → src/vic3analyser/extract/snapshot.py
- `test_market_prices_from_world_market_by_good_order()` --calls--> `build_snapshot()`  [INFERRED]
  tests/test_snapshot.py → src/vic3analyser/extract/snapshot.py

## Communities (42 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (93): BaseModel, Building, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState (+85 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (24): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), producible_goods(), What to build: rank building types by projected value-added at current prices, w, Goods the player can actually produce now.      A good is producible if some bui, analyse_construction() (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (25): building_throughput_bonus(), economy_of_scale_bonus(), effective_active_laws(), _modifier_throughput_for(), Throughput model: how much a building actually produces per level.  The base val, Throughput fraction a building gets from researched techs + active laws., Combined throughput *bonus fraction* for a building type (0 = none).      ``0.2`, Per-building-type throughput bonus fraction for a building multiset.      Thread (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.27
Nodes (7): analyse_market(), GoodSignal, MarketReport, Market analysis: which goods are in shortage (expensive) or glut (cheap).  A sho, Classify every traded good's price signal.      ``producible`` (goods the player, Snapshot, str

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (49): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _load_scalars(), _manifest() (+41 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (29): coerce_key(), coerce_scalar(), _MultiList, parse(), _Parser, A parser for the Clausewitz/Jomini text format used by Paradox files.  Handles t, A list produced by collapsing duplicate keys (vs an array literal)., Parse Clausewitz text into a nested dict. (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.17
Nodes (25): bytes, Config, _decode(), _looks_like_text(), _melt_cmd(), melt_save(), _melt_zip(), MeltError (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.50
Nodes (4): _depth_map(), Market depth (goods units) per good.      For goods the player produces/consumes, Maps any player footprint to an equilibrium price vector.      ``base_gap`` is t, Market depth (goods units) per good.      For goods the player produces/consumes

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (16): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.22
Nodes (28): $(), analyseSave(), drawGdp(), el(), fmt(), lineChart(), loadSaves(), loadSettings() (+20 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (17): Connection, int, Path, Snapshot, str, _date_key(), Recent snapshots oldest→newest (up to ``limit``) for calibration.          The o, Return denormalised headline metrics over time for charting.          ``metrics` (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (14): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Known gaps, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`) (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (10): market_map(), analyse_tech_priorities(), _pm_value(), Research priorities: which technologies unlock the most economic value.  For the, TechPriority, Snapshot, float, GameDefs (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (128): BuildOption, A candidate building type the plan may invest construction into., CapacityBudget, compute_capacity_budget(), Free build capacity across the player's states, for the whole country., Free build capacity across the player's states, for the whole country., Aggregate free land/resource capacity across the player's states., Aggregate free land/resource capacity across the player's states. (+120 more)

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
Cohesion: 0.11
Nodes (35): allocate_build_levels(), best_construction_pm(), _construction_add(), construction_cost_per_point(), construction_pm_upgrade(), construction_pms(), construction_points_per_level(), current_construction_pm() (+27 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (24): admin_capacity_per_level(), base_bureaucracy_demand(), gov_capacity(), GovCapacity, Government capacity: bureaucracy and tax capacity as modelled constraints.  A gr, Fraction of the *desired* tax on GDP growth the government can actually     coll, Economy-wide throughput penalty fraction from a bureaucracy deficit., ``(bureaucracy, tax_capacity)`` a government_administration level adds at     it (+16 more)

### Community 31 - "Community 31"
Cohesion: 0.38
Nodes (9): Any, Any, str, analyse_all(), Recursively convert dataclasses/pydantic/containers to JSON-able data., Serialise a GoodSignal including its computed ``status`` (asdict drops     prope, Run every analysis and return one JSON-able payload., _ser() (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (10): analyse_profitability(), BuildingProfit, _estimate_value_added(), Per-building profitability ranking for the player's buildings.  Prefers the real, Sum value-added across the building's active PMs, scaled by level., Building, float, GameDefs (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.22
Nodes (26): _cfg(), _defs(), _defs_with_construction(), Tests for the system-level optimizer / forecaster.  Uses a small synthetic econo, The engine consumes only the player-visible Snapshot — no gamestate, so     it s, _snap(), test_build_strategy_report_shape_and_jsonable(), test_calibrate_share_from_history() (+18 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (31): AppState, is_autosave(), All ``.v3`` saves in ``save_dir``, newest first.          Autosaves and manual s, Begin watching ``save_dir`` for new saves. Returns whether it ran., Toggle continuous watching at runtime. Returns the effective state.          Ena, Set which saves the watcher reacts to ("any"/"autosave").          Restarts the, Ingest the newest save in ``save_dir`` on demand. Returns its date.          Wit, On startup, ingest the newest save already in the folder.          Honours ``wat (+23 more)

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (17): build_price_model(), calibrate_share(), player_gross(), Net supply per good from the player's buildings' *currently active* PMs., Net supply per good from the player's buildings' *currently active* PMs., Gross production and consumption per good across the player's buildings.      Us, Net supply per good from the player's buildings' *currently active* PMs., Gross production and consumption per good across the player's buildings.      Us (+9 more)

### Community 38 - "Community 38"
Cohesion: 0.06
Nodes (66): create_app(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, FastAPI, PathLike, SnapshotStore, Path, str (+58 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (18): _allocation_mult(), private_construction_money_week(), private_construction_points_week(), Private construction: the investment pool builds in parallel, for free.  Governm, Money/week the investment pool puts toward private construction.      Anchored o, Construction points/week the pool funds, at the given basket price., float, GameDefs (+10 more)

### Community 41 - "Community 41"
Cohesion: 0.35
Nodes (11): _defs(), _gov_defs(), A government_administration whose PMs trade paper for bureaucracy/tax     capaci, _snap(), test_market_shortage_detection(), test_pm_switch_does_not_downgrade_capacity_building(), test_pm_switch_not_recommended_when_current_is_best(), test_pm_switch_not_recommended_when_tech_locked() (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.16
Nodes (19): clamp(), labour_pool(), LabourPool, Labour supply: buildings need workers, and there are only so many.  The base mod, The player's labour supply, as a ratio basis for the staffing penalty., Available labour at ``month`` as a multiple of the base workforce., Build a :class:`LabourPool` from the snapshot, or ``None`` if the save     doesn, Fraction of demanded labour that's actually staffed (``1.0`` = full).      ``emp (+11 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (13): price_of(), Signed supply/demand imbalance under a footprint (>0 shortage)., Signed supply/demand imbalance under a footprint (>0 shortage)., Signed supply/demand imbalance under a footprint (>0 shortage)., Price of a good under a price vector, falling back to its base price., Price of a good under a price vector, falling back to its base price., Price of a good under a price vector, falling back to its base price., Value-added (revenue − input cost) of a goods flow at given prices. (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.27
Nodes (14): _as_int(), _country_database(), _find_country_by_tag(), _is_int(), _player_from_manager(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf, First played country id from ``player_manager.database.<n>.country``. (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.08
Nodes (37): economic_build_options(), _produces_priced_good(), The action space the optimizer searches over.  An economic plan is built out of, Estimated game-weeks to research a tech, from its era (coarse)., Whether any PM of the building outputs a good with a known base price., All economic building types the plan could invest in (gating deferred).      "Ec, Not-yet-researched technologies that unlock economic PMs or buildings., Preferred state ids to place a building in, best capacity first.      Reuses the (+29 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (20): add_flows(), best_pm_in_group(), _capacity_dominated(), holdings_footprint(), _pm_factors(), The cascading-effects core: a price-feedback model of the player's market.  Ever, Accumulate a PM's net supply (output − input) × levels into ``into``., Highest value-added PM in a group that the player's tech unlocks.      Capacity- (+12 more)

## Knowledge Gaps
- **64 isolated node(s):** `PathLike`, `bool`, `bool`, `int`, `Any` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GameDefs` connect `Community 4` to `Community 32`, `Community 1`, `Community 2`, `Community 0`, `Community 38`, `Community 39`, `Community 8`, `Community 12`, `Community 13`, `Community 46`, `Community 48`, `Community 27`, `Community 29`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `Snapshot` connect `Community 0` to `Community 32`, `Community 1`, `Community 2`, `Community 3`, `Community 39`, `Community 8`, `Community 42`, `Community 12`, `Community 13`, `Community 46`, `Community 15`, `Community 48`, `Community 27`, `Community 29`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `parse()` connect `Community 5` to `Community 32`, `Community 4`, `Community 38`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `GameDefs` (e.g. with `StepTrace` and `GameDefs`) actually correct?**
  _`GameDefs` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `Snapshot` (e.g. with `Building` and `ConstructionState`) actually correct?**
  _`Snapshot` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `PriceModel` (e.g. with `OptimizeResult` and `StepTrace`) actually correct?**
  _`PriceModel` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `CountryEconomy` (e.g. with `Building` and `ConstructionState`) actually correct?**
  _`CountryEconomy` has 38 INFERRED edges - model-reasoned connections that need verification._