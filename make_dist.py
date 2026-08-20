"""Six NEW ways to show the six distributions. Throwaway.

Box plot, histogram, sorted curve and table+strip were shown on 18/08 and passed
over, so they are not repeated here.
"""
import json, math, html, statistics

P = json.load(open("docs/data.json"))
rows = P["names"]
FLAGS = [("accruals", "Accruals vs cash"), ("working_capital", "Receivables & inventory"),
         ("share_count_roic", "Share count vs returns"), ("goodwill", "Goodwill share"),
         ("tax_rate", "Tax rate"), ("stock_comp", "Stock compensation")]
A, WN, NA, RULE, INK = "#82a8ca", "#d29b76", "#5d6874", "#262f3a", "#e6eaef"
W = 470

def vals(k):
    return sorted(r["flags"][k]["value"] for r in rows
                  if r["flags"][k]["applicable"] and r["flags"][k]["value"] is not None)

def q(v, p): return v[min(len(v) - 1, max(0, int(p * (len(v) - 1))))]
def txt(x, y, s, size=10, fill=NA, anchor="start", extra=""):
    return (f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" font-size="{size}" '
            f'text-anchor="{anchor}" font-family="monospace"{extra}>{html.escape(str(s))}</text>')

def density(v, lo, hi, n=48):
    """Simple histogram smoothed once - enough for a shape."""
    b = [0] * n
    for t in v:
        b[min(n - 1, max(0, int((t - lo) / ((hi - lo) or 1) * n)))] += 1
    sm = [(b[max(0,i-1)] + 2*b[i] + b[min(n-1,i+1)]) / 4 for i in range(n)]
    m = max(sm) or 1
    return [x / m for x in sm]

opts = []

# 1 RIDGELINE
H = 42 * len(FLAGS) + 40
b = ""
for i, (k, lab) in enumerate(FLAGS):
    v = vals(k); base = 40 + i * 42
    lo, hi = q(v, 0.02), q(v, 0.98); cut = q(v, 0.90)
    d = density(v, lo, hi)
    pts = [f"{120 + j/(len(d)-1)*(W-140):.1f},{base - x*36:.1f}" for j, x in enumerate(d)]
    b += txt(112, base - 4, lab, 9, NA, "end")
    b += f'<polygon points="{120},{base} {" ".join(pts)} {W-20},{base}" fill="{A}" opacity="0.3"/>'
    b += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{A}" stroke-width="1.6"/>'
    xc = 120 + (cut - lo) / ((hi - lo) or 1) * (W - 140)
    b += f'<line x1="{xc:.0f}" y1="{base-38}" x2="{xc:.0f}" y2="{base}" stroke="{WN}" stroke-width="1.5"/>'
