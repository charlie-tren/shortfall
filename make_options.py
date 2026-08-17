"""Ten renderings of the same data, for Charlie to pick from. Throwaway."""
import json, math, html

p = json.load(open("docs/data.json"))
pts = [r for r in p["names"] if r["short_interest"] is not None]
W, H, L, R, T, B = 470, 300, 44, 14, 26, 40
CROWD = 0.09
ylo = max(0, math.floor((min(r["composite"] for r in pts) - 3) / 5) * 5)
maxsi = max(r["short_interest"] for r in pts)
A, WN, NA, RULE = "#82a8ca", "#d29b76", "#5d6874", "#262f3a"

def px(v): return L + math.sqrt(min(v, maxsi) / maxsi) * (W - L - R)
def py(v): return H - B - ((v - ylo) / (100 - ylo)) * (H - T - B)
def hot(r): return r["composite"] >= 90 and r["short_interest"] < CROWD
def dot(x, y, r_, fill, op): return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_}" fill="{fill}" opacity="{op}"/>'
def txt(x, y, s, size=10, fill=NA, anchor="start"):
    return f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" font-family="monospace">{html.escape(str(s))}</text>'

def frame(body, xlab="short interest"):
    g = "".join(f'<line x1="{L}" y1="{py(v)}" x2="{W-R}" y2="{py(v)}" stroke="{RULE}"/>' + txt(L-7, py(v)+4, v, 10, NA, "end")
                for v in range(int(math.ceil(ylo/20)*20), 101, 20))
    return f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{g}{body}{txt((L+W-R)/2, H-6, xlab, 10, NA, "middle")}</svg>'

def plain(body):
    return f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{body}</svg>'

opts = []

b = "".join(dot(px(r["short_interest"]), py(r["composite"]), 3.6 if hot(r) else 2.4,
                WN if hot(r) else A, 0.9 if hot(r) else 0.4) for r in pts)
opts.append(("Current", "What is live now. Sqrt x-axis, corner shaded.", frame(b)))

sub = [r for r in pts if r["composite"] >= 75]
b = "".join(dot(px(r["short_interest"]), py(r["composite"]), 4 if hot(r) else 2.8,
                WN if hot(r) else A, 0.95 if hot(r) else 0.5) for r in sub)
opts.append(("Top quartile only", f"Drop everything under 75. {len(sub)} points, not {len(pts)}.", frame(b)))

