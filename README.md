# Vic3 Economic Analyser

An external dashboard that automates the economic analysis a Victoria 3 player does by hand —
ranking buildings and production methods, and recommending **what to build, where to build, what to
research, and what to focus the economy on**.

It uses only **player-visible** data (market prices, your own buildings/balances/pops, construction
queue, researched techs). It does **not** read AI strategic plans or hidden state.

## How it works

1. Watches your Victoria 3 autosave folder.
2. On each new save: melts it to plaintext (via [rakaly](https://github.com/rakaly/cli) for binary/ironman
   saves), parses it, and extracts your country's economic state.
3. Joins that dynamic state with the static game rules from your install's `common/`
   (`building_types`, `production_methods`, `goods`, `technology`) to compute counterfactuals.
4. Serves an interactive dashboard on `http://127.0.0.1:8000` with analysis + a ranked action list.

"Live" means per game-month — the natural granularity of the Vic3 economy.

## Setup

```bash
uv sync
# Edit config.toml if auto-detection doesn't find your install / save folder.
uv run vic3analyser
```

For binary/ironman saves, install the `rakaly` CLI and put it on PATH (or set `rakaly_bin` in
`config.toml`). Alternatively set `save_file_format = "text"` in your Vic3 `pdx_settings.json` to skip
melting.

## Status

Early development. See `/home/kolesniii/.claude/plans/` for the implementation plan and `SCHEMA.md`
(once written) for the mapped save-file structure.