opts.append(("Ridgeline", "Overlapping density curves. Rust tick is the worst 10% line.",
             f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'))

# 2 VIOLIN
H = 46 * len(FLAGS) + 30
b = ""
for i, (k, lab) in enumerate(FLAGS):
    v = vals(k); mid = 34 + i * 46
    lo, hi = q(v, 0.02), q(v, 0.98)
    d = density(v, lo, hi)
    up = [f"{130 + j/(len(d)-1)*(W-150):.1f},{mid - x*15:.1f}" for j, x in enumerate(d)]
    dn = [f"{130 + j/(len(d)-1)*(W-150):.1f},{mid + x*15:.1f}" for j, x in reversed(list(enumerate(d)))]
    b += txt(122, mid + 4, lab, 9, NA, "end")
    b += f'<polygon points="{" ".join(up + dn)}" fill="{A}" opacity="0.4" stroke="{A}" stroke-width="1"/>'
    for p_, col in ((0.5, INK), (0.9, WN)):
        x = 130 + (q(v, p_) - lo) / ((hi - lo) or 1) * (W - 150)
        b += f'<line x1="{x:.0f}" y1="{mid-17}" x2="{x:.0f}" y2="{mid+17}" stroke="{col}" stroke-width="1.6"/>'
opts.append(("Violin", "Mirrored density. White line median, rust line worst 10%.",
             f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'))

# 3 DECILE DOTS
H = 40 * len(FLAGS) + 34
b = txt(130, 20, "each dot is a decile boundary", 9, NA)
for i, (k, lab) in enumerate(FLAGS):
    v = vals(k); y = 42 + i * 40
    lo, hi = q(v, 0.02), q(v, 0.98)
    b += txt(122, y + 4, lab, 9, NA, "end")
    b += f'<line x1="130" y1="{y}" x2="{W-20}" y2="{y}" stroke="{RULE}"/>'
    for dec in range(1, 10):
        x = 130 + (q(v, dec / 10) - lo) / ((hi - lo) or 1) * (W - 150)
        hot = dec == 9
        b += (f'<circle cx="{x:.1f}" cy="{y}" r="{4.5 if hot else 3}" '
              f'fill="{WN if hot else A}" opacity="{1 if hot else 0.6}"/>')
opts.append(("Decile dots", "Nine dots per test. Where they bunch, companies bunch.",
             f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'))

# 4 CUMULATIVE
H = 60 * len(FLAGS) + 20
b = ""
for i, (k, lab) in enumerate(FLAGS):
    v = vals(k); base = 52 + i * 60
    lo, hi = q(v, 0.02), q(v, 0.98)
    b += txt(20, base - 44, lab, 10, INK)
    pts = []
    for j in range(0, 101):
        x = 20 + j / 100 * (W - 40)
        val = q(v, j / 100)
        yy = base - 36 * max(0, min(1, (val - lo) / ((hi - lo) or 1)))
        pts.append(f"{x:.1f},{yy:.1f}")
    b += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{A}" stroke-width="2"/>'
    x90 = 20 + 0.9 * (W - 40)
    b += f'<line x1="{x90:.0f}" y1="{base-38}" x2="{x90:.0f}" y2="{base}" stroke="{WN}" stroke-dasharray="3 3"/>'
    b += f'<line x1="20" y1="{base}" x2="{W-20}" y2="{base}" stroke="{RULE}"/>'
opts.append(("Cumulative", "Percentile on the x axis, the figure on the y. Read off any level.",
             f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'))

# 5 HEATMAP MATRIX - companies as columns, tests as rows
top = sorted(rows, key=lambda r: -r["composite"])[:70]
H = 30 * len(FLAGS) + 46
cw = (W - 130) / len(top)
b = txt(122, 22, f"worst {len(top)} companies, left to right", 9, NA, "end")
for i, (k, lab) in enumerate(FLAGS):
    y = 34 + i * 30
    b += txt(122, y + 14, lab, 9, NA, "end")
    for j, r in enumerate(top):
        f = r["flags"][k]
        x = 130 + j * cw
        if not f["applicable"] or f.get("rank") is None:
            b += f'<rect x="{x:.1f}" y="{y}" width="{cw-0.5:.1f}" height="20" fill="{RULE}" opacity="0.35"/>'
        else:
            o = 0.08 + 0.9 * (f["rank"] / 100) ** 2
            col = WN if f["rank"] >= 90 else A
            b += f'<rect x="{x:.1f}" y="{y}" width="{cw-0.5:.1f}" height="20" fill="{col}" opacity="{o:.2f}"/>'
opts.append(("Matrix", "One column per company, one row per test. Grey means not applicable.",
             f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'))

# 6 THRESHOLD TABLE
H = 32 * len(FLAGS) + 56
b = ""
for j, (lbl, xx) in enumerate([("median", 250), ("worst 10%", 340), ("worst 1%", 430)]):
    b += txt(xx, 24, lbl, 9, NA, "end")
for i, (k, lab) in enumerate(FLAGS):
    v = vals(k); y = 48 + i * 32
    b += txt(20, y, lab, 12, INK)
    for xx, p_ in ((250, .5), (340, .9), (430, .99)):
        val = q(v, p_)
        col = INK if p_ == .5 else WN
        b += txt(xx, y, f"{val*100:+.1f}%", 12, col, "end")
    b += f'<line x1="20" y1="{y+10}" x2="{W-20}" y2="{y+10}" stroke="{RULE}" opacity="0.5"/>'
opts.append(("Threshold table", "No picture. The actual figure at each cut-off.",
             f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'))

cards = "".join(
    f'<div class="opt"><div class="hd"><span class="n">{i}</span><span class="ti">{t}</span></div>'
    f'<div class="sv">{s}</div><p class="ds">{d}</p></div>'
    for i, (t, d, s) in enumerate(opts, 1))
open("dist.html", "w", encoding="utf-8").write(
    '<html><head><meta charset="utf-8"><style>'
    'body{margin:0;background:#0f1319;color:#e6eaef;font:14px/1.5 ui-sans-serif,system-ui,sans-serif;padding:26px}'
    'h1{font:600 13px/1 ui-sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#82a8ca;margin:0 0 6px}'
    '.sub{color:#99a4b1;font-size:13px;margin:0 0 20px}'
    '.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}'
    '.opt{background:#161c24;border:1px solid #262f3a;border-radius:9px;padding:14px}'
    '.hd{display:flex;align-items:baseline;gap:9px;margin-bottom:8px}'
    '.n{font:600 11px/1 ui-monospace,monospace;color:#5d6874}.ti{font-size:15px;font-weight:600}'
    '.sv svg{width:100%;height:auto;display:block}.ds{margin:8px 0 0;font-size:12px;color:#99a4b1}'
    '</style></head><body><h1>Distributions - six more ways</h1>'
    '<p class="sub">Box plot, histogram, sorted curve and threshold strips were shown on 18/08. These are new.</p>'
    f'<div class="grid">{cards}</div></body></html>')
print("wrote dist.html")
