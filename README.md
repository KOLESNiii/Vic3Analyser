# Vic3 Economic Analyser

An external dashboard that automates the economic analysis a Victoria 3 player does by hand —
ranking buildings and production methods, and recommending **what to build, where to build, what to
research, and what to focus the economy on**.

It uses only **player-visible** data (market prices, your own buildings/balances/pops, construction
queue, researched techs). It does **not** read AI strategic plans or hidden state.

On top of the per-item recommendations, a **Strategy & Forecast** engine plans the whole economy at
once (see below).

## Strategy & Forecast — system-level optimization

The per-item analyses (PM switches, what/where to build, tech) each value a single change at the
*current, frozen* market price. That is locally correct but ignores that acting on a recommendation
**moves the whole system**: building eight steel mills floods steel (its price falls, so the eighth
mill earns far less than the first) and drains iron and coal (their prices rise, so *those* become
the next best thing to build).

The Strategy engine models that feedback and searches for the plan that **maximizes economic
growth while staying solvent** over a multi-year horizon:

- **Cascading prices.** It inverts Vic3's price mechanic (price is clamped to ±75% of base by
  supply/demand), so the *current* price reveals the *current* imbalance. Market depth is anchored
  on your own observed production scale — and *calibrated from your save history* (how your prices
  actually moved as your production changed) when enough snapshots exist.
- **Forecasting.** It steps the economy month-by-month: construction capacity is spent against the
  queue, buildings phase in over time, the market re-settles to equilibrium each step, and GDP,
  treasury, employment and standard-of-living are projected — charted against a do-nothing baseline.
  Real construction points/week are read from the save when a queue exists, and construction-sector
  expansion is modeled as a growth lever: extra sectors add capacity but consume construction goods
  and can strain the treasury.
- **Hard solvency buffer.** Plans are only treated as feasible if projected treasury plus credit
  stays above a reserve buffer for the full forecast. The default reserve is 12 weeks of current
  expenses, so the optimizer can still borrow for growth but will not recommend a plan that runs the
  country down to the credit limit.
- **Trying many combinations.** A greedy water-filling pass allocates each slice of construction to
  the best marginal building *at the evolving equilibrium* (so the marginal winner rotates as goods
  saturate — the cascade), then a local search perturbs the plan to escape local optima.
- **Capacity-aware placement.** Static state-region definitions supply total arable land and
  capped resource deposits, so farms/mines/logging/fishing are bounded by visible state capacity.
  The build order includes state-level placement slices where those levels can actually fit.
- **Objectives.** Growth rate is the default target, constrained by the solvency buffer. GDP,
  treasury, and the older composite score are still switchable on the dashboard, but infeasible plans
  are rejected before objective scores are compared.

Open the **Strategy & Forecast** tab and click **Plan**. Everything is an *estimate* from
player-visible data: absolute world supply/demand and the exact GDP/SoL formulas aren't in saves, so
market depth, GDP and SoL are modeled (the assumptions banner says exactly what was assumed or
calibrated). Construction capacity is a first-class, overridable input; when the save has no active
queue it falls back to an estimate. Tune the horizon, capacity, objective and search effort right on
the tab, or set defaults under `[optimize]` in `config.toml`.

## How it works

1. Watches your Victoria 3 autosave folder.
2. On each new save: melts it to plaintext (via a [rakaly](https://github.com/rakaly) melter for
   binary/ironman saves), parses it, and extracts your country's economic state.
3. Joins that dynamic state with the static game rules from your install's `common/`
   (`building_types`, `production_methods`, `goods`, `technology`) to compute counterfactuals.
4. Serves an interactive dashboard on `http://127.0.0.1:8000` with analysis + a ranked action list.

"Live" means per game-month — the natural granularity of the Vic3 economy.

### Watch mode

While watching is on (`auto_watch = true`), `watch_mode` controls which saves
trigger analysis:

- `"any"` (default) — every new save, autosaves and manual saves alike.
- `"autosave"` — only Vic3's `autosave*.v3` files, ignoring manual saves.

Set it in `config.toml` or switch it live on the **Settings** tab.

### On-demand analysis

Prefer to analyse only when you choose to? Turn off continuous watching
(`auto_watch = false` in `config.toml`, or toggle it on the dashboard's
**Settings** tab) and analyse on demand instead:

- **Analyse latest save** / **Analyse latest autosave** — one click reads the
  most recent save (of any kind, or the most recent autosave). Use it once at
  the start of a game to plan your opening before anything happens, or right
  after a major event.
- **Available saves** — pick any specific save (autosaves are flagged) and
  analyse it directly.

## Setup

```bash
uv sync
# Edit config.toml if auto-detection doesn't find your install / save folder.
uv run vic3analyser
```

### Melting binary/ironman saves

Binary saves (the `zip_binary_all` default, including ironman) must be melted to plaintext first. The
analyser shells out to an external [rakaly](https://github.com/rakaly) melter for this. Two options,
auto-detected on PATH (`melter` preferred, then `rakaly`) or set explicitly via `rakaly_bin` in
`config.toml`:

- **`melter` (recommended).** Build the small thin wrapper from
  [rakaly/librakaly](https://github.com/rakaly/librakaly): grab `rakaly.h` and the prebuilt library
  from its Releases, drop in the sample `melter.cpp`, and compile:

  ```bash
  g++ -std=c++17 melter.cpp -I. -L. -lrakaly -o melter   # add -lpthread -ldl -lm on Linux
  ```

  This wrapper has explicit Vic3 support (`rakaly::parseVic3`) and handles the `.v3` container
  natively. The analyser invokes it as `melter save <file>`.

- **`rakaly` CLI.** Alternatively install the standalone [rakaly CLI](https://github.com/rakaly/cli);
  it shares the same Rust core and also supports Vic3 (`rakaly melt --format vic3`).

Either way, if you'd rather skip melting entirely, set `save_file_format = "text"` in your Vic3
`pdx_settings.json` so the game writes plaintext saves.

## Status

Early development. See `/home/kolesniii/.claude/plans/` for the implementation plan and `SCHEMA.md`
(once written) for the mapped save-file structure.
