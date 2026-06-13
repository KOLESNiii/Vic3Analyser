"use strict";

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, children = []) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else n.setAttribute(k, v);
  }
  for (const c of [].concat(children)) n.append(c);
  return n;
};

const fmt = (x, d = 0) =>
  x === null || x === undefined ? "—" : Number(x).toLocaleString(undefined, { maximumFractionDigits: d });

let lastDate = null;
let gdpChart = null;
let stratGdpChart = null;
let stratTreasuryChart = null;
let currentTag = null;

// --- tabs -------------------------------------------------------------------
document.querySelectorAll("#tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`[data-panel="${btn.dataset.tab}"]`).classList.add("active");
    if (btn.dataset.tab === "settings") loadSettings();
    if (btn.dataset.tab === "strategy" && !stratGdpChart) runStrategy();
  });
});

// --- table helper -----------------------------------------------------------
function table(cols, rows) {
  const thead = el("tr", {}, cols.map((c) => el("th", { class: c.num ? "num" : "" }, c.label)));
  const body = rows.map((r, ri) =>
    el(
      "tr",
      {},
      cols.map((c) => {
        const v = c.render ? c.render(r, ri) : r[c.key];
        const td = el("td", { class: c.num ? "num" : "" });
        if (v instanceof Node) td.append(v);
        else td.innerHTML = v === undefined || v === null ? "—" : v;
        return td;
      })
    )
  );
  if (!rows.length) return el("p", { class: "hint" }, "Nothing to show.");
  return el("table", {}, [el("thead", {}, thead), el("tbody", {}, body)]);
}

const signed = (x, d = 0) => {
  const cls = x > 0 ? "pos" : x < 0 ? "neg" : "";
  return `<span class="${cls}">${x > 0 ? "+" : ""}${fmt(x, d)}</span>`;
};

// --- renderers --------------------------------------------------------------
function renderRecommendations(recs) {
  const box = $("#recs");
  box.innerHTML = "";
  if (!recs.length) { box.append(el("p", { class: "hint" }, "No recommendations.")); return; }
  for (const r of recs) {
    box.append(
      el("div", { class: "rec" }, [
        el("div", { class: "rec-head" }, [
          el("div", {}, [el("div", { class: "cat" }, r.category), el("div", { class: "rec-title" }, r.title)]),
          el("div", { class: "rec-impact" }, r.impact ? "+" + fmt(r.impact) + "/wk" : ""),
        ]),
        el("div", { class: "rec-detail" }, r.detail),
      ])
    );
  }
}

function renderOverview(data, series) {
  const c = data.country;
  const cards = $("#overview-cards");
  cards.innerHTML = "";
  const items = [
    ["Date", data.date],
    ["Country", data.player_tag],
    ["GDP", fmt(c.gdp)],
    ["Treasury", fmt(c.treasury)],
    ["Weekly balance", c.weekly_balance == null ? "—" : signed(c.weekly_balance)],
  ];
  for (const [label, value] of items) {
    cards.append(el("div", { class: "card" }, [el("div", { class: "label" }, label), el("div", { class: "value", html: String(value) })]));
  }
  drawGdp(series);
}

function drawGdp(series) {
  const ctx = $("#gdp-chart");
  const labels = series.map((s) => s.date);
  const gdp = series.map((s) => s.gdp);
  if (gdpChart) gdpChart.destroy();
  gdpChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ label: "GDP", data: gdp, borderColor: "#d4a23a", tension: 0.2 }] },
    options: { plugins: { legend: { labels: { color: "#9aa3b2" } } }, scales: { x: { ticks: { color: "#9aa3b2" } }, y: { ticks: { color: "#9aa3b2" } } } },
  });
}

function renderMarket(market) {
  $("#market-table").replaceChildren(
    table(
      [
        { label: "Good", key: "good" },
        { label: "Price", num: true, render: (r) => fmt(r.price) },
        { label: "Base", num: true, render: (r) => fmt(r.base_price) },
        { label: "vs base", num: true, render: (r) => (r.price_ratio == null ? "—" : signed((r.price_ratio - 1) * 100, 0) + "%") },
        { label: "Status", render: (r) => `<span class="tag ${r.status}">${r.status}</span>` },
      ],
      market.goods
    )
  );
}

