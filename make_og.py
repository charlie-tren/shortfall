"""Build docs/og.png. The template has always pointed at it; it never existed, so
every share of this page rendered a broken preview.

2400x1260 at 2x, so 1200x630 CSS pixels - the size LinkedIn and Slack expect.
"""
import json
import pathlib

from playwright.sync_api import sync_playwright

p = json.load(open("docs/data.json"))
n = len(p["names"])
disclosed = len(p.get("disclosed", []))
font = pathlib.Path("docs/big-shoulders.woff2").resolve().as_uri()

html = f"""<html><head><meta charset="utf-8"><style>
@font-face {{ font-family:"BS"; src:url("{font}") format("woff2"); font-weight:700; }}
* {{ box-sizing:border-box; margin:0; }}
body {{ width:1200px; height:630px; background:#0f1319; color:#e6eaef;
  font-family:"Iowan Old Style",Georgia,serif; padding:74px 80px;
  display:flex; flex-direction:column; justify-content:space-between; }}
h1 {{ font-family:"BS",sans-serif; font-weight:700; font-size:150px; line-height:.9;
  text-transform:uppercase; letter-spacing:.01em; }}
p {{ font-size:34px; color:#99a4b1; max-width:22ch; line-height:1.35; margin-top:22px; }}
.row {{ display:flex; gap:64px; font-family:ui-monospace,monospace; }}
.k {{ font-size:52px; color:#82a8ca; }}
.l {{ font-size:19px; color:#5d6874; letter-spacing:.06em; text-transform:uppercase; }}
.dom {{ font-family:ui-monospace,monospace; font-size:20px; color:#5d6874; }}
.top {{ display:flex; justify-content:space-between; align-items:flex-start; }}
.mark {{ width:96px; height:96px; border-radius:22px; background:#0b0e13; position:relative; }}
.mark i {{ position:absolute; display:block; }}
.b1 {{ left:24px; top:21px; width:20px; height:54px; border:5px solid #4a6a85; border-radius:4px; }}
.b2 {{ left:54px; top:51px; width:20px; height:24px; background:#9dc0dd; border-radius:4px; }}
</style></head><body>
<div class="top"><div><h1>Shortfall</h1>
<p>Six accounting tests over the S&amp;P 500 and ASX 200.</p></div>
<div class="mark"><i class="b1"></i><i class="b2"></i></div></div>
<div class="row">
  <div><div class="k">{n}</div><div class="l">companies screened</div></div>
  <div><div class="k">{disclosed}</div><div class="l">disclosed a problem</div></div>
  <div><div class="k">6</div><div class="l">tests</div></div>
</div>
<div class="dom">charlietrenorden.com/shortfall</div>
</body></html>"""

out = pathlib.Path("_og.html")
out.write_text(html, encoding="utf-8")
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
    pg.goto(out.resolve().as_uri())
    pg.wait_for_timeout(700)
    pg.screenshot(path="docs/og.png")
    b.close()
out.unlink()
print("wrote docs/og.png")
