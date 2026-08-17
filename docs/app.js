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

/* The MAGNITUDE, not just the rank. A 99th-percentile accrual could be 4% of assets
   or 40%; those are different theses and a rank alone cannot tell them apart. */
const FORMAT = {
  accruals:         (v) => (v * 100).toFixed(1) + "% of assets",
  working_capital:  (v) => (v >= 0 ? "+" : "") + (v * 100).toFixed(0) + "% vs sales",
  share_count_roic: (v) => (v * 100).toFixed(1) + " dilution x fall",
  goodwill:         (v) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "pp of assets",
  tax_rate:         (v) => (v * 100).toFixed(1) + "pp swing",
  stock_comp:       (v) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "pp of revenue",
};
/* Defaults are NOT equal - they mirror DEFAULT_WEIGHTS in score.py, which weights
   each test by how directly it observes an accounting problem. Keep the two in step. */
const DEFAULT_WEIGHTS = {
  accruals: 1.5, working_capital: 1.25, goodwill: 1.0,
  share_count_roic: 1.0, tax_rate: 0.75, stock_comp: 0.75,
};

const state = {
  weights: {}, market: "all", sector: "all", size: "all",
  minScore: 0, minHot: "all", price: "all", eventsOnly: false, tail: null, page: 0,
  xvar: "assets",
  yvar: "short_interest",
  perTest: {},
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
    for (const [k, min] of Object.entries(state.perTest)) {
      if (!min) continue;
      const f = r.flags[k];
      // A test that does not apply cannot clear a minimum on it.
      if (!f || !f.applicable || f.rank == null || f.rank < min) return false;
    }
    if (state.price !== "all") {
      const v = r.ret_1y;
      if (v == null) return false;
      if (state.price === "up" && v < 0.2) return false;
      if (state.price === "down" && v > -0.2) return false;
      if (state.price === "flat" && (v <= -0.2 || v >= 0.2)) return false;
    }
    if (state.tail) {
      const f = r.flags[state.tail];
      if (!f || !f.applicable || f.rank == null || f.rank < 90) return false;
    }
    return true;
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
  renderQuadrant(rows);
  renderPerf(rows);
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

/* X-axis variables the reader can put short interest against. Each carries its own
   accessor and formatter; `log` marks the ones that need a log scale to be readable. */
const XVARS = {
  assets:           { label: "Total assets", log: true,  get: (r) => r.assets,
                      fmt: (v) => money(v) },
  turnover:         { label: "Revenue / assets", get: (r) => (r.revenue && r.assets) ? r.revenue / r.assets : null,
                      fmt: (v) => v.toFixed(2) },
  score:            { label: "Score", get: (r) => r.composite, fmt: (v) => v.toFixed(0) },
  ret:              { label: "12-month return", get: (r) => r.ret_1y,
                      fmt: (v) => (v * 100).toFixed(0) + "%" },
  accruals:         { label: "Accruals", get: (r) => flagVal(r, "accruals"),
                      fmt: (v) => (v * 100).toFixed(1) + "%" },
  working_capital:  { label: "Receivables & inventory", get: (r) => flagVal(r, "working_capital"),
                      fmt: (v) => (v * 100).toFixed(0) + "%" },
  goodwill:         { label: "Goodwill share", get: (r) => flagVal(r, "goodwill"),
                      fmt: (v) => (v * 100).toFixed(1) + "pp" },
  tax_rate:         { label: "Tax rate swing", get: (r) => flagVal(r, "tax_rate"),
                      fmt: (v) => (v * 100).toFixed(1) + "pp" },
  stock_comp:       { label: "Stock compensation", get: (r) => flagVal(r, "stock_comp"),
                      fmt: (v) => (v * 100).toFixed(1) + "pp" },

  /* LEVELS. Everything above this line is a CHANGE, and changes barely correlate
     with anything - measured mean |rho| 0.075 against 0.308 for level-vs-level
     pairs, because differencing removes the component two ratios share. These are
     the same quantities before the difference is taken. */
  l_receivables:    { label: "Receivables / revenue", group: "level",
                      get: (r) => lvl(r, "receivables_to_revenue"), fmt: (v) => v.toFixed(2) },
  l_inventory:      { label: "Inventory / revenue", group: "level",
                      get: (r) => lvl(r, "inventory_to_revenue"), fmt: (v) => v.toFixed(2) },
  l_goodwill:       { label: "Goodwill / assets", group: "level",
                      get: (r) => lvl(r, "goodwill_to_assets"), fmt: (v) => (v * 100).toFixed(0) + "%" },
  l_stockcomp:      { label: "Stock comp / revenue", group: "level",
                      get: (r) => lvl(r, "stock_comp_to_revenue"), fmt: (v) => (v * 100).toFixed(1) + "%" },
  l_etr:            { label: "Effective tax rate", group: "level",
                      get: (r) => lvl(r, "effective_tax_rate"), fmt: (v) => (v * 100).toFixed(0) + "%" },
  l_roic:           { label: "Return on invested capital", group: "level",
                      get: (r) => lvl(r, "roic"), fmt: (v) => (v * 100).toFixed(0) + "%" },
  l_debt:           { label: "Debt / assets", group: "level",
                      get: (r) => lvl(r, "debt_to_assets"), fmt: (v) => (v * 100).toFixed(0) + "%" },
};

function lvl(r, k) {
  return r.levels ? r.levels[k] : null;
}

function flagVal(r, k) {
  const f = r.flags[k];
  return f && f.applicable && f.value != null ? f.value : null;
}

function spearman(pairs) {
  if (pairs.length < 20) return null;
  const rank = (vals) => {
    const idx = vals.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
    const out = new Array(vals.length);
    idx.forEach(([, i], r) => { out[i] = r; });
    return out;
  };
  const x = rank(pairs.map((p) => p[0])), y = rank(pairs.map((p) => p[1]));
  const mx = x.reduce((a, b) => a + b, 0) / x.length;
  const my = y.reduce((a, b) => a + b, 0) / y.length;
  let n = 0, dx = 0, dy = 0;
  x.forEach((v, i) => { n += (v - mx) * (y[i] - my); dx += (v - mx) ** 2; dy += (y[i] - my) ** 2; });
  return dx && dy ? n / Math.sqrt(dx * dy) : null;
}

/* Generic scatter. Both panels use it so they cannot drift apart in style. */
function scatter(svg, data, opts) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const W = 1000, H = 480, L = 66, R = 26, T = 22, B = 62;
  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  if (data.length < 20) return null;

  const clip = (vals) => {
    const s = [...vals].sort((a, b) => a - b);
    return [s[Math.floor(0.02 * (s.length - 1))], s[Math.floor(0.98 * (s.length - 1))]];
  };
  const tx = opts.logX ? (v) => Math.log10(Math.max(v, 1)) : (v) => v;
  const ty = opts.logY ? (v) => Math.log10(Math.max(v, 1))
           : opts.sqrtY ? (v) => Math.sqrt(Math.max(v, 0)) : (v) => v;
  const [xlo, xhi] = clip(data.map((d) => tx(d.x)));
  const [ylo, yhi] = clip(data.map((d) => ty(d.y)));
  const px = (v) => L + Math.max(0, Math.min(1, (tx(v) - xlo) / ((xhi - xlo) || 1))) * (W - L - R);
  const py = (v) => H - B - Math.max(0, Math.min(1, (ty(v) - ylo) / ((yhi - ylo) || 1))) * (H - T - B);

  for (let i = 0; i <= 4; i++) {
    const raw = ylo + (i / 4) * (yhi - ylo);
    const v = opts.logY ? Math.pow(10, raw) : opts.sqrtY ? raw * raw : raw;
    const y = H - B - (i / 4) * (H - T - B);
    svgEl("line", { x1: L, y1: y, x2: W - R, y2: y, class: "grid" }, svg);
    const t = svgEl("text", { x: L - 10, y: y + 5, class: "axislabel", "text-anchor": "end" }, svg);
    t.textContent = opts.fmtY(v);
  }
  for (let i = 0; i <= 4; i++) {
    const raw = xlo + (i / 4) * (xhi - xlo);
    const v = opts.logX ? Math.pow(10, raw) : raw;
    const t = svgEl("text", { x: px(v), y: H - 34, class: "axislabel", "text-anchor": "middle" }, svg);
    t.textContent = opts.fmtX(v);
  }
  const xt = svgEl("text", { x: (L + W - R) / 2, y: H - 8, class: "axistitle", "text-anchor": "middle" }, svg);
  xt.textContent = opts.xLabel;
  const yt = svgEl("text", { x: -(T + (H - B - T) / 2), y: 16, class: "axistitle",
                             "text-anchor": "middle", transform: "rotate(-90)" }, svg);
  yt.textContent = opts.yLabel;

  const xs = data.map((d) => tx(d.x)), ys = data.map((d) => ty(d.y));
  const mx = xs.reduce((a, b) => a + b, 0) / xs.length;
  const my = ys.reduce((a, b) => a + b, 0) / ys.length;
  let num = 0, den = 0;
  xs.forEach((v, i) => { num += (v - mx) * (ys[i] - my); den += (v - mx) ** 2; });
  const rho = spearman(data.map((d) => [tx(d.x), ty(d.y)]));
  /* The fit is always drawn where asked for, but a WEAK one is drawn faintly and the
     caption still prints rho. A line through rho 0.01 looks like a finding, so the
     styling has to carry the strength the geometry cannot. */
  if (den && rho != null && opts.alwaysFit !== false) {
    const sl = num / den;
    const at = (t_) => {
      const raw = my + sl * (t_ - mx);
      return opts.logY ? Math.pow(10, raw) : opts.sqrtY ? raw * raw : raw;
    };
    svgEl("line", { x1: px(opts.logX ? Math.pow(10, xlo) : xlo), y1: py(at(xlo)),
                    x2: px(opts.logX ? Math.pow(10, xhi) : xhi), y2: py(at(xhi)),
                    class: "trend" + (Math.abs(rho) < 0.15 ? " weak" : "") }, svg);
  }

  /* BINNED MEDIANS on top of the cloud. A scatter of 500 points hides a real
     relationship in overplotting - the eye cannot average. Splitting x into deciles
     and drawing the median y of each makes the shape visible without asserting
     anything: these are the data, summarised, not a model fitted to them. */
  if (opts.bins !== false && data.length >= 100) {
    const sorted = [...data].sort((p, q) => tx(p.x) - tx(q.x));
    const k = Math.max(1, Math.floor(sorted.length / 10));
    const med = [];
    for (let i = 0; i < 10; i++) {
      const chunk = i === 9 ? sorted.slice(9 * k) : sorted.slice(i * k, (i + 1) * k);
      if (chunk.length < 5) continue;
      const mid = (arr) => {
        const s = [...arr].sort((m, n) => m - n);
        return s[Math.floor(s.length / 2)];
      };
      med.push([mid(chunk.map((c) => c.x)), mid(chunk.map((c) => c.y))]);
    }
    if (med.length > 2) {
      const d = med.map(([mxv, myv], i) => `${i ? "L" : "M"}${px(mxv).toFixed(1)},${py(myv).toFixed(1)}`).join(" ");
      svgEl("path", { d, class: "binline" }, svg);
      med.forEach(([mxv, myv]) => svgEl("circle", { cx: px(mxv), cy: py(myv), r: 5,
                                                    class: "binpt" }, svg));
    }
  }

  data.forEach((d) => {
    const dot = svgEl("circle", { cx: px(d.x), cy: py(d.y), r: 3.4,
                                  class: "dot" + (d.row.composite >= 90 ? " hot" : "") }, svg);
    dot.addEventListener("mouseenter", (e) => showTip(d.row, d.row.composite, e.clientX, e.clientY));
    dot.addEventListener("mouseleave", hideTip);
  });
  return rho;
}