function renderPM(pm) {
  $("#pm-table").replaceChildren(
    table(
      [
        { label: "Building", key: "building_type" },
        { label: "State", num: true, key: "state_id" },
        { label: "Switch", render: (r) => `${r.current_pm || "(none)"} → <b>${r.best_pm}</b>` },
        { label: "+ / level", num: true, render: (r) => signed(r.delta_per_level) },
        { label: "+ total", num: true, render: (r) => signed(r.delta_total) },
      ],
      pm
    )
  );
}

function renderProfit(rows) {
  $("#profit-table").replaceChildren(
    table(
      [
        { label: "Building", key: "building_type" },
        { label: "State", num: true, key: "state_id" },
        { label: "Level", num: true, key: "level" },
        { label: "Profit/wk", num: true, render: (r) => (r.weekly_profit == null ? "—" : signed(r.weekly_profit)) },
        { label: "Per level", num: true, render: (r) => (r.per_level_profit == null ? "—" : signed(r.per_level_profit)) },
        { label: "", render: (r) => (r.estimated ? '<span class="tag est">est.</span>' : "") },
      ],
      rows
    )
  );
}

function renderBuildWhat(rows) {
  $("#build-what-table").replaceChildren(
    table(
      [
        { label: "Building", key: "building_type" },
        { label: "Score", num: true, render: (r) => fmt(r.score) },
        { label: "Value/level", num: true, render: (r) => fmt(r.raw_value_added) },
        { label: "Best PMs", render: (r) => (r.best_pms || []).join(", ") },
        { label: "Notes", render: (r) => (r.notes || []).join("; ") },
      ],
      rows
    )
  );
}

function renderBuildWhere(rows) {
  $("#build-where-table").replaceChildren(
    table(
      [
        { label: "State", render: (r) => r.name || r.state_id },
        { label: "Score", num: true, render: (r) => fmt(r.score, 2) },
        { label: "Free infra", num: true, render: (r) => fmt(r.free_infrastructure) },
        { label: "Unemployed", num: true, render: (r) => fmt(r.unemployment) },
        { label: "Reasons", render: (r) => (r.reasons || []).join("; ") },
      ],
      rows
    )
  );
}

function renderConstruction(c) {
  const wrap = $("#construction-table");
  wrap.innerHTML = "";
  wrap.append(el("p", { class: "hint" }, `Construction points/week: ${fmt(c.points_per_week)}`));
  wrap.append(
    table(
      [
        { label: "Queued building", key: "building_type" },
        { label: "Levels", num: true, key: "levels" },
        { label: "Cost left", num: true, render: (r) => fmt(r.remaining_cost) },
        { label: "Est profit/wk", num: true, render: (r) => fmt(r.est_weekly_profit) },
        { label: "Payback (wk)", num: true, render: (r) => fmt(r.payback_weeks, 1) },
      ],
      c.queue
    )
  );
  if (c.suggested_additions && c.suggested_additions.length) {
    wrap.append(el("p", { class: "hint" }, "Consider adding: " + c.suggested_additions.join(", ")));
  }
}

function renderTech(rows) {
  $("#tech-table").replaceChildren(
    table(
      [
        { label: "Technology", key: "tech" },
        { label: "Potential +/wk", num: true, render: (r) => signed(r.potential_uplift) },
        { label: "Unlocks", render: (r) => (r.unlocks || []).join(", ") },
      ],
      rows
    )
  );
}

// --- strategy & forecast ----------------------------------------------------
async function runStrategy() {
  const btn = $("#strat-run");
  const msg = $("#strat-msg");
  btn.disabled = true;
  msg.textContent = "Optimizing… (this can take a few seconds)";
  const params = new URLSearchParams();
  if (currentTag) params.set("player_tag", currentTag);
  params.set("objective", $("#strat-objective").value);
  params.set("horizon", $("#strat-horizon").value || "60");
  params.set("effort", $("#strat-effort").value || "200");
  params.set("solvency_policy", "hard_buffer");
  params.set("solvency_buffer_weeks", $("#strat-buffer-weeks").value || "12");
  const cap = $("#strat-capacity").value;
  if (cap) params.set("capacity", cap);
  try {
    const res = await fetch("/api/strategy?" + params.toString());
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "failed");
    renderStrategy(body);
    msg.textContent = "";
  } catch (e) {
    msg.textContent = "Could not build a strategy: " + e.message;
    msg.className = "hint err";
  } finally {
    btn.disabled = false;
  }
}

