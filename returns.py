"""Twelve-month price change, as CONTEXT on the chart - not as validation.

Measured 17/08/2026: composite against 1-year return is rho -0.025. The screen does
not predict returns and this file must never be read as evidence that it does.

What the number is for is the same question short interest answers: has the market
already marked this down? A company the screen flags that is still up is a different
proposition from one that has already halved, and the chart should let you tell them
apart at a glance rather than requiring a second tab.

One batched download for the whole universe, so this is the cheapest thing in the
build - unlike short interest, which is one call per company.
"""

import json
import warnings

CACHE = "returns.json"


def load(path=CACHE):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def fetch(tickers, period="1y"):
    """{ticker: fractional change} from first to last valid close.

    First and last VALID close, not iloc[0] and iloc[-1]: US and Australian trading
    calendars differ, so a naive first row is NaN for one market or the other.
    """
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = yf.download(tickers, period=period, interval="1d",
                           progress=False, auto_adjust=True)["Close"]
    out = {}
    for t in tickers:
        if t not in data.columns:
            continue
        s = data[t].dropna()
        if len(s) < 100:      # too little history to be a 12-month change
            continue
        out[t] = round(float(s.iloc[-1] / s.iloc[0] - 1), 4)
    return out


def save(data, path=CACHE):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
