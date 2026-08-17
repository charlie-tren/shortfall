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
/* Defaults are NOT equal - they mirror DEFAULT_WEIGHTS in score.py, which weights
   each test by how directly it observes an accounting problem. Keep the two in step. */
const DEFAULT_WEIGHTS = {
  accruals: 1.5, working_capital: 1.25, goodwill: 1.0,
  share_count_roic: 1.0, tax_rate: 0.75, stock_comp: 0.75,
};

const state = {
  weights: {}, market: "all", sector: "all", size: "all",
  minScore: 0, minHot: "all", eventsOnly: false, tail: null,
};
FLAGS.forEach(([k]) => (state.weights[k] = DEFAULT_WEIGHTS[k]));

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

/* SEVERITY: the weighted mean of a company's WORST TWO applicable tests.
   Must mirror composite() in score.py exactly - the page re-scores client side the
   moment a slider moves, so any divergence means the ranking silently changes as
   soon as the reader touches anything. This function was a plain mean of all six
   for a while after score.py had already moved to severity, which meant the live
   ranking was never the one the build computed. */
const SEVERITY_TOP_N = 2;

function composite(row, weights) {
  const scored = [];
  FLAGS.forEach(([k]) => {
    const f = row.flags[k];
    if (!f || !f.applicable || f.rank == null) return;
    const w = weights[k];
    if (!w) return;
    scored.push([f.rank * w, w]);
  });
  if (!scored.length) return null;
  scored.sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, SEVERITY_TOP_N);
  const den = top.reduce((s, x) => s + x[1], 0);
  return den ? top.reduce((s, x) => s + x[0], 0) / den : null;
}

function defaultWeights() {
  const w = {};
  FLAGS.forEach(([k]) => (w[k] = DEFAULT_WEIGHTS[k]));
  return w;
}

function hotCount(r) {
  return FLAGS.filter(([k]) => {
    const f = r.flags[k];
    return f && f.applicable && f.rank != null && f.rank >= 90;
  }).length;
}

function visible() {
  return window.SHORTFALL.names.filter((r) => {
    if (state.market !== "all" && r.market !== state.market) return false;
    if (state.sector !== "all" && r.sector !== state.sector) return false;
    if (state.eventsOnly && !(r.events && r.events.length)) return false;
    if (state.size !== "all") {
      if (!r.assets || !SIZE_BANDS[state.size](r.assets)) return false;
    }
    if (state.minHot !== "all" && hotCount(r) < parseInt(state.minHot, 10)) return false;
    if (state.tail) {
      const f = r.flags[state.tail];
      if (!f || !f.applicable || f.rank == null || f.rank < 90) return false;
    }
    return true;
  });
}

/* The disclosed list is deliberately NOT re-ranked by the sliders. These are facts
   the company reported, not percentiles, so a reader's weighting has nothing to say
   about them. Built once. */
function buildDisclosed() {
  const host = document.getElementById("disclosed");
  host.textContent = "";
  (window.SHORTFALL.disclosed || []).forEach((row) => {
    const item = el("a", { class: "disc", href: "#" + row.ticker }, host);
    el("span", { class: "d-name", text: row.name }, item);
    el("span", { class: "d-ticker", text: row.ticker }, item);
    const kinds = [...new Set(row.events.map((e) => e.label))];
    const tags = el("span", { class: "d-tags" }, item);
    kinds.forEach((k) => el("span", { class: "badge", text: k }, tags));
    el("span", { class: "d-score", text: row.composite.toFixed(0) }, item);
  });
}

function scored() {
  const rows = visible().map((r) => ({
    row: r,
    score: composite(r, state.weights),
    base: composite(r, defaultWeights()),
  })).filter((x) => x.score != null && x.score >= state.minScore);
  rows.sort((a, b) => b.score - a.score);
  return rows;
}

function render() {
  const rows = scored();
  renderOverview(rows);
  renderQuadrant(rows);
  renderStrips(rows);
  renderCards(rows);
}

/* Score against short interest.

   THE POINT IS THAT THESE DO NOT CORRELATE (rho +0.036, measured). If the screen
   agreed with short sellers it would only be rediscovering crowded trades. Because
   the two are independent, points spread over the whole plane, and the top-left
   corner - flagged by the screen, almost nobody short it - is the only part of this
   page that is not already in the price.

   Absent short interest is left OUT, never drawn as zero: "nobody is short it" and
   "we do not know" are different claims. */
const CROWDED = 0.09;