function renderStrategy(d) {
  const s = d.summary;
  const cards = $("#strat-cards");
  cards.innerHTML = "";
  const feasible = s.solvency_feasible;
  const items = [
    ["GDP uplift", s.gdp_uplift_pct == null ? "—" : signed(s.gdp_uplift_pct, 1) + "%"],
    ["Annual growth", signed(s.annual_growth_pct, 1) + "%"],
    ["GDP " + s.horizon_months + "mo", fmt(s.optimized_gdp)],
    ["Final treasury", fmt(s.final_treasury)],
    ["Reserve needed", fmt(s.reserve_required)],
    ["Min headroom", fmt(s.min_headroom)],
    ["Solvency", feasible ? "Feasible" : "Below reserve"],
    ["Std. of living", `${fmt(s.sol0, 1)} → ${fmt(s.final_sol, 1)}`],
    ["Levels to build", fmt(s.total_levels)],
    ["Construction", `${fmt(s.construction_start_capacity, 0)} → ${fmt(s.construction_final_capacity, 0)}/wk`],
  ];
  if (s.construction_frame_points_mult > 1) {
    items.push(["Frame upgrade", `${s.construction_frame_current} → ${s.construction_frame_best} (×${fmt(s.construction_frame_points_mult, 2)})`]);
  }
  if (s.economic_law) {
    items.push(["Economic law", s.economic_law + (s.economic_law_scenario ? " (scenario)" : "")]);
  }
  if (s.investment_pool_weekly) {
    items.push(["Private build", `${fmt(s.investment_pool_weekly, 0)}/wk pool`]);
  }
  for (const [label, value] of items) {
    cards.append(el("div", { class: "card" }, [el("div", { class: "label" }, label), el("div", { class: "value", html: String(value) })]));
  }

  const a = d.assumptions;
  const banner = $("#strat-assumptions");
  banner.classList.remove("hidden");
  const notes = (a.notes || []).join(" ");
  let solvencyNote = "";
  if (!feasible) {
    solvencyNote = s.baseline_solvency_feasible
      ? ' <span class="neg">No growth plan stayed above the reserve; showing the least bad candidate.</span>'
      : ' <span class="neg">Baseline is already below the reserve; rebuild cash headroom before expanding.</span>';
  }
  banner.innerHTML =
    `<b>Assumptions (estimates):</b> objective “${s.objective}”, horizon ${s.horizon_months} months, ` +
    `construction ${fmt(a.construction_capacity, 0)}/wk ${a.capacity_from_save ? "(from save)" : "(estimated)"}, ` +
    `reserve ${fmt(s.reserve_required)} (${fmt(s.solvency_buffer_weeks, 0)} weeks expenses), ` +
    `market share ${fmt(a.world_market_share * 100, 0)}% ${a.elasticity_calibrated ? "(calibrated from history)" : "(assumed)"}. ` +
    notes + solvencyNote +
    ((d.pareto && d.pareto.length > 1)
      ? "<br><b>Growth vs solvency trade-off:</b> " +
        d.pareto
          .map((p) => `${signed(p.growth_pct, 1)}%/yr @ headroom ${fmt(p.min_headroom)}${p.feasible ? "" : " (below reserve)"}`)
          .join("  ·  ")
      : "");

  // forecast charts
  const labels = d.series.months;
  stratGdpChart = lineChart("#strat-gdp-chart", stratGdpChart, labels, [
    { label: "Optimized GDP", data: d.series.optimized_gdp, color: "#d4a23a" },
    { label: "Do nothing", data: d.series.baseline_gdp, color: "#6b7280" },
  ]);
  stratTreasuryChart = lineChart("#strat-treasury-chart", stratTreasuryChart, labels, [
    { label: "Optimized treasury", data: d.series.optimized_treasury, color: "#3a9bd4" },
    { label: "Do nothing", data: d.series.baseline_treasury, color: "#6b7280" },
  ]);

  // cascade narrative
  const ul = $("#strat-cascade");
  ul.innerHTML = "";
  for (const line of d.cascade || []) ul.append(el("li", {}, line));

  // build order
  $("#strat-build").replaceChildren(
    table(
      [
        { label: "#", num: true, render: (_r, i) => i + 1 },
        { label: "Building", key: "name" },
        { label: "Levels", num: true, key: "levels" },
        { label: "Constr. cost", num: true, render: (r) => fmt(r.construction_cost) },
        { label: "Placement", render: placementText },
        { label: "Production methods", render: (r) => (r.pms || []).map((p) => p.replace(/^pm_/, "")).join(", ") },
      ],
      d.build_order || []
    )
  );

  // PM switches
  $("#strat-pm").replaceChildren(
    table(
      [
        { label: "Building", key: "name" },
        { label: "State", num: true, render: (r) => (r.state_id == null ? "—" : r.state_id) },
        { label: "Switch", render: (r) => `${(r.from_pm || "(none)").replace(/^pm_/, "")} → <b>${r.to_pm.replace(/^pm_/, "")}</b>` },
        { label: "+ value", num: true, render: (r) => signed(r.delta_value) },
      ],
      d.pm_switches || []
    )
  );

  // tech
  $("#strat-tech").replaceChildren(
    table(
      [
        { label: "Technology", key: "tech" },
        { label: "Era", render: (r) => (r.era || "—").replace(/^era_/, "Era ") },
        { label: "~Weeks", num: true, render: (r) => fmt(r.weeks) },
        { label: "Unlocks", render: (r) => [...(r.unlocks_pms || []), ...(r.unlocks_buildings || [])].slice(0, 5).join(", ") },
      ],
      d.tech_program || []
    )
  );

  // price outlook
  $("#strat-prices").replaceChildren(
    table(
      [
        { label: "Good", key: "good" },
        { label: "Now (×base)", num: true, render: (r) => fmt(r.start_ratio, 2) },
        { label: "Projected (×base)", num: true, render: (r) => fmt(r.projected_ratio, 2) },
        { label: "Change", num: true, render: (r) => signed(r.change_pct, 0) + "%" },
      ],
      d.price_outlook || []
    )
  );
}

