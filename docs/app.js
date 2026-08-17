/* Shortfall. No innerHTML anywhere - a security hook blocks it, and the page
   prints third-party company names. */

const FLAGS = [
  ["accruals",         "Accruals vs cash"],
  ["working_capital",  "Receivables & inventory"],
  ["share_count_roic", "Share count vs returns"],
  ["goodwill",         "Goodwill share"],
  ["tax_rate",         "Tax rate"],
  ["stock_comp",       "Stock compensation"],
];

const NS = "http://www.w3.org/2000/svg";
const state = { weights: {}, market: "all", eventsOnly: false };
FLAGS.forEach(([k]) => (state.weights[k] = 1));

function el(tag, props = {}, parent = null) {
  const n = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (k === "text") n.textContent = v;
    else if (k === "class") n.className = v;
    else n.setAttribute(k, v);
  });
  if (parent) parent.appendChild(n);
  return n;
}

function svgEl(tag, attrs = {}, parent = null) {
  const n = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
  if (parent) parent.appendChild(n);
  return n;
}

/* Weighted mean over APPLICABLE flags only, renormalising so an inapplicable
   flag's weight never counts as a zero. Mirrors score.py exactly. */
function composite(row, weights) {
  let num = 0, den = 0;
  FLAGS.forEach(([k]) => {
    const f = row.flags[k];
    if (!f || !f.applicable || f.rank == null) return;
    num += f.rank * weights[k];
    den += weights[k];
  });
  return den ? num / den : null;
}

function equalWeights() {
  const w = {};
  FLAGS.forEach(([k]) => (w[k] = 1));
  return w;
}

function visible() {
  return window.SHORTFALL.names.filter((r) => {
    if (state.market !== "all" && r.market !== state.market) return false;
    if (state.eventsOnly && !(r.events && r.events.length)) return false;
    return true;
  });
}

function scored() {
  const rows = visible().map((r) => ({
    row: r,
    score: composite(r, state.weights),
    base: composite(r, equalWeights()),
  })).filter((x) => x.score != null);
  rows.sort((a, b) => b.score - a.score);
  return rows;
}

function render() {
  const rows = scored();
  renderScatter(rows);
  renderCards(rows);
  const note = document.getElementById("scatterNote");
  note.textContent = `${rows.length} companies. Hover a point for the name. `
    + `Cards below are the top ${Math.min(rows.length, 100)} by score.`;
}

function renderCards(rows) {
  const host = document.getElementById("cards");
  host.textContent = "";
  rows.slice(0, 100).forEach(({ row, score, base }) => {
    const card = el("article", { class: "card" }, host);
    const head = el("header", {}, card);
    el("h3", { text: row.name }, head);
    el("span", { class: "ticker", text: row.ticker }, head);
    el("span", { class: "score", text: score.toFixed(0) }, head);
    if (Math.abs(score - base) >= 0.5) {
      el("span", { class: "base", text: `equal weight: ${base.toFixed(0)}` }, head);
    }
    (row.events || []).forEach((e) =>
      el("span", { class: "badge", text: e.label }, card));
    if (row.goodwill_exceeds_equity) {
      el("span", { class: "badge", text: "Goodwill exceeds book equity" }, card);
    }
    const list = el("dl", { class: "flags" }, card);
    FLAGS.forEach(([k, label]) => {
      const f = row.flags[k];
      const on = f && f.applicable && f.rank != null;
      // Each label/value pair gets its own wrapper. Without it the dt and dd flow
      // through the grid independently and a value ends up beside the WRONG flag,
      // which on this page is a correctness bug rather than a cosmetic one.
      const pair = el("div", { class: "pair" }, list);
      el("dt", { text: label }, pair);
      const dd = el("dd", {
        class: on ? "on" : "na",
        text: on ? f.rank.toFixed(0) : "n/a",
        title: f && !f.applicable ? f.reason : "",
      }, pair);
      if (on) dd.style.setProperty("--w", f.rank.toFixed(0) + "%");
    });
    el("p", { class: "applicable",
              text: `${row.applicable} of 6 flags applicable` }, card);
  });
}

/* Money formatted the way a reader reads it, not the way it is stored. */
function money(v) {
  if (v == null) return "size not reported";
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(1) + "tn";
  if (a >= 1e9) return (v / 1e9).toFixed(1) + "bn";
  if (a >= 1e6) return (v / 1e6).toFixed(0) + "m";
  return String(Math.round(v));
}