function renderQuadrant(rows) {
  const svg = document.getElementById("quadSvg");
  if (!svg) return;
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  const pts = rows.filter(({ row }) => row.short_interest != null);
  const note = document.getElementById("quadNote");
  if (pts.length < 10) {
    note.textContent = "Short interest is not available for this selection.";
    return;
  }

  const W = 1000, H = 420, L = 46, R = 18, T = 16, B = 42;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const maxSI = Math.max(0.2, ...pts.map((p) => p.row.short_interest));
  const px = (v) => L + Math.min(v / maxSI, 1) * (W - L - R);
  const py = (v) => H - B - (v / 100) * (H - T - B);

  const midScore = 90;
  svgEl("rect", { x: L, y: T, width: px(CROWDED) - L, height: py(midScore) - T,
                  class: "quadhi" }, svg);

  [0, 25, 50, 75, 100].forEach((v) => {
    svgEl("line", { x1: L, y1: py(v), x2: W - R, y2: py(v), class: "grid" }, svg);
    const t = svgEl("text", { x: L - 8, y: py(v) + 4, class: "axislabel",
                              "text-anchor": "end" }, svg);
    t.textContent = String(v);
  });
  for (let s = 0; s <= maxSI + 0.001; s += 0.05) {
    const t = svgEl("text", { x: px(s), y: H - 14, class: "axislabel",
                              "text-anchor": "middle" }, svg);
    t.textContent = (s * 100).toFixed(0) + "%";
  }
  svgEl("line", { x1: px(CROWDED), y1: T, x2: px(CROWDED), y2: H - B,
                  class: "divider" }, svg);

  // Below the band, not inside it - inside, the label sat on top of the very dots
  // it describes.
  const lab = svgEl("text", { x: L + 6, y: py(midScore) + 15, class: "quadlabel" }, svg);
  lab.textContent = "↑ flagged, barely shorted";
  const lab2 = svgEl("text", { x: W - R - 6, y: py(midScore) + 15, class: "quadlabel",
                               "text-anchor": "end" }, svg);
  lab2.textContent = "flagged and already crowded →";
  const xt = svgEl("text", { x: (L + W - R) / 2, y: H - 2, class: "axistitle",
                             "text-anchor": "middle" }, svg);
  xt.textContent = "short interest, % of float";

  pts.forEach(({ row, score }) => {
    const x = px(row.short_interest), y = py(score);
    const interesting = score >= midScore && row.short_interest < CROWDED;
    const dot = svgEl("circle", {
      cx: x, cy: y, r: interesting ? 4.6 : 3.2,
      class: "dot" + (interesting ? " hot" : "") + (row.events && row.events.length ? " ev" : ""),
    }, svg);
    dot.addEventListener("mouseenter", (e) => showTip(row, score, e.clientX, e.clientY));
    dot.addEventListener("mouseleave", hideTip);
  });

  const hot = pts.filter(({ row, score }) => score >= midScore && row.short_interest < CROWDED);
  note.textContent =
    `${pts.length} US companies with a short-interest figure. The two are unrelated `
    + `(rank correlation +0.04), which is what makes the shaded corner worth `
    + `something: ${hot.length} companies score ${midScore} or above with under `
    + `${(CROWDED * 100).toFixed(0)}% of float short.`;
}

/* Sector against test: which corners of the market are firing which test.
   Cells count companies past a single MARKET-WIDE cut - see the note inside, a
   sector-relative cut would make every cell identical. Click a cell to filter. */
function renderOverview(rows) {
  const host = document.getElementById("overview");
  host.textContent = "";
  const sectors = Array.from(new Set(rows.map((r) => r.row.sector).filter(Boolean))).sort();
  if (!sectors.length) return;

  // One market-wide 90th-percentile cut per test, computed across everything shown.
  const cutoffs = {};
  FLAGS.forEach(([key]) => {
    const vals = rows.map(({ row }) => {
      const f = row.flags[key];
      return f && f.applicable ? f.value : null;
    }).filter((v) => v != null).sort((a, b) => a - b);
    cutoffs[key] = vals.length ? vals[Math.floor(0.9 * (vals.length - 1))] : Infinity;
  });

  const table = el("table", { class: "heat" }, host);
  const head = el("tr", {}, el("thead", {}, table));
  el("th", { text: "" }, head);
  FLAGS.forEach(([, label]) => el("th", { text: label }, head));
  el("th", { class: "n", text: "n" }, head);

  const body = el("tbody", {}, table);
  sectors.forEach((sec) => {
    const members = rows.filter((r) => r.row.sector === sec);
    const tr = el("tr", {}, body);
    el("th", { class: "rowhead", text: sec }, tr);
    FLAGS.forEach(([key]) => {
      const applies = members.filter(({ row }) => {
        const f = row.flags[key];
        return f && f.applicable && f.value != null;
      });
      const td = el("td", {}, tr);
      if (!applies.length) {
        td.className = "self";
        td.title = `${sec}: test does not apply`;
        return;
      }
      /* Counted against the MARKET-WIDE threshold, not the sector's own.
         Scoring is sector-relative, which is right - but a heatmap of sector-relative
         deciles is uniform by construction: every sector has exactly 10% of itself in
         its own worst 10%, so the cells only ever track sector size. Against one
         market-wide cut the differences are real, and this is where you see that
         stock compensation is concentrated in technology. */
      const hot = applies.filter(({ row }) => row.flags[key].value >= cutoffs[key]).length;
      const share = hot / applies.length;
      td.textContent = hot ? String(hot) : "";
      td.title = `${sec} - ${hot} of ${applies.length} past the market-wide cut`;
      td.style.background =
        `color-mix(in srgb, var(--warn) ${(Math.min(share / 0.3, 1) * 78).toFixed(0)}%, transparent)`;
      td.addEventListener("click", () => {
        state.sector = state.sector === sec ? "all" : sec;
        state.tail = state.tail === key ? null : key;
        buildFilters();
        render();
      });
    });
    el("td", { class: "n", text: String(members.length) }, tr);
  });

  document.getElementById("overviewCount").textContent =
    `${rows.length} companies`;
  document.getElementById("overviewNote").textContent =
    "Companies past the market-wide worst-10% cut on each test. Scores elsewhere "
    + "are ranked within sector, so a REIT is compared with REITs. Click a cell to filter.";
}

