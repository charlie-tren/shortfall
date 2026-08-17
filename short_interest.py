"""Short interest, so the page can show what the market already believes.

WHY IT IS HERE, given it correlates with nothing: measured 17/08/2026, composite
against short interest is rho +0.036 across a 150-name sample, and median short
interest is flat across score quartiles (3.8%, 3.7%, 3.2%, 4.1%).

The absence of a relationship is the reason to plot it. If the screen agreed with
short sellers it would only be rediscovering crowded trades. Because the two are
independent, a company can sit high on the screen with almost nobody short it -
and that corner is the only part of this page that is not already priced.

US ONLY. Yahoo returned a figure for 150 of 150 US names sampled and nothing at all
for ASX. ASIC publishes daily short positions for Australian stocks and would close
the gap, but it is a separate source and is not wired up.
"""

import json
import os
import warnings

CACHE = "short_interest.json"

# Above this share of float a name is "crowded" - the market is already there.
# Roughly the 90th percentile of the sampled distribution (9.0%), rounded.
CROWDED = 0.09


def load(path=CACHE):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def fetch(tickers, log=None):
    """{ticker: percent of float} for whatever Yahoo will give us.

    One call per company, so this is the slowest step in the build after the ASX
    leg. Absent is absent - a missing name is left out rather than defaulted to
    zero, because "nobody is short it" and "we do not know" are different claims
    and the second must never be drawn as the first.
    """
    import yfinance as yf

    out = {}
    for i, t in enumerate(tickers, 1):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                v = yf.Ticker(t).info.get("shortPercentOfFloat")
            if v is not None:
                out[t] = round(float(v), 5)
        except Exception:
            pass
        if log and i % 100 == 0:
            log(f"  short interest {i}/{len(tickers)}")
    return out


def save(data, path=CACHE):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
