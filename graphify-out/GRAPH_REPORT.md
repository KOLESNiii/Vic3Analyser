# Graph Report - analyser  (2026-06-10)

## Corpus Check
- 48 files · ~28,198 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 770 nodes · 2136 edges · 35 communities (32 shown, 3 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 399 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0f38145e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
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
- [[_COMMUNITY_Community 41|Community 41]]

## God Nodes (most connected - your core abstractions)
1. `Snapshot` - 51 edges
2. `GameDefs` - 44 edges
3. `PriceModel` - 42 edges
4. `MarketGood` - 34 edges
5. `CountryEconomy` - 31 edges
6. `ActivePM` - 30 edges
7. `Building` - 29 edges
8. `TechState` - 29 edges
9. `build_strategy()` - 26 edges
10. `Config` - 25 edges

## Surprising Connections (you probably didn't know these)
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Config` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Path` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `float` --uses--> `OptimizeConfig`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/config.py
- `GameDefs` --uses--> `OptimizeConfig`  [INFERRED]
  tests/test_strategy.py → src/vic3analyser/config.py

## Communities (35 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (80): BaseModel, Building, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState (+72 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (29): economic_build_options(), _produces_priced_good(), The action space the optimizer searches over.  An economic plan is built out of, Estimated game-weeks to research a tech, from its era (coarse)., Whether any PM of the building outputs a good with a known base price., All economic building types the plan could invest in (gating deferred).      "Ec, Not-yet-researched technologies that unlock economic PMs or buildings., Preferred state ids to place a building in, best capacity first.      Reuses the (+21 more)

### Community 3 - "Community 3"
Cohesion: 0.27
Nodes (7): analyse_market(), GoodSignal, MarketReport, Market analysis: which goods are in shortage (expensive) or glut (cheap).  A sho, Classify every traded good's price signal.      ``producible`` (goods the player, Snapshot, str

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (39): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _load_scalars(), _manifest() (+31 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (25): coerce_key(), coerce_scalar(), parse(), _Parser, Parse Clausewitz text into a nested dict., Return significant tokens (whitespace and comments stripped)., Convert a bare/quoted token to a native Python scalar., _tokenize() (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (68): create_app(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, FastAPI, PathLike, SnapshotStore, Path, str (+60 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (27): bytes, Config, _decode(), _looks_like_text(), _melt_cmd(), melt_save(), _melt_zip(), MeltError (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.24
Nodes (15): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.24
Nodes (27): $(), analyseSave(), drawGdp(), el(), fmt(), lineChart(), loadSaves(), loadSettings() (+19 more)

### Community 10 - "Community 10"
Cohesion: 0.20
Nodes (10): Connection, int, Path, Snapshot, str, Return denormalised headline metrics over time for charting.          ``metrics`, Insert or replace a snapshot (idempotent on player_tag+date)., Recent snapshots oldest→newest (up to ``limit``) for calibration.          The o (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (14): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Known gaps, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`) (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.24
Nodes (15): bool, _as_int(), _country_database(), _find_country_by_tag(), _is_int(), _player_from_manager(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (10): code:bash (uv sync), code:bash (g++ -std=c++17 melter.cpp -I. -L. -lrakaly -o melter   # add), How it works, Melting binary/ironman saves, On-demand analysis, Setup, Status, Strategy & Forecast — system-level optimization (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.60
Nodes (5): _snap(), test_get_specific_date(), test_idempotent_replace(), test_save_and_retrieve(), test_series_and_tags()

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (105): BuildOption, A candidate building type the plan may invest construction into., PriceModel, Maps any player footprint to an equilibrium price vector.      ``base_gap`` is t, _batch_footprint(), _greedy(), _main_output(), _merge_program() (+97 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (24): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), producible_goods(), What to build: rank building types by projected value-added at current prices, w, Goods the player can actually produce now.      A good is producible if some bui, GoodsValue (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.57
Nodes (6): _defs(), Buildings/goods the player can't act on must not be recommended.  Regression tes, _snap(), test_locked_good_not_an_actionable_shortage(), test_producible_goods_excludes_locked(), test_unbuildable_building_excluded_from_build_what()

### Community 28 - "Community 28"
Cohesion: 0.25
Nodes (9): analyse_tech_priorities(), _pm_value(), Research priorities: which technologies unlock the most economic value.  For the, TechPriority, float, GameDefs, Snapshot, str (+1 more)

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (8): _defs(), _market(), _snap(), test_construction_payback_and_suggestions(), test_tech_priorities_uplift(), test_what_to_build_demand_weighting(), test_what_to_build_ranks_and_filters(), test_where_to_build_ranking()

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (13): analyse_construction(), ConstructionReport, QueueItemAnalysis, Construction focus: payback ranking of the queue and suggested additions.  Const, build_recommendations(), Synthesize all analyses into one prioritized, explained action list.  This is th, Recommendation, int (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.38
Nodes (9): Any, Any, str, analyse_all(), Recursively convert dataclasses/pydantic/containers to JSON-able data., Serialise a GoodSignal including its computed ``status`` (asdict drops     prope, Run every analysis and return one JSON-able payload., _ser() (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.27
Nodes (9): analyse_profitability(), BuildingProfit, _estimate_value_added(), Per-building profitability ranking for the player's buildings.  Prefers the real, Sum value-added across the building's active PMs, scaled by level., Building, float, GameDefs (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (31): add_flows(), best_pm_in_group(), build_price_model(), calibrate_share(), clamp(), _depth_map(), holdings_footprint(), player_gross() (+23 more)

### Community 34 - "Community 34"
Cohesion: 0.28
Nodes (18): _cfg(), _defs(), Tests for the system-level optimizer / forecaster.  Uses a small synthetic econo, The engine consumes only the player-visible Snapshot — no gamestate, so     it s, _snap(), test_build_strategy_report_shape_and_jsonable(), test_calibrate_share_from_history(), test_defs_accessors_resolve_script_values_and_employment() (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (38): AppState, is_autosave(), All ``.v3`` saves in ``save_dir``, newest first.          Autosaves and manual s, Begin watching ``save_dir`` for new saves. Returns whether it ran., Toggle continuous watching at runtime. Returns the effective state.          Ena, Begin watching ``save_dir`` for new saves. Returns whether it ran., Set which saves the watcher reacts to ("any"/"autosave").          Restarts the, Toggle continuous watching at runtime. Returns the effective state.          Ena (+30 more)

### Community 41 - "Community 41"
Cohesion: 0.53
Nodes (8): _defs(), _snap(), test_market_shortage_detection(), test_pm_switch_not_recommended_when_current_is_best(), test_pm_switch_not_recommended_when_tech_locked(), test_pm_switch_recommended_when_tech_available(), test_profitability_estimates_when_figures_absent(), test_profitability_uses_real_figures_when_present()

## Knowledge Gaps
- **62 isolated node(s):** `PathLike`, `bool`, `bool`, `int`, `Any` (+57 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GameDefs` connect `Community 4` to `Community 32`, `Community 1`, `Community 33`, `Community 0`, `Community 6`, `Community 8`, `Community 16`, `Community 26`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Why does `Snapshot` connect `Community 0` to `Community 32`, `Community 1`, `Community 33`, `Community 3`, `Community 8`, `Community 16`, `Community 26`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `AppState` connect `Community 35` to `Community 6`, `Community 31`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `Snapshot` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`Snapshot` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `GameDefs` (e.g. with `GameDefs` and `Snapshot`) actually correct?**
  _`GameDefs` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `PriceModel` (e.g. with `OptimizeResult` and `StepTrace`) actually correct?**
  _`PriceModel` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `MarketGood` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`MarketGood` has 27 INFERRED edges - model-reasoned connections that need verification._