const YVARS = Object.assign({
  short_interest: { label: "Short interest", sqrt: true,
                    get: (r) => r.short_interest, fmt: (v) => (v * 100).toFixed(0) + "%" },
}, XVARS);

/* The two lines were unlabelled and they are different kinds of thing: one is the
   data summarised, the other is a model. Built from what actually RENDERED, so the
   key can never claim a fit that was suppressed. */
function chartKey(hostId, svg) {
  const host = document.getElementById(hostId);
  if (!host) return;
  host.textContent = "";
  if (svg.querySelector(".binline")) {
    const a = el("span", { class: "key" }, host);
    el("i", { class: "k-bin" }, a);
    el("span", { text: "median of each tenth of the companies" }, a);
  }
  const fit = svg.querySelector(".trend");
  if (fit) {
    const b = el("span", { class: "key" }, host);
    const wk = fit.getAttribute("class").indexOf("weak") >= 0;
    el("i", { class: "k-fit" + (wk ? " weak" : "") }, b);
    el("span", { text: wk ? "fitted line, too weak to rely on" : "fitted line" }, b);
  }
  const c = el("span", { class: "key" }, host);
  el("i", { class: "k-hot" }, c);
  el("span", { text: "scores 90 or above" }, c);
}

function renderQuadrant(rows) {
  const svg = document.getElementById("quadSvg");
  if (!svg) return;
  const vx = XVARS[state.xvar] || XVARS.assets;
  const vy = YVARS[state.yvar] || YVARS.short_interest;
  const data = rows.map(({ row }) => ({ row, x: vx.get(row), y: vy.get(row) }))
                   .filter((d) => d.x != null && d.y != null);
  const rho = scatter(svg, data, {
    logX: !!vx.log, logY: !!vy.log, sqrtY: !!vy.sqrt,
    xLabel: vx.label, yLabel: vy.label, fmtX: vx.fmt, fmtY: vy.fmt,
  });
  // n=500 gives a standard error on rho of 0.045, so anything under about 0.09 is
  // not distinguishable from zero and the page should not imply otherwise.
  const weak = rho != null && Math.abs(rho) < 0.09;
  document.getElementById("quadNote").textContent = data.length < 20
    ? "Not enough data for this pair."
    : data.length + " companies. Rank correlation "
      + (rho == null ? "n/a" : rho.toFixed(2))
      + (weak ? " - indistinguishable from zero at this sample size." : ".");
  chartKey("quadKey", svg);
}

