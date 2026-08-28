"""Which companies the sibling sites cover, so a link is never offered into a page
that does not have the company.

Shortfall, Consensus Drift and DCF Studio each publish a `tickers.json` listing what
they cover. This module reads a sibling's, and it is deliberately paranoid about it:

- **The live file is fetched, and the answer is COMMITTED to `peers/`.** So the build
  never depends on the network being up or the sibling being deployed - a failed fetch
  falls back to the copy from last time, loudly, and the site still builds.
- **A fetched list is only accepted if it looks like one.** A Cloudflare error page,
  a 404 body or an empty array would otherwise silently empty the peer set and quietly
  delete every link on the site, which is the failure mode worth guarding: a wrong
  answer that looks like a working build.

The overlap is not the formality it first appears. Consensus Drift plots 1,207 of its
1,309 names, dropping the rest each week where estimate history is too sparse - so 37
of Shortfall's 652 have no reading to link to, and the number moves weekly.
"""
from __future__ import annotations

import json
import os

PEERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "peers")

SITES = {
    "consensus-drift": "https://charlietrenorden.com/consensus-drift/tickers.json",
}

# A sibling that loses most of its universe is far more likely to be a broken build
# than a real change, and accepting it would silently strip the links from this site.
MIN_KEEP = 0.5


def cached(slug):
    path = os.path.join(PEERS, f"{slug}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fetch(slug, url, timeout=20):
    import urllib.request
    # Most of the estate sits behind Cloudflare, which rejects urllib's default agent.
    req = urllib.request.Request(url, headers={"User-Agent": "shortfall-build/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def load(slug=None, log=print):
    """Return {slug: {"tickers": [...], "as_of": ...}} for every sibling site."""
    out = {}
    for s, url in SITES.items():
        if slug and s != slug:
            continue
        old = cached(s)
        try:
            got = fetch(s, url)
            new = got.get("tickers")
            if not isinstance(new, list) or not new:
                raise ValueError(f"no ticker list in {url}")
            if old and len(new) < len(old["tickers"]) * MIN_KEEP:
                raise ValueError(f"{s} published {len(new)} tickers against "
                                 f"{len(old['tickers'])} last time - refusing it")
            os.makedirs(PEERS, exist_ok=True)
            with open(os.path.join(PEERS, f"{s}.json"), "w",
                      encoding="utf-8", newline="\n") as fh:
                json.dump(got, fh, indent=1)
            out[s] = got
            log(f"peers: {s} {len(new)} tickers, as of {got.get('as_of')}")
        except Exception as exc:                      # noqa: BLE001
            if old is None:
                # No file=sys.stderr: `log` is injected by run_build and takes one
                # argument. Passing a kwarg the caller's logger does not accept turns
                # a warning into a TypeError that takes the whole build down.
                log(f"peers: {s} unreachable and never cached - no links to it "
                    f"will be shown ({exc})")
                continue
            out[s] = old
            log(f"peers: {s} unreachable, using the cached list from "
                f"{old.get('as_of')} ({exc})")
    return out


def write_js(peers, path="docs/peers.js"):
    """A JS global rather than a fetch. Same reason as data.js: the page then works
    from file://, and there is no request to fail in a reader's browser."""
    slim = {s: {"url": d.get("url"), "as_of": d.get("as_of"),
                "tickers": d.get("tickers", [])}
            for s, d in peers.items()}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("window.SHORTFALL_PEERS = " + json.dumps(slim, separators=(",", ":"))
                 + ";\n")


if __name__ == "__main__":
    write_js(load())