function renderCards(rows) {
  const host = document.getElementById("cards");
  host.textContent = "";
  rows.slice(0, 100).forEach(({ row, score, base }) => {
    const card = el("article", { class: "card" }, host);
    const head = el("header", {}, card);
    el("h3", { text: row.name }, head);
    el("span", { class: "ticker", text: row.ticker }, head);
    const sc = el("span", { class: "score" }, head);
    el("span", { class: "score-n", text: score.toFixed(0) }, sc);
    el("span", { class: "score-of", text: "/100" }, sc);
    if (Math.abs(score - base) >= 0.5) {
      el("span", { class: "base", text: `default: ${base.toFixed(0)}` }, head);
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
              text: `${row.applicable} of 6 tests apply. Ranked against `
                    + `${row.ranked_against === "universe" ? "the whole market" : row.sector}.` }, card);
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

/* One strip per test: every company as a tick along the 0-100 axis, with the top
   decile picked out. Replaces a score-against-size scatter that had no relationship
   in it and so drew a formless blob.

   This is the view that serves the actual question. A short candidate is a company
   sitting in the far tail of one or two tests, and a strip shows exactly who is out
   there and how far from the pack. Click a strip to keep only its tail. */
function renderStrips(rows) {
  const host = document.getElementById("strips");
  host.textContent = "";
  const W = 1000, H = 34, L = 4, R = 4;
  const px = (v) => L + (v / 100) * (W - L - R);

  FLAGS.forEach(([key, label]) => {
    const present = rows.filter(({ row }) => {
      const f = row.flags[key];
      return f && f.applicable && f.rank != null && f.value != null;
    });
    if (!present.length) return;
    const strip = el("div", { class: "strip" + (state.tail === key ? " active" : "") }, host);
    const head = el("div", { class: "strip-head" }, strip);
    el("span", { class: "strip-name", text: label }, head);
    el("span", { class: "strip-n", text: `${present.length} companies` }, head);

    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "stripSvg");
    svg.setAttribute("preserveAspectRatio", "none");
    strip.appendChild(svg);

    /* RAW values, not percentile ranks. Ranks are uniform by construction, so a
       strip of them is an evenly spaced comb with exactly 10% inside any 10% band -
       it can only ever draw one shape, which is no information at all. The raw
       values are genuinely skewed, so the clump and the outliers are real.

       Clipped to the 2nd-98th percentile so a single extreme does not squash the
       rest against the axis; anything beyond is pinned to the edge. */
    const vals = present.map(({ row }) => row.flags[key].value).sort((a, b) => a - b);
    const at = (q) => vals[Math.min(vals.length - 1, Math.max(0, Math.floor(q * (vals.length - 1))))];
    const lo = at(0.02), hi = at(0.98);
    const span = (hi - lo) || 1;
    const vx = (v) => L + Math.max(0, Math.min(1, (v - lo) / span)) * (W - L - R);
    const cut = at(0.90);

    svgEl("line", { x1: L, y1: H / 2, x2: W - R, y2: H / 2, class: "grid" }, svg);
    svgEl("rect", { x: vx(cut), y: 2, width: (W - R) - vx(cut), height: H - 4,
                    class: "tailband" }, svg);

    present.forEach(({ row }) => {
      const f = row.flags[key];
      const x = vx(f.value);
      const hot = f.rank >= 90;
      const ev = row.events && row.events.length;
      const tick = svgEl("line", {
        x1: x, y1: hot ? 4 : 9, x2: x, y2: hot ? H - 4 : H - 9,
        class: "tick" + (hot ? " hot" : "") + (ev ? " ev" : ""),
      }, svg);
      tick.addEventListener("mouseenter", (e) => showTip(row, row.composite, e.clientX, e.clientY, true));
      tick.addEventListener("mouseleave", hideTip);
    });

    strip.addEventListener("click", () => {
      state.tail = state.tail === key ? null : key;
      render();
    });
  });

  const n = rows.length;
  document.getElementById("stripNote").textContent =
    `Each mark is one company, placed by how extreme it is on that test. `
    + `The shaded band is the worst 10%. Click a test to keep only its tail`
    + (state.tail ? ` - showing ${FLAGS.find((f) => f[0] === state.tail)[1]}, ${n} companies.` : `.`);
}

function showTip(row, score, x, y, viewport) {
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

  const sx = x, sy = y;
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
      type: "range", min: "0", max: "3", step: "0.05",
      value: String(DEFAULT_WEIGHTS[k]),
      "aria-label": `Weight for ${label}`,
    }, wrap);
    const out = el("output", { text: DEFAULT_WEIGHTS[k].toFixed(2) }, wrap);
    input.addEventListener("input", () => {
      state.weights[k] = parseFloat(input.value);
      out.textContent = parseFloat(input.value).toFixed(2);
      render();
    });
  });
  document.getElementById("resetWeights").addEventListener("click", () => {
    state.weights = defaultWeights();
    host.querySelectorAll("input").forEach((i, idx) => {
      i.value = String(DEFAULT_WEIGHTS[FLAGS[idx][0]]);
    });
    host.querySelectorAll("output").forEach((o, idx) => {
      o.textContent = DEFAULT_WEIGHTS[FLAGS[idx][0]].toFixed(2);
    });
    render();
  });
}