function placementText(r) {
  const alloc = r.state_allocations || [];
  if (!alloc.length) return r.suggested_state == null ? "—" : String(r.suggested_state);
  return alloc
    .map((a) => {
      const name = a.state_name || (a.state_id == null ? "Unknown" : `State ${a.state_id}`);
      return `${name}: ${fmt(a.levels, 0)}`;
    })
    .join(", ");
}

function lineChart(sel, existing, labels, datasets) {
  const ctx = $(sel);
  if (existing) existing.destroy();
  return new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: datasets.map((ds) => ({
        label: ds.label,
        data: ds.data,
        borderColor: ds.color,
        backgroundColor: ds.color,
        tension: 0.2,
        pointRadius: 0,
        borderWidth: 2,
      })),
    },
    options: {
      plugins: { legend: { labels: { color: "#9aa3b2" } } },
      scales: { x: { ticks: { color: "#9aa3b2", maxTicksLimit: 12 } }, y: { ticks: { color: "#9aa3b2" } } },
    },
  });
}

$("#strat-run").addEventListener("click", runStrategy);

// --- settings ---------------------------------------------------------------
function setMsg(text, isError = false) {
  const m = $("#settings-msg");
  m.textContent = text;
  m.className = "hint" + (isError ? " err" : "");
}

async function loadSettings() {
  try {
    const s = await (await fetch("/api/settings")).json();
    $("#auto-watch").checked = !!s.auto_watch;
    $("#watch-mode").value = s.watch_mode || "any";
    $("#watch-mode-field").style.opacity = s.auto_watch ? "1" : ".5";
    $("#watch-mode").disabled = !s.auto_watch;
    $("#saves-dir").textContent = s.save_dir ? "From: " + s.save_dir : "No save folder configured (set save_dir in config.toml).";
  } catch (e) {
    setMsg("Could not load settings.", true);
  }
  await loadSaves();
}

async function loadSaves() {
  try {
    const saves = await (await fetch("/api/saves")).json();
    renderSaves(saves);
  } catch (e) {
    $("#saves-table").replaceChildren(el("p", { class: "hint err" }, "Could not list saves."));
  }
}

function renderSaves(saves) {
  $("#saves-table").replaceChildren(
    table(
      [
        { label: "Save", render: (r) => `${r.name}${r.is_autosave ? ' <span class="tag">auto</span>' : ""}` },
        { label: "Modified", render: (r) => new Date(r.mtime * 1000).toLocaleString() },
        { label: "Size", num: true, render: (r) => fmt(r.size / 1e6, 1) + " MB" },
        {
          label: "",
          render: (r) => {
            const b = el("button", { class: "mini" }, "Analyse");
            b.addEventListener("click", () => analyseSave(r.path, b));
            return b;
          },
        },
      ],
      saves
    )
  );
}