/* X is company SIZE on a log scale, Y is the score.

   The first version plotted score against rank position, which can only ever draw
   a descending curve - it looked like analysis and contained none. Size is a real
   second dimension: it separates "a big company scoring high", which is worth a
   look, from "a small one", which usually is not. */
function renderScatter(rows) {
  const svg = document.getElementById("scatterSvg");
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const W = svg.clientWidth || 900, H = 340;
  const L = 40, R = 16, T = 14, B = 34;

  const withSize = rows.filter((r) => r.row.assets && r.row.assets > 0);
  if (!withSize.length) return;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

  const logs = withSize.map((r) => Math.log10(r.row.assets));
  const lo = Math.floor(Math.min(...logs)), hi = Math.ceil(Math.max(...logs));
  const px = (v) => L + ((Math.log10(v) - lo) / (hi - lo || 1)) * (W - L - R);
  const py = (v) => H - B - (v / 100) * (H - T - B);

  [0, 25, 50, 75, 100].forEach((v) => {
    svgEl("line", { x1: L, y1: py(v), x2: W - R, y2: py(v), class: "grid" }, svg);
    const t = svgEl("text", { x: L - 8, y: py(v) + 4, class: "axislabel", "text-anchor": "end" }, svg);
    t.textContent = String(v);
  });
  for (let e = lo; e <= hi; e++) {
    const t = svgEl("text", { x: px(Math.pow(10, e)), y: H - 12, class: "axislabel", "text-anchor": "middle" }, svg);
    t.textContent = money(Math.pow(10, e));
  }
  const yl = svgEl("text", { x: L - 8, y: T + 2, class: "axislabel", "text-anchor": "end" }, svg);
  yl.textContent = "score";
  const xl = svgEl("text", { x: W - R, y: H - 12, class: "axislabel", "text-anchor": "end" }, svg);
  xl.textContent = "total assets";

  const layer = svgEl("g", {}, svg);
  withSize.forEach(({ row, score, base }) => {
    const x = px(row.assets), y = py(score), yb = py(base);
    if (Math.abs(y - yb) > 1) {
      svgEl("line", { x1: x, y1: yb, x2: x, y2: y, class: "shift" }, layer);
    }
    const flagged = row.events && row.events.length;
    const dot = svgEl("circle", {
      cx: x, cy: y, r: flagged ? 4.5 : 3.2,
      class: flagged ? "dot flagged" : "dot",
      "data-ticker": row.ticker,
    }, layer);
    dot.addEventListener("mouseenter", () => showTip(row, score, x, y));
    dot.addEventListener("mouseleave", hideTip);
  });
}

function showTip(row, score, x, y) {
  const tip = document.getElementById("tip");
  tip.textContent = "";
  el("strong", { text: row.name }, tip);
  el("span", { class: "t-ticker", text: row.ticker }, tip);
  const fired = FLAGS.filter(([k]) => {
    const f = row.flags[k];
    return f && f.applicable && f.rank != null && f.rank >= 80;
  }).map(([, label]) => label);
  el("span", {
    class: "t-line",
    text: `score ${score.toFixed(0)} · ${money(row.assets)} assets · ${row.applicable} of 6 flags`,
  }, tip);
  if (fired.length) el("span", { class: "t-line", text: "highest: " + fired.join(", ") }, tip);
  (row.events || []).forEach((e) => el("span", { class: "t-event", text: e.label }, tip));

  const svg = document.getElementById("scatterSvg");
  const box = svg.getBoundingClientRect();
  const sx = box.left + (x / svg.viewBox.baseVal.width) * box.width;
  const sy = box.top + (y / svg.viewBox.baseVal.height) * box.height;
  tip.style.display = "block";
  const tw = tip.offsetWidth;
  tip.style.left = Math.max(8, Math.min(window.innerWidth - tw - 8, sx - tw / 2)) + "px";
  tip.style.top = (sy + window.scrollY - tip.offsetHeight - 14) + "px";
}

function hideTip() {
  document.getElementById("tip").style.display = "none";
}