function renderPerf(rows) {
  const svg = document.getElementById("perfSvg");
  if (!svg) return;
  const data = rows.map(({ row, score }) => ({ row, x: score, y: row.ret_1y }))
                   .filter((d) => d.x != null && d.y != null);
  const rho = scatter(svg, data, {
    logX: false, sqrtY: false, alwaysFit: false, bins: true,
    xLabel: "Score", yLabel: "12-month return",
    fmtX: (x) => x.toFixed(0), fmtY: (y) => (y * 100).toFixed(0) + "%",
  });
  const flat = rho != null && Math.abs(rho) < 0.15;
  document.getElementById("perfNote").textContent = data.length < 20
    ? "Not enough price history for this selection."
    : data.length + " companies. Rank correlation " + (rho == null ? "n/a" : rho.toFixed(2))
      + (flat ? " - no fitted line drawn, there is nothing to fit." : ".");
  chartKey("perfKey", svg);
}

const PAGE_SIZE = 20;

function renderCards(rows) {
  const host = document.getElementById("cards");
  host.textContent = "";
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  if (state.page >= pages) state.page = 0;
  rows.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE).forEach(({ row, score, base }) => {
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
      if (on) {
        dd.style.setProperty("--w", f.rank.toFixed(0) + "%");
        if (f.value != null && FORMAT[k]) {
          el("span", { class: "mag", text: FORMAT[k](f.value) }, pair);
        }
      }
    });
    el("p", { class: "applicable",
              text: `${row.applicable} of 6 tests apply. Ranked against `
                    + `${row.ranked_against === "universe" ? "the whole market" : row.sector}.` }, card);
  });
  renderPager(rows.length, pages);
}

