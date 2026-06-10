# Graph Report - analyser  (2026-06-09)

## Corpus Check
- 41 files · ~14,004 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 454 nodes · 1181 edges · 26 communities (23 shown, 3 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 250 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `54e06254`
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
- `_cfg()` --calls--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Config` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Path` --uses--> `Paths`  [INFERRED]
  tests/test_melt.py → src/vic3analyser/config.py
- `Config` --uses--> `Config`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py
- `Path` --uses--> `Config`  [INFERRED]
  tests/test_api.py → src/vic3analyser/config.py

## Communities (26 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.16
Nodes (52): BaseModel, ConstructionState, CountryEconomy, ActivePM, Building, ConstructionItem, ConstructionState, CountryEconomy (+44 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (38): analyse_what_to_build(), _best_available_pm(), BuildCandidate, _mean_signal(), What to build: rank building types by projected value-added at current prices, w, analyse_where_to_build(), _free_arable(), _norm() (+30 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (15): AppState, Holds shared, mutable server state behind a lock., Process one save (thread-safe). Returns the snapshot date., On startup, ingest the newest save already in the folder., Watchdog handler that fires on new/updated ``.v3`` saves.  Saves are large and w, SaveHandler, FileSystemEvent, FileSystemEventHandler (+7 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (36): analyse_market(), GoodSignal, MarketReport, Market analysis: which goods are in shortage (expensive) or glut (cheap).  A sho, GoodsValue, market_map(), price_of(), Shared economic helpers for valuing goods flows at current market prices.  All f (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (19): _category_files(), _common_roots(), GameDefs, _good_from_modifier(), _load_category(), load_defs(), _manifest(), Load the static game-rule definitions from a Victoria 3 ``common/`` tree.  These (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (32): coerce_key(), coerce_scalar(), _MultiList, parse(), parse_file(), _Parser, A parser for the Clausewitz/Jomini text format used by Paradox files.  Handles t, A list produced by collapsing duplicate keys (vs an array literal). (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (24): _cfg(), _make_install(), Config, Path, End-to-end API test: synthetic install + crafted plaintext save through the full, test_full_api_flow(), _cfg(), _make_install() (+16 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (24): bytes, _decode(), _looks_like_text(), melt_save(), _melt_zip(), MeltError, MeltResult, _pick() (+16 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (23): _active_pm_in_group(), analyse_pm_switches(), _is_available(), optimise_building(), _pm_value(), PMOption, PMRecommendation, Production-method optimisation — the counterfactual core.  For each of the playe (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.36
Nodes (17): $(), drawGdp(), el(), fmt(), refreshAnalysis(), refreshStatus(), renderBuildWhat(), renderBuildWhere() (+9 more)

### Community 10 - "Community 10"
Cohesion: 0.27
Nodes (7): Connection, Path, Snapshot, str, Insert or replace a snapshot (idempotent on player_tag+date)., Return denormalised headline metrics over time for charting.          ``metrics`, SnapshotStore

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (12): Building profitability (`analysis/profitability.py`), Construction (`analysis/construction.py`), Conventions, Fields the analysis needs (per area), How to (re)confirm this map, Market (`analysis/market.py`), PM optimisation (`analysis/pm_optimizer.py`), Tech (`analysis/tech.py`) (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.29
Nodes (12): _as_int(), _country_database(), _find_country_by_tag(), _is_int(), Enforce the player-visibility rule and resolve which country is the player.  The, Return ``(country_id, tag)`` for the player country.      Resolution order: conf, resolve_player(), _tag_of() (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (40): create_app(), main(), FastAPI server: serves the dashboard and analysis API, and watches the autosave, FastAPI, PathLike, SnapshotStore, Path, str (+32 more)

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (5): code:bash (uv sync), How it works, Setup, Status, Vic3 Economic Analyser

### Community 15 - "Community 15"
Cohesion: 0.60
Nodes (5): _snap(), test_get_specific_date(), test_idempotent_replace(), test_save_and_retrieve(), test_series_and_tags()

### Community 16 - "Community 16"
Cohesion: 0.83
Nodes (3): _defs(), _snap(), test_recommendations_include_categories_and_rank()

## Knowledge Gaps
- **49 isolated node(s):** `PathLike`, `bool`, `bool`, `int`, `bool` (+44 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Snapshot` connect `Community 0` to `Community 8`, `Community 1`, `Community 3`, `Community 13`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 13` to `Community 0`, `Community 4`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `parse()` connect `Community 5` to `Community 13`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Snapshot` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`Snapshot` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `MarketGood` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`MarketGood` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ActivePM` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`ActivePM` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Building` (e.g. with `ConstructionState` and `CountryEconomy`) actually correct?**
  _`Building` has 18 INFERRED edges - model-reasoned connections that need verification._