async function analyseSave(path, btn) {
  if (btn) btn.disabled = true;
  setMsg("Analysing…");
  try {
    const res = await fetch("/api/ingest?path=" + encodeURIComponent(path), { method: "POST" });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "failed");
    setMsg("Analysed save dated " + body.ingested + ".");
    await refreshStatus();
  } catch (e) {
    setMsg("Analysis failed: " + e.message, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function postSettings(params, okMsg) {
  try {
    const res = await fetch("/api/settings?" + params, { method: "POST" });
    const body = await res.json();
    $("#watch-mode").disabled = !body.auto_watch;
    $("#watch-mode-field").style.opacity = body.auto_watch ? "1" : ".5";
    setMsg(typeof okMsg === "function" ? okMsg(body) : okMsg);
  } catch (err) {
    setMsg("Could not change setting.", true);
  }
}

$("#auto-watch").addEventListener("change", (e) =>
  postSettings("auto_watch=" + e.target.checked, (b) =>
    b.watching ? "Watching the save folder." : "Continuous watching off — analyse on demand."
  )
);

$("#watch-mode").addEventListener("change", (e) =>
  postSettings("watch_mode=" + e.target.value, (b) =>
    b.watch_mode === "autosave" ? "Watching autosaves only." : "Watching every new save."
  )
);

async function runAnalyseLatest(btn, autosaveOnly) {
  btn.disabled = true;
  setMsg(autosaveOnly ? "Analysing latest autosave…" : "Analysing latest save…");
  try {
    const res = await fetch("/api/analyse-latest?autosave_only=" + !!autosaveOnly, { method: "POST" });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "failed");
    setMsg("Analysed save dated " + body.ingested + ".");
    await refreshStatus();
    await loadSaves();
  } catch (err) {
    setMsg("Analysis failed: " + err.message, true);
  } finally {
    btn.disabled = false;
  }
}

$("#analyse-latest").addEventListener("click", (e) => runAnalyseLatest(e.target, false));
$("#analyse-latest-auto").addEventListener("click", (e) => runAnalyseLatest(e.target, true));

// --- polling ----------------------------------------------------------------
async function refreshStatus() {
  try {
    const s = await (await fetch("/api/status")).json();
    const parts = [];
    parts.push(s.defs_loaded ? "defs ✓" : "defs ✗");
    if (s.player_tags && s.player_tags.length) parts.push("tags: " + s.player_tags.join(", "));
    if (s.last_ingest) parts.push("save: " + s.last_ingest);
    $("#status").textContent = parts.join("  ·  ");

    const banner = $("#banner");
    if (!s.defs_loaded) {
      banner.classList.remove("hidden");
      banner.textContent = "Game definitions not loaded: " + (s.defs_error || "set vic3_install in config.toml");
    } else if (!s.last_ingest) {
      banner.classList.remove("hidden");
      banner.textContent = s.auto_watch
        ? "Waiting for a save. The watcher ingests new saves from " + (s.save_dir || "(no save_dir set)") + "."
        : "On-demand mode: open Settings and click “Analyse latest save” to get started.";
    } else {
      banner.classList.add("hidden");
    }

    if (s.last_ingest && s.last_ingest !== lastDate) {
      lastDate = s.last_ingest;
      await refreshAnalysis(s.player_tags && s.player_tags[0]);
    }
  } catch (e) {
    $("#status").textContent = "server unreachable";
  }
}

async function refreshAnalysis(tag) {
  currentTag = tag || null;
  const data = await (await fetch("/api/analysis")).json();
  const series = tag ? await (await fetch(`/api/series?player_tag=${tag}`)).json() : [];
  renderRecommendations(data.recommendations || []);
  renderOverview(data, series);
  renderMarket(data.market);
  renderPM(data.pm_switches || []);
  renderProfit(data.profitability || []);
  renderBuildWhat(data.build_what || []);
  renderBuildWhere(data.build_where || []);
  renderConstruction(data.construction || { queue: [] });
  renderTech(data.tech || []);
}

refreshStatus();
setInterval(refreshStatus, 5000);
