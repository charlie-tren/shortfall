"""Ten candidate axis pairs, each with a measured correlation. Throwaway."""
import json, math, html, statistics

p = json.load(open("docs/data.json"))
rows = p["names"]
W, H, L, R, T, B = 470, 290, 58, 16, 24, 44
A, WN, NA, RULE = "#82a8ca", "#d29b76", "#5d6874", "#262f3a"

def val(r, k):
    if k == "logassets": return math.log10(r["assets"]) if r.get("assets") else None
    if k == "si": return r.get("short_interest")
    if k == "ret": return r.get("ret_1y")
    if k == "score": return r.get("composite")
    if k == "ntests": return r.get("applicable")
    if k == "turn": return (r["revenue"] / r["assets"]) if r.get("revenue") and r.get("assets") else None
    f = r["flags"].get(k)
    return f["value"] if f and f["applicable"] else None

LAB = {"logassets": "total assets (log)", "si": "short interest", "ret": "12m return",
       "score": "score", "ntests": "tests applying", "turn": "revenue / assets",
       "accruals": "accruals", "working_capital": "receivables & inventory",
       "share_count_roic": "share count vs returns", "goodwill": "goodwill share",
       "tax_rate": "tax rate swing", "stock_comp": "stock comp"}

PAIRS = [("logassets","si"),("ntests","turn"),("logassets","turn"),("logassets","accruals"),
         ("si","ret"),("turn","share_count_roic"),("logassets","ret"),
         ("share_count_roic","stock_comp"),("working_capital","stock_comp"),("si","accruals")]

def sp(pr):
    xs=[a for a,_ in pr]; ys=[b for _,b in pr]
    rx={v:i for i,v in enumerate(sorted(xs))}; ry={v:i for i,v in enumerate(sorted(ys))}
    x=[rx[v] for v in xs]; y=[ry[v] for v in ys]
    mx,my=statistics.mean(x),statistics.mean(y)
    n=sum((i-mx)*(j-my) for i,j in zip(x,y)); d=(sum((i-mx)**2 for i in x)*sum((j-my)**2 for j in y))**0.5
    return n/d if d else 0

def clip(vs):
    s = sorted(vs); return s[int(0.02*(len(s)-1))], s[int(0.98*(len(s)-1))]

cards = []
for xk, yk in PAIRS:
    pr = [(val(r, xk), val(r, yk), r["composite"]) for r in rows]
    pr = [t for t in pr if t[0] is not None and t[1] is not None]
    rho = sp([(a, b) for a, b, _ in pr])
    xlo, xhi = clip([a for a, _, _ in pr]); ylo, yhi = clip([b for _, b, _ in pr])
    px = lambda v: L + max(0, min(1, (v - xlo) / ((xhi - xlo) or 1))) * (W - L - R)
    py = lambda v: H - B - max(0, min(1, (v - ylo) / ((yhi - ylo) or 1))) * (H - T - B)
    body = "".join(
        f'<circle cx="{px(a):.1f}" cy="{py(b):.1f}" r="2.6" fill="{WN if s>=90 else A}" '
        f'opacity="{0.95 if s>=90 else 0.28}"/>' for a, b, s in pr)
    # fitted line
    xs = [a for a, _, _ in pr]; ys = [b for _, b, _ in pr]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys)); den = sum((x-mx)**2 for x in xs)
    if den:
        sl = num/den
        body += (f'<line x1="{px(xlo):.0f}" y1="{py(my+sl*(xlo-mx)):.0f}" x2="{px(xhi):.0f}" '
                 f'y2="{py(my+sl*(xhi-mx)):.0f}" stroke="{NA}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    svg = (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">'
           f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{RULE}"/>'
           f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{RULE}"/>{body}'
           f'<text x="{(L+W-R)/2}" y="{H-10}" fill="{NA}" font-size="11" text-anchor="middle" '
           f'font-family="monospace">{html.escape(LAB[xk])}</text>'
           f'<text x="-{(T+(H-B-T)/2):.0f}" y="14" fill="{NA}" font-size="11" text-anchor="middle" '
           f'font-family="monospace" transform="rotate(-90)">{html.escape(LAB[yk])}</text></svg>')
    cards.append((f"{LAB[yk]} vs {LAB[xk]}", f"rho {rho:+.2f}, n={len(pr)}", svg))

body = "".join(
    f'<div class="opt"><div class="hd"><span class="n">{i}</span><span class="ti">{t}</span>'
    f'<span class="rho">{d}</span></div><div class="sv">{s}</div></div>'
    for i, (t, d, s) in enumerate(cards, 1))
open("pairs.html", "w", encoding="utf-8").write(
    '<html><head><meta charset="utf-8"><style>'
    'body{margin:0;background:#0f1319;color:#e6eaef;font:14px/1.5 ui-sans-serif,system-ui,sans-serif;padding:26px}'
    'h1{font:600 13px/1 ui-sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#82a8ca;margin:0 0 6px}'
    '.sub{color:#99a4b1;font-size:13px;margin:0 0 20px}'
    '.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}'
    '.opt{background:#161c24;border:1px solid #262f3a;border-radius:9px;padding:13px}'
    '.hd{display:flex;align-items:baseline;gap:9px;margin-bottom:4px;flex-wrap:wrap}'
    '.n{font:600 11px/1 ui-monospace,monospace;color:#5d6874}.ti{font-size:14px;font-weight:600}'
    '.rho{font:11px/1 ui-monospace,monospace;color:#82a8ca;margin-left:auto}'
    '.sv svg{width:100%;height:auto;display:block}'
    '</style></head><body><h1>Ten pairs that actually correlate</h1>'
    '<p class="sub">Rust dots score 90+. Dashed line is the fit. Ordered by strength.</p>'
    f'<div class="grid">{body}</div></body></html>')
print("wrote pairs.html")
