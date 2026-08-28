"""Render the cross-site link affordance on the REAL Shortfall card, one variant per shot.

    python tools/link_options.py

Charlie's rule is to render options rather than describe them, and to render the real
page with one thing overridden rather than a mock-up - the spacing, the type and the
actual numbers are then exactly what he will see. So this loads docs/index.html off
disk, waits for the card list, and injects each candidate affordance into the same
card before shooting it.

Every variant builds its nodes with createElement and textContent rather than an HTML
string. That is not ceremony: the repo's write hook refuses innerHTML, and the rule is
right even here, where a company name from the data set is being put on the page.

Writes a contact sheet next to itself. Throwaway tooling for one decision; delete it
once the shape is settled.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "docs" / "index.html").as_uri()
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "tools" / "link_options.png")

# Injected with the page's own custom properties, so a variant that looks wrong looks
# wrong for design reasons rather than because it was styled by hand.
CSS = """
.xl { font-family: var(--mono); font-size: 12px; }
.xl a { color: var(--accent); text-decoration: none;
        border-bottom: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); }
.xl .off { color: var(--na); border-bottom: 1px dotted var(--na); }
.xl .sep { color: var(--na); padding: 0 .5em; }
.xl .lead { color: var(--soft); padding-right: .55em; }
.xfoot { margin-top: 14px; padding-top: 12px;
         border-top: 1px solid color-mix(in srgb, var(--soft) 22%, transparent); }
.xmenu { position: relative; display: inline-block; }
.xmenu .pop { position: absolute; left: 0; top: 125%; z-index: 5; min-width: 172px;
              background: #14171c; padding: 6px 0;
              border: 1px solid color-mix(in srgb, var(--soft) 30%, transparent);
              border-radius: 6px; box-shadow: 0 8px 24px rgba(0,0,0,.45); }
.xmenu .pop a { display: block; padding: 7px 14px; border: 0; font-size: 12.5px; }
.xdash { border-bottom: 1px dashed var(--soft); }
.xcaret { font-size: 11px; color: var(--soft); padding-left: .35em; }
.xmark { display: inline-flex; align-items: center; justify-content: center;
         width: 22px; height: 22px; margin-left: 6px; border-radius: 4px;
         font-family: var(--mono); font-size: 10px; color: var(--accent);
         border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent); }
"""

# The helpers every variant is written against. `row` builds a run of links with the
# middot between them; `off` marks one as unavailable rather than clickable.
HELPERS = """
const card = document.querySelector('#cards .card');
const mk = (tag, cls, text, parent) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text) n.textContent = text;
  if (parent) parent.appendChild(n);
  return n;
};
const foot = () => {
  let f = card.querySelector('.xfoot');
  if (!f) { f = mk('div', 'xfoot', '', card); }
  f.textContent = '';
  return f;
};
const row = (host, lead, items) => {
  const s = mk('span', 'xl', '', host);
  if (lead) mk('span', 'lead', lead, s);
  items.forEach(([label, available], i) => {
    if (i) mk('span', 'sep', '\\u00b7', s);
    const n = mk(available ? 'a' : 'span', available ? '' : 'off', label, s);
    if (available) n.href = '#';
    else n.title = 'Not in this universe';
  });
  return s;
};
const menu = (host, items) => {
  const m = mk('span', 'xmenu', '', host);
  const pop = mk('span', 'pop xl', '', m);
  items.forEach((label) => { const a = mk('a', '', label, pop); a.href = '#'; });
  return m;
};
const CD = 'Consensus Drift', DS = 'DCF Studio';
"""

VARIANTS = [
    ("Today", "no change - the baseline", "", False),

    ("1  Two plain links, footer",
     "always visible, no menu, nothing to discover",
     "row(foot(), '', [[CD, true], [DS, true]]);", False),

    ("2  'Also on' prefix",
     "same, with a label saying what the links are",
     "row(foot(), 'Also on', [[CD, true], [DS, true]]);", False),

    ("3  The name opens a menu",
     "shown open - closed it is a company name with a dashed underline",
     """const h = card.querySelector('h3');
        const name = h.textContent; h.textContent = '';
        const m = menu(h, [CD, DS]);
        m.insertBefore(mk('span', 'xdash', name), m.firstChild);""", True),

    ("4  A caret beside the name",
     "shown open - the name itself keeps whatever it does now",
     """const h = card.querySelector('h3');
        const m = menu(h, [CD, DS]);
        m.insertBefore(mk('span', 'xcaret', '\\u25be'), m.firstChild);""", True),

    ("5  Two marks, no words",
     "needs each site to have a recognisable mark first",
     """const t = card.querySelector('.ticker');
        let at = t;
        [['CD', 'Consensus Drift'], ['DS', 'DCF Studio']].forEach(([s, full]) => {
          const n = mk('span', 'xmark', s); n.title = full;
          at.parentNode.insertBefore(n, at.nextSibling);
          at = n;
        });""", False),

    ("7  Links in the header",
     "beside the ticker rather than under the flags",
     """const t = card.querySelector('.ticker');
        const holder = mk('span', '', '');
        holder.style.paddingLeft = '12px';
        t.parentNode.insertBefore(holder, t.nextSibling);
        row(holder, '', [[CD, true], [DS, true]]);""", False),

    ("17  Missing target greyed",
     "how a name outside the other universe reads",
     "row(foot(), 'Also on', [[CD, true], [DS, false]]);", False),

    ("18  Missing target omitted",
     "shorter than its neighbours - compare against 2",
     "row(foot(), 'Also on', [[CD, true]]);", False),
]


def font(size):
    for name in ("seguisb.ttf", "segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    shots = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for title, note, js, tall in VARIANTS:
            # color_scheme matters: the page picks its theme from the OS unless one
            # is saved, and Playwright defaults to light - so without this the whole
            # sheet is a light-mode site Charlie does not use.
            pg = b.new_page(viewport={"width": 900, "height": 1500},
                            device_scale_factor=2, color_scheme="dark")
            pg.goto(PAGE)
            pg.wait_for_selector("#cards .card", state="visible", timeout=30000)
            pg.add_style_tag(content=CSS)
            if js:
                pg.evaluate("() => {" + HELPERS + js + "}")
            box = pg.query_selector("#cards .card").bounding_box()
            pad = 14
            # A popover is drawn outside the card's own box, so shoot a padded region
            # of the page rather than the element, or the menu is clipped away.
            # full_page because the card list sits well below the fold: a viewport
            # screenshot with a clip that far down is "outside the resulting image".
            shots.append((title, note, pg.screenshot(full_page=True, clip={
                "x": box["x"] - pad, "y": box["y"] - pad,
                "width": box["width"] + pad * 2,
                "height": box["height"] + pad * 2 + (86 if tall else 0),
            })))
            pg.close()
        b.close()

    tiles = [Image.open(io.BytesIO(s)) for _, _, s in shots]
    w = max(t.width for t in tiles)
    head, gap = 74, 26
    sheet = Image.new("RGB", (w + 48, sum(t.height + head + gap for t in tiles) + 24),
                      "#0d0f12")
    d = ImageDraw.Draw(sheet)
    y = 12
    for (title, note, _), t in zip(shots, tiles):
        d.text((24, y + 8), title, fill="#e8e6e1", font=font(28))
        d.text((24, y + 44), note, fill="#8b8f97", font=font(20))
        sheet.paste(t, (24, y + head))
        y += t.height + head + gap
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"{OUT}  {sheet.width}x{sheet.height}  {len(tiles)} variants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
