# Graph Report - analyser  (2026-06-10)

## Corpus Check
- 42 files · ~17,420 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 531 nodes · 1390 edges · 33 communities (30 shown, 3 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 273 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `007f1fe8`
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

## God Nodes (most connected - your core abstractions)
1. `Snapshot` - 41 edges
2. `MarketGood` - 30 edges
3. `GameDefs` - 29 edges
4. `CountryEconomy` - 27 edges
5. `Config` - 25 edges
6. `ActivePM` - 25 edges
7. `Building` - 25 edges
8. `TechState` - 25 edges
9. `build_snapshot()` - 22 edges
10. `StateInfo` - 21 edges

## Surprising Connections (you probably didn't know these)
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Config` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Path` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Config` --uses--> `Config`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Path` --uses--> `Config`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py

## Communities (33 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (72): BaseModel, Building, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState (+64 more)

### Community 1 - "Community 1"
Cohesion: 0.27
Nodes (9): analyse_where_to_build(), _free_arable(), _norm(), Where to build: rank the player's states by capacity to host new economic buildi, StateCapacity, float, int, Snapshot (+1 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (31): Any, AppState, create_app(), is_autosave(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, Begin watching ``save_dir`` for new saves. Returns whether it ran., Toggle continuous watching at runtime. Returns the effective state.          Ena (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.18
Nodes (13): analyse_market(), GoodSignal, MarketReport, Market analysis: which goods are in shortage (expensive) or glut (cheap).  A sho, Classify every traded good's price signal.      ``producible`` (goods the player, Snapshot, str, _defs() (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (21): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _manifest(), Load the static game-rule definitions from a Victoria 3 ``common/`` tree.  These (+13 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (32): coerce_key(), coerce_scalar(), _MultiList, parse(), parse_file(), _Parser, A parser for the Clausewitz/Jomini text format used by Paradox files.  Handles t, A list produced by collapsing duplicate keys (vs an array literal). (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (40): Path, SnapshotStore, Config, GameDefs, Path, Snapshot, _cfg(), _make_install() (+32 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (27): bytes, Config, _decode(), _looks_like_text(), _melt_cmd(), melt_save(), _melt_zip(), MeltError (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (23): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.26
Nodes (24): $(), analyseSave(), drawGdp(), el(), fmt(), loadSaves(), loadSettings(), postSettings() (+16 more)

### Community 10 - "Community 10"
Cohesion: 0.27
Nodes (7): Connection, Path, Snapshot, str, Insert or replace a snapshot (idempotent on player_tag+date)., Return denormalised headline metrics over time for charting.          ``metrics`, SnapshotStore

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (13): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Known gaps, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`) (+5 more)

### Community 12 - "Community 12"
Cohesion: 0.24
Nodes (15): bool, _as_int(), _country_database(), _find_country_by_tag(), _is_int(), _player_from_manager(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf (+7 more)

### Community 13 - "Community 13"
Cohesion: 0.21
Nodes (18): PathLike, Path, str, _candidate_installs(), _candidate_save_dirs(), _first_existing(), _home(), load_config() (+10 more)

### Community 14 - "Community 14"
Cohesion: 0.20
Nodes (9): code:bash (uv sync), code:bash (g++ -std=c++17 melter.cpp -I. -L. -lrakaly -o melter   # add), How it works, Melting binary/ironman saves, On-demand analysis, Setup, Status, Vic3 Economic Analyser (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.60
Nodes (5): _snap(), test_get_specific_date(), test_idempotent_replace(), test_save_and_retrieve(), test_series_and_tags()

### Community 16 - "Community 16"
Cohesion: 0.83
Nodes (3): _defs(), _snap(), test_recommendations_include_categories_and_rank()

### Community 26 - "Community 26"
Cohesion: 0.23
Nodes (13): GoodsValue, market_map(), price_of(), Shared economic helpers for valuing goods flows at current market prices.  All f, Current market price for a good, falling back to its base price., Value a set of input/output goods flows at current market prices.      ``base_pr, A signed signal: >0 means scarce/expensive (worth producing), <0 glut.      Uses, shortage_score() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.30
Nodes (11): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), producible_goods(), What to build: rank building types by projected value-added at current prices, w, Goods the player can actually produce now.      A good is producible if some bui, float (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.31
Nodes (8): analyse_tech_priorities(), _pm_value(), Research priorities: which technologies unlock the most economic value.  For the, TechPriority, float, GameDefs, Snapshot, str

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (8): _defs(), _market(), _snap(), test_construction_payback_and_suggestions(), test_tech_priorities_uplift(), test_what_to_build_demand_weighting(), test_what_to_build_ranks_and_filters(), test_where_to_build_ranking()

### Community 30 - "Community 30"
Cohesion: 0.19
Nodes (12): analyse_construction(), ConstructionReport, QueueItemAnalysis, Construction focus: payback ranking of the queue and suggested additions.  Const, build_recommendations(), Synthesize all analyses into one prioritized, explained action list.  This is th, Recommendation, GameDefs (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.36
Nodes (9): Any, str, analyse_all(), End-to-end ingestion: a ``.v3`` save in, a stored :class:`Snapshot` out.      me, Recursively convert dataclasses/pydantic/containers to JSON-able data., Serialise a GoodSignal including its computed ``status`` (asdict drops     prope, Run every analysis and return one JSON-able payload., _ser() (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.27
Nodes (9): analyse_profitability(), BuildingProfit, _estimate_value_added(), Per-building profitability ranking for the player's buildings.  Prefers the real, Sum value-added across the building's active PMs, scaled by level., Building, float, GameDefs (+1 more)

## Knowledge Gaps
- **56 isolated node(s):** `PathLike`, `bool`, `bool`, `int`, `bool` (+51 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GameDefs` connect `Community 4` to `Community 32`, `Community 0`, `Community 2`, `Community 6`, `Community 8`, `Community 27`, `Community 28`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `Snapshot` connect `Community 0` to `Community 32`, `Community 1`, `Community 3`, `Community 8`, `Community 26`, `Community 27`, `Community 28`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 6` to `Community 0`, `Community 2`, `Community 4`, `Community 7`, `Community 13`, `Community 31`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Snapshot` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`Snapshot` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `MarketGood` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`MarketGood` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `GameDefs` (e.g. with `GameDefs` and `Snapshot`) actually correct?**
  _`GameDefs` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `CountryEconomy` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`CountryEconomy` has 23 INFERRED edges - model-reasoned connections that need verification._