cells = {}
for r in pts:
    k = (int(px(r["short_interest"]) // 18), int(py(r["composite"]) // 18))
    cells[k] = cells.get(k, 0) + 1
mx = max(cells.values())
b = "".join(f'<rect x="{k[0]*18}" y="{k[1]*18}" width="17" height="17" fill="{A}" opacity="{0.10+0.85*v/mx:.2f}"/>'
            for k, v in cells.items())
b += "".join(dot(px(r["short_interest"]), py(r["composite"]), 3, WN, 1) for r in pts if hot(r))
opts.append(("Density grid", "Bin the crowd. Only corner names stay as dots.", frame(b)))

amax = max((r["assets"] or 0) for r in pts)
b = "".join(dot(px(r["short_interest"]), py(r["composite"]),
                round(1.5 + 5 * math.sqrt((r["assets"] or 0) / amax), 1),
                WN if hot(r) else A, 0.85 if hot(r) else 0.28) for r in pts)
opts.append(("Bubble by size", "Radius is total assets. Big flagged names pop.", frame(b)))

b = "".join(dot(px(r["short_interest"]), py(r["composite"]), 2, NA, 0.22) for r in pts if not hot(r))
for r in sorted([r for r in pts if hot(r)], key=lambda r: -r["composite"])[:8]:
    x, y = px(r["short_interest"]), py(r["composite"])
    b += dot(x, y, 3.4, WN, 1) + txt(x + 6, y + 3, r["ticker"], 9)
opts.append(("Labelled corner", "Rest greyed right back. The corner is named.", frame(b)))

b, bands = "", {}
for r in sorted(pts, key=lambda r: r["short_interest"]):
    band = int(r["composite"] // 5) * 5
    i = bands.get(band, 0); bands[band] = i + 1
    b += dot(px(r["short_interest"]), py(band + 2.5) + ((i % 7) - 3) * 3.0, 2.2,
             WN if hot(r) else A, 0.9 if hot(r) else 0.4)
opts.append(("Beeswarm", "Scores snapped to bands and jittered so nothing hides.", frame(b)))

q = {"a": 0, "b": 0, "c": 0, "d": 0}
for r in pts:
    hi, cr = r["composite"] >= 90, r["short_interest"] >= CROWD
    q["a" if (hi and not cr) else "b" if (hi and cr) else "c" if not hi and not cr else "d"] += 1
b = ""
for i, (k, lab) in enumerate([("a", "flagged, not shorted"), ("b", "flagged, crowded"),
                              ("c", "quiet"), ("d", "shorted, not flagged")]):
    x, y = L + (i % 2) * 200, T + (i // 2) * 112
    b += (f'<rect x="{x}" y="{y}" width="190" height="100" rx="6" fill="{WN if k=="a" else A}" '
          f'opacity="{0.22 if k=="a" else 0.07}"/>' + txt(x + 14, y + 48, q[k], 26, "#e6eaef")
          + txt(x + 14, y + 70, lab, 10))
opts.append(("Quadrant counts", "No dots. Four numbers, click to drill in.", plain(b)))

sis = sorted(pts, key=lambda r: r["short_interest"])
rank = {r["ticker"]: 100 * i / (len(sis) - 1) for i, r in enumerate(sis)}
b = "".join(dot(L + rank[r["ticker"]] / 100 * (W - L - R), py(r["composite"]),
                3.4 if hot(r) else 2.3, WN if hot(r) else A, 0.9 if hot(r) else 0.36) for r in pts)
opts.append(("Rank vs rank", "Short interest as a percentile too. Even spread.", frame(b, "short interest percentile")))

b = ""
for i, mkt in enumerate(["United States (NYSE & Nasdaq)", "Australia (ASX)"]):
    sub = [r for r in p["names"] if r["market"] == mkt and r["short_interest"] is not None]
    ox = i * 232
    b += txt(ox + 20, 16, f'{mkt.split(" (")[0]} ({len(sub)})', 10)
    for r in sub:
        b += dot(ox + 26 + math.sqrt(min(r["short_interest"], maxsi) / maxsi) * 172,
                 py(r["composite"]), 3 if hot(r) else 2, WN if hot(r) else A,
                 0.9 if hot(r) else 0.4)
opts.append(("Split by market", "Two panels. ASX has no short interest, so it empties.", frame(b)))

b = ""
for i, r in enumerate(sorted([r for r in pts if hot(r)], key=lambda r: -r["composite"])[:12]):
    y = T + i * 21
    w = (r["composite"] - 88) / 12 * 300
    b += (txt(L + 52, y + 11, r["ticker"], 10, "#e6eaef", "end")
          + f'<rect x="{L+58}" y="{y+2}" width="{max(w,2):.0f}" height="11" rx="2" fill="{WN}" opacity="0.8"/>'
          + txt(L + 62 + max(w, 2), y + 11, f'{r["composite"]:.0f} · {100*r["short_interest"]:.1f}% short', 9))
opts.append(("Just the shortlist", "Abandon the scatter. The 12 corner names as bars.", plain(b)))

cards = "".join(
    f'<div class="opt"><div class="hd"><span class="n">{i}</span><span class="ti">{t}</span></div>'
    f'<div class="sv">{svg}</div><p class="ds">{d}</p></div>'
    for i, (t, d, svg) in enumerate(opts, 1))
open("options.html", "w", encoding="utf-8").write(
    '<html><head><meta charset="utf-8"><style>'
    'body{margin:0;background:#0f1319;color:#e6eaef;font:14px/1.5 ui-sans-serif,system-ui,sans-serif;padding:26px}'
    'h1{font:600 13px/1 ui-sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#82a8ca;margin:0 0 20px}'
    '.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}'
    '.opt{background:#161c24;border:1px solid #262f3a;border-radius:9px;padding:14px}'
    '.hd{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}'
    '.n{font:600 11px/1 ui-monospace,monospace;color:#5d6874}.ti{font-size:15px;font-weight:600}'
    '.sv svg{width:100%;height:auto;display:block}.ds{margin:6px 0 0;font-size:12px;color:#99a4b1}'
    '</style></head><body><h1>Dot plot - ten directions</h1>'
    f'<div class="grid">{cards}</div></body></html>')
print("wrote options.html with", len(opts), "options")