function renderPager(total, pages) {
  const from = total ? state.page * PAGE_SIZE + 1 : 0;
  const to = Math.min((state.page + 1) * PAGE_SIZE, total);
  const label = total
    ? `${from}-${to} of ${total}`
    : "nothing matches these filters";
  ["", "Top"].forEach((sfx) => {
    const info = document.getElementById("pageInfo" + sfx);
    if (!info) return;
    info.textContent = label;
    document.getElementById("prevPage" + sfx).disabled = state.page === 0;
    document.getElementById("nextPage" + sfx).disabled = state.page >= pages - 1;
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
      state.page = 0;
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
    text: `score ${score.toFixed(0)} · ${money(row.assets)} assets · ${row.applicable} of 6 tests`,
  }, tip);
  if (row.ret_1y != null || row.short_interest != null) {
    const bits = [];
    if (row.ret_1y != null) bits.push(`${(row.ret_1y * 100).toFixed(0)}% over 12m`);
    if (row.short_interest != null) bits.push(`${(row.short_interest * 100).toFixed(1)}% short`);
    el("span", { class: "t-line", text: bits.join(" · ") }, tip);
  }
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
  sel.addEventListener("change", () => { onChange(sel.value); state.page = 0; render(); });
  return sel;
}

/* The per-test filters sit as COLUMN HEADINGS over the card list, in the same six
   column grid the cards use, so each control is directly above the number it
   filters. They were in the generic filter row, which meant reading a card and
   then hunting back up the page for the matching slider. */
