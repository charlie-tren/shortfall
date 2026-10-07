"""All SEC HTTP lives here. Rate limiting is applied in one place on purpose.

SEC guidance is 10 requests/second and a contactable User-Agent. We sleep 250ms,
comfortably inside it.
"""

import json
import time
import urllib.error
import urllib.request

# SEC asks for a contactable User-Agent. This repo is public, so the contact point is
# the site rather than a work address - there is no reason to put an employer's domain
# in the request log of a public screener.
UA = {"User-Agent": "shortfall (+https://charlietrenorden.com/shortfall/)"}
PAUSE = 0.25


def _get(url):
    time.sleep(PAUSE)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def normalise_ticker(ticker):
    """Wikipedia writes class shares BRK.B; EDGAR writes BRK-B."""
    return ticker.replace(".", "-").upper()


# company_tickers.json is NOT complete. Measured 14/08/2026: AEP is absent from it
# entirely, yet files with the SEC under CIK 4904, ticker AEP, exchange Nasdaq -
# confirmed against data.sec.gov/submissions/CIK0000004904.json.
#
# Only add an entry here after confirming the CIK against the submissions endpoint.
# Guessing a CIK would attach one company's filings to another company's name.
TICKER_CIK_OVERRIDES = {
    "AEP": 4904,   # American Electric Power Co Inc, verified 14/08/2026
}


# A holding-company reorganisation moves the ticker to a NEW CIK that has filed no
# annual report yet, so every past 10-K sits under the old one. The new CIK then
# carries a balance sheet and no revenue, profit or cash flow, all six tests read
# not-applicable, and the company silently drops into `excluded`.
#
# ExxonMobil, July 2026: XOM moved to ExxonMobil Holdings Corp (2115436) and Exxon
# Mobil Corp (34088) filed a 25-NSE on 02/07/2026. Every 10-K to FY2025 is under
# 34088. Verified 07/10/2026 against both submissions endpoints.
#
# successor CIK -> predecessor CIKs, newest first. Each concept is read from the
# successor first and the predecessors after, so once the new parent files its own
# 10-K it takes over without anyone touching this. Only a pure reorganisation goes
# here: after a MERGER the predecessor is a different business, and splicing its
# history on would score a company on someone else's accounts.
CIK_PREDECESSORS = {
    2115436: (34088,),   # ExxonMobil Holdings Corp <- Exxon Mobil Corp
}


def filer_ciks(cik):
    """The CIK and any predecessors whose filings belong to the same company."""
    return (cik, *CIK_PREDECESSORS.get(cik, ()))


def load_ticker_lookup():
    """{normalised ticker: cik int} for every SEC filer. ~10,400 entries."""
    d = _get("https://www.sec.gov/files/company_tickers.json")
    lookup = {v["ticker"].upper(): int(v["cik_str"]) for v in d.values()}
    lookup.update(TICKER_CIK_OVERRIDES)
    return lookup


def dedupe_by_cik(names, lookup):
    """Drop the second share class of a dual-class listing.

    GOOGL/GOOG, FOXA/FOX and NWSA/NWS each map to ONE CIK, because they are one
    filer. Keying anything by CIK without this silently loses whichever class is
    seen second; showing both would put the same company on the page twice with
    identical flags. First seen wins, which is the class the index table lists first.

    Returns (kept names, [(dropped ticker, kept ticker)]).
    """
    seen, kept, dropped = {}, [], []
    for n in names:
        cik = lookup.get(normalise_ticker(n["ticker"]))
        if cik is None:
            kept.append(n)
            continue
        if cik in seen:
            dropped.append((n["ticker"], seen[cik]))
            continue
        seen[cik] = n["ticker"]
        kept.append(n)
    return kept, dropped


def map_tickers_to_cik(tickers, lookup):
    """Map, failing LOUDLY on any miss.

    A silent drop here removes a company from the screen with no trace, which is
    the worst failure mode this build has: the page would look complete.
    """
    out, missing = {}, []
    for t in tickers:
        cik = lookup.get(normalise_ticker(t))
        if cik is None:
            missing.append(t)
        else:
            out[t] = cik
    if missing:
        raise ValueError(f"{len(missing)} tickers did not map to a CIK: {missing}")
    return out


def parse_frame(payload):
    """{cik: float} from a frames payload."""
    return {int(e["cik"]): float(e["val"]) for e in payload.get("data", [])}


def frame(tag, unit, period, taxonomy="us-gaap"):
    """One tag, every filer, one period. Returns {cik: value}, {} if absent.

    A missing frame is normal - not every tag exists in every period - so this
    returns {} rather than raising. The COVERAGE GATE in score.py is what turns a
    genuinely absent concept into a build failure.
    """
    url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json"
    try:
        return parse_frame(_get(url))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise


def submissions(cik):
    """Filing metadata for one company. Used for the event flags."""
    return _get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
