# Graph Report - analyser  (2026-06-10)

## Corpus Check
- 41 files · ~15,516 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 480 nodes · 1252 edges · 26 communities (23 shown, 3 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 253 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fa3151a8`
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

## God Nodes (most connected - your core abstractions)
1. `Snapshot` - 39 edges
2. `MarketGood` - 28 edges
3. `ActivePM` - 25 edges
4. `Building` - 25 edges
5. `CountryEconomy` - 25 edges
6. `GameDefs` - 25 edges
7. `Config` - 24 edges
8. `TechState` - 23 edges
9. `StateInfo` - 21 edges
10. `parse()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `test_full_api_flow()` --calls--> `create_app()`  [INFERRED]
  tests/test_api.py → src/vic3analyser/api/server.py
- `test_on_demand_analysis()` --calls--> `create_app()`  [INFERRED]
  tests/test_api.py → src/vic3analyser/api/server.py
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Config` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Path` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py

## Communities (26 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.16
Nodes (52): BaseModel, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState, CountryEconomy (+44 more)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (17): analyse_where_to_build(), _free_arable(), _norm(), Where to build: rank the player's states by capacity to host new economic buildi, StateCapacity, float, int, Snapshot (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (29): Any, AppState, create_app(), is_autosave(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, Begin watching ``save_dir`` for new saves. Returns whether it ran., Toggle continuous watching at runtime. Returns the effective state.          Ena (+21 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (63): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), What to build: rank building types by projected value-added at current prices, w, analyse_construction(), ConstructionReport, QueueItemAnalysis (+55 more)

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (19): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _manifest(), Load the static game-rule definitions from a Victoria 3 ``common/`` tree.  These (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (32): coerce_key(), coerce_scalar(), _MultiList, parse(), parse_file(), _Parser, A parser for the Clausewitz/Jomini text format used by Paradox files.  Handles t, A list produced by collapsing duplicate keys (vs an array literal). (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (35): SnapshotStore, Config, GameDefs, Path, Snapshot, str, _cfg(), _make_install() (+27 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (24): bytes, _decode(), _looks_like_text(), melt_save(), _melt_zip(), MeltError, MeltResult, _pick() (+16 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (23): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.26
Nodes (24): $(), analyseSave(), drawGdp(), el(), fmt(), loadSaves(), loadSettings(), postSettings() (+16 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (8): Connection, Path, Snapshot, str, SQLite time-series store for extracted snapshots.  Each snapshot is stored whole, Insert or replace a snapshot (idempotent on player_tag+date)., Return denormalised headline metrics over time for charting.          ``metrics`, SnapshotStore

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (12): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`), Tech (`analysis/tech.py`) (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.29
Nodes (12): _as_int(), _country_database(), _find_country_by_tag(), _is_int(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf, resolve_player(), _tag_of() (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.21
Nodes (18): PathLike, Path, str, _candidate_installs(), _candidate_save_dirs(), _first_existing(), _home(), load_config() (+10 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (7): code:bash (uv sync), How it works, On-demand analysis, Setup, Status, Vic3 Economic Analyser, Watch mode

### Community 15 - "Community 15"
Cohesion: 0.60
Nodes (5): _snap(), test_get_specific_date(), test_idempotent_replace(), test_save_and_retrieve(), test_series_and_tags()

### Community 16 - "Community 16"
Cohesion: 0.83
Nodes (3): _defs(), _snap(), test_recommendations_include_categories_and_rank()

## Knowledge Gaps
- **51 isolated node(s):** `Watch mode`, `On-demand analysis`, `code:bash (uv sync)`, `Status`, `float` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Snapshot` connect `Community 0` to `Community 8`, `Community 1`, `Community 10`, `Community 3`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `parse()` connect `Community 5` to `Community 3`, `Community 6`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `GameDefs` connect `Community 4` to `Community 0`, `Community 2`, `Community 3`, `Community 6`, `Community 8`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Snapshot` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`Snapshot` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `MarketGood` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`MarketGood` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ActivePM` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`ActivePM` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Building` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`Building` has 18 INFERRED edges - model-reasoned connections that need verification._