function buildSliders() {
  const host = document.getElementById("sliders");
  FLAGS.forEach(([k, label]) => {
    const wrap = el("label", { class: "slider" }, host);
    el("span", { text: label }, wrap);
    const input = el("input", {
      type: "range", min: "0", max: "3", step: "0.1", value: "1",
      "aria-label": `Weight for ${label}`,
    }, wrap);
    const out = el("output", { text: "1.0" }, wrap);
    input.addEventListener("input", () => {
      state.weights[k] = parseFloat(input.value);
      out.textContent = parseFloat(input.value).toFixed(1);
      render();
    });
  });
  document.getElementById("resetWeights").addEventListener("click", () => {
    state.weights = equalWeights();
    host.querySelectorAll("input").forEach((i) => { i.value = "1"; });
    host.querySelectorAll("output").forEach((o) => { o.textContent = "1.0"; });
    render();
  });
}

function buildFilters() {
  const host = document.getElementById("filters");
  const markets = Array.from(new Set(window.SHORTFALL.names.map((r) => r.market))).sort();

  const mLabel = el("label", { text: "Market" }, host);
  const sel = el("select", {}, mLabel);
  el("option", { value: "all", text: "All markets" }, sel);
  markets.forEach((m) => el("option", { value: m, text: m }, sel));
  sel.addEventListener("change", () => { state.market = sel.value; render(); });

  const eLabel = el("label", { text: "" }, host);
  const cb = el("input", { type: "checkbox" }, eLabel);
  el("span", { text: "Only companies with a restatement, auditor change or late filing" }, eLabel);
  cb.addEventListener("change", () => { state.eventsOnly = cb.checked; render(); });
}

/* The correlation matrix. It is nearly empty, and that IS the content: if the six
   tests corroborated each other a high score would describe a syndrome. They do not,
   so it describes a company that is mildly unusual in several unrelated ways. */
function buildMatrix() {
  const c = window.SHORTFALL.correlations;
  const host = document.getElementById("matrix");
  if (!c || !c.pairs.length) return;

  const rho = {};
  c.pairs.forEach((p) => { rho[p.a + "|" + p.b] = p; rho[p.b + "|" + p.a] = p; });

  const table = el("table", { class: "matrix" }, host);
  const head = el("tr", {}, el("thead", {}, table));
  el("th", { text: "" }, head);
  c.order.forEach((k) => el("th", { text: c.short[k] }, head));

  const body = el("tbody", {}, table);
  c.order.forEach((a) => {
    const tr = el("tr", {}, body);
    el("th", { text: c.short[a], class: "rowhead" }, tr);
    c.order.forEach((b) => {
      const td = el("td", {}, tr);
      if (a === b) { td.className = "self"; td.textContent = ""; return; }
      const p = rho[a + "|" + b];
      if (!p) { td.textContent = ""; return; }
      td.textContent = p.rho.toFixed(2);
      td.title = `${c.short[a]} vs ${c.short[b]}: Spearman ${p.rho}, n=${p.n}`;
      // Opacity carries magnitude; hue carries sign. Nothing here gets past ~0.17,
      // so the whole grid reading as blank is the honest rendering.
      const mag = Math.min(Math.abs(p.rho) / 0.35, 1);
      td.style.background = p.rho >= 0
        ? `color-mix(in srgb, var(--accent) ${(mag * 70).toFixed(0)}%, transparent)`
        : `color-mix(in srgb, var(--warn) ${(mag * 70).toFixed(0)}%, transparent)`;
    });
  });

  const s = c.strongest;
  document.getElementById("agreeNote").textContent =
    `Rank correlation between every pair. Mean strength ${c.mean_abs}; the strongest of `
    + `${c.pairs.length} pairs is ${c.short[s.a]} against ${c.short[s.b]} at ${s.rho}. `
    + `Near enough independent - so a high score is a company that is mildly unusual in `
    + `several unrelated ways, not one failing a single underlying test.`;
}

function buildExplain() {
  const body = document.getElementById("explainBody");
  body.textContent = "";
  (window.SHORTFALL.explanations || []).forEach((e) => {
    const tr = el("tr", {}, body);
    el("td", { text: e.flag }, tr);
    el("td", { text: e.measures }, tr);
    el("td", { text: e.deterioration }, tr);
    el("td", { text: e.innocent }, tr);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  buildSliders();
  buildFilters();
  buildMatrix();
  buildExplain();
  render();
  const btn = document.getElementById("themeBtn");
  const lbl = document.getElementById("themeLbl");
  lbl.textContent = document.documentElement.getAttribute("data-theme") === "dark"
    ? "Dark" : "Light";
  btn.addEventListener("click", () => {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
    localStorage.setItem("theme", dark ? "light" : "dark");
    lbl.textContent = dark ? "Light" : "Dark";
    render();
  });
  window.addEventListener("resize", () => renderScatter(scored()));
});
