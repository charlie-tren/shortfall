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
  const shown = Math.min(rows.length, 100);
  note.textContent = `${rows.length} companies ranked. Showing the top ${shown}. `
    + `Higher means more flags firing more strongly, not a worse company.`;
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
      el("dd", {
        class: on ? "on" : "na",
        text: on ? f.rank.toFixed(0) : "not applicable",
        title: f && !f.applicable ? f.reason : "",
      }, pair);
    });
    el("p", { class: "applicable",
              text: `${row.applicable} of 6 flags applicable` }, card);
  });
}

function renderScatter(rows) {
  const svg = document.getElementById("scatterSvg");
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const W = svg.clientWidth || 900, H = 300, PAD = 34;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

  svgEl("line", { x1: PAD, y1: H - PAD, x2: W - PAD, y2: H - PAD, class: "axis" }, svg);
  [0, 50, 100].forEach((v) => {
    const y = H - PAD - (v / 100) * (H - 2 * PAD);
    svgEl("line", { x1: PAD, y1: y, x2: W - PAD, y2: y, class: "axis", opacity: 0.35 }, svg);
    const t = svgEl("text", { x: 4, y: y + 3, class: "axislabel" }, svg);
    t.textContent = String(v);
  });

  rows.forEach(({ row, score, base }, i) => {
    const x = PAD + (i / Math.max(rows.length - 1, 1)) * (W - 2 * PAD);
    const y = H - PAD - (score / 100) * (H - 2 * PAD);
    const yb = H - PAD - (base / 100) * (H - 2 * PAD);
    if (Math.abs(y - yb) > 1) {
      svgEl("line", { x1: x, y1: yb, x2: x, y2: y, class: "shift" }, svg);
    }
    const flagged = row.events && row.events.length;
    const dot = svgEl("circle", {
      cx: x, cy: y, r: 3, class: flagged ? "dot flagged" : "dot",
    }, svg);
    const title = svgEl("title", {}, dot);
    title.textContent = `${row.name} (${row.ticker}) - ${score.toFixed(0)}`;
  });
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