function dropdown(host, label, values, onChange, allLabel) {
  const wrap = el("label", { text: label }, host);
  const sel = el("select", {}, wrap);
  el("option", { value: "all", text: allLabel }, sel);
  values.forEach((v) => el("option", { value: String(v), text: String(v) }, sel));
  sel.addEventListener("change", () => { onChange(sel.value); render(); });
  return sel;
}

function buildFilters() {
  const host = document.getElementById("filters");
  host.textContent = "";
  const all = window.SHORTFALL.names;
  const uniq = (fn) => Array.from(new Set(all.map(fn).filter(Boolean))).sort();

  dropdown(host, "Market", uniq((r) => r.market), (v) => (state.market = v), "All markets");
  dropdown(host, "Sector", uniq((r) => r.sector), (v) => (state.sector = v), "All sectors");

  const sizes = [["all", "Any size"], ["mega", "Over $100bn"], ["large", "$10bn - $100bn"],
                 ["mid", "$1bn - $10bn"], ["small", "Under $1bn"]];
  const sWrap = el("label", { text: "Size" }, host);
  const sSel = el("select", {}, sWrap);
  sizes.forEach(([v, t]) => el("option", { value: v, text: t }, sSel));
  sSel.addEventListener("change", () => { state.size = sSel.value; render(); });

  const minWrap = el("label", { text: "Min score" }, host);
  const min = el("input", { type: "range", min: "0", max: "95", step: "5", value: "0",
                            class: "minscore" }, minWrap);
  const out = el("output", { text: "0" }, minWrap);
  min.addEventListener("input", () => {
    state.minScore = parseFloat(min.value);
    out.textContent = min.value;
    render();
  });

  const tWrap = el("label", { text: "Tests firing" }, host);
  const tSel = el("select", {}, tWrap);
  [["all", "Any"], ["1", "1 or more above 90"], ["2", "2 or more above 90"],
   ["3", "3 or more above 90"]].forEach(([v, t]) => el("option", { value: v, text: t }, tSel));
  tSel.addEventListener("change", () => { state.minHot = tSel.value; render(); });

  const eLabel = el("label", { text: "" }, host);
  const cb = el("input", { type: "checkbox" }, eLabel);
  el("span", { text: "Disclosed a problem" }, eLabel);
  cb.addEventListener("change", () => { state.eventsOnly = cb.checked; render(); });

  const clear = el("button", { type: "button", text: "Clear", class: "clearBtn" }, host);
  clear.addEventListener("click", () => {
    Object.assign(state, { market: "all", sector: "all", size: "all", minScore: 0,
                           minHot: "all", eventsOnly: false, tail: null });
    buildFilters();
    render();
  });
}

const SIZE_BANDS = {
  mega: (a) => a >= 100e9,
  large: (a) => a >= 10e9 && a < 100e9,
  mid: (a) => a >= 1e9 && a < 10e9,
  small: (a) => a < 1e9,
};

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
  buildDisclosed();
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
  window.addEventListener("resize", () => renderStrips(scored()));
});