function buildTestHeader() {
  const host = document.getElementById("testHead");
  if (!host) return;
  host.textContent = "";
  FLAGS.forEach(([k, label]) => {
    const col = el("div", { class: "thcol" }, host);
    el("span", { class: "thname", text: label }, col);
    const row = el("div", { class: "throw" }, col);
    const inp = el("input", { type: "range", min: "0", max: "95", step: "5",
                              value: String(state.perTest[k] || 0),
                              "aria-label": `Minimum rank for ${label}` }, row);
    const out = el("output", { text: state.perTest[k] ? "≥ " + state.perTest[k] : "any" }, row);
    inp.addEventListener("input", () => {
      state.perTest[k] = parseFloat(inp.value);
      out.textContent = inp.value === "0" ? "any" : "≥ " + inp.value;
      col.classList.toggle("on", inp.value !== "0");
      state.page = 0;
      render();
    });
    col.classList.toggle("on", (state.perTest[k] || 0) !== 0);
  });
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
  sSel.addEventListener("change", () => { state.size = sSel.value; state.page = 0; render(); });

  const minWrap = el("label", { text: "Min score" }, host);
  const min = el("input", { type: "range", min: "0", max: "95", step: "5", value: "0",
                            class: "minscore" }, minWrap);
  const out = el("output", { text: "0" }, minWrap);
  min.addEventListener("input", () => {
    state.minScore = parseFloat(min.value);
    out.textContent = min.value;
    state.page = 0;
    render();
  });

  const pWrap = el("label", { text: "12m price" }, host);
  const pSel = el("select", {}, pWrap);
  [["all", "Any"], ["up", "Up 20%+"], ["flat", "Between -20% and +20%"],
   ["down", "Down 20%+"]].forEach(([v, t]) => el("option", { value: v, text: t }, pSel));
  pSel.addEventListener("change", () => { state.price = pSel.value; state.page = 0; render(); });

  const tWrap = el("label", { text: "Tests firing" }, host);
  const tSel = el("select", {}, tWrap);
  [["all", "Any"], ["1", "1 or more above 90"], ["2", "2 or more above 90"],
   ["3", "3 or more above 90"]].forEach(([v, t]) => el("option", { value: v, text: t }, tSel));
  tSel.addEventListener("change", () => { state.minHot = tSel.value; state.page = 0; render(); });

  const eLabel = el("label", { text: "" }, host);
  const cb = el("input", { type: "checkbox" }, eLabel);
  el("span", { text: "Disclosed a problem" }, eLabel);
  cb.addEventListener("change", () => { state.eventsOnly = cb.checked; state.page = 0; render(); });

  const clear = el("button", { type: "button", text: "Clear", class: "clearBtn" }, host);
  clear.addEventListener("click", () => {
    Object.assign(state, { market: "all", sector: "all", size: "all", minScore: 0,
                           minHot: "all", price: "all", eventsOnly: false, tail: null,
                           page: 0, perTest: {} });
    buildFilters();
    buildTestHeader();
    render();
  });
}

const SIZE_BANDS = {
  mega: (a) => a >= 100e9,
  large: (a) => a >= 10e9 && a < 100e9,
  mid: (a) => a >= 1e9 && a < 10e9,
  small: (a) => a < 1e9,
};

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

function goPage(delta, from) {
  state.page = Math.max(0, state.page + delta);
  render();
  // Paging from the bottom arrows jumps you back to the top of the list; paging
  // from the top arrows should leave you where you already are.
  if (from !== "Top") {
    document.getElementById("pagerTop").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  ["", "Top"].forEach((sfx) => {
    document.getElementById("prevPage" + sfx).addEventListener("click", () => goPage(-1, sfx));
    document.getElementById("nextPage" + sfx).addEventListener("click", () => goPage(1, sfx));
  });
  const fill = (sel, vars) => {
    const changes = el("optgroup", { label: "Change over time" }, sel);
    const lv = el("optgroup", { label: "Level, latest year" }, sel);
    Object.entries(vars).forEach(([k, v]) =>
      el("option", { value: k, text: v.label }, v.group === "level" ? lv : changes));
  };
  const xsel = document.getElementById("xvar");
  const ysel = document.getElementById("yvar");
  fill(xsel, XVARS); fill(ysel, YVARS);
  xsel.value = state.xvar; ysel.value = state.yvar;
  xsel.addEventListener("change", () => { state.xvar = xsel.value; render(); });
  ysel.addEventListener("change", () => { state.yvar = ysel.value; render(); });
  buildSliders();
  buildFilters();
  buildTestHeader();
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
