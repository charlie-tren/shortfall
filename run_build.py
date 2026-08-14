"""Full rebuild: universe -> both legs -> flags -> gate -> docs/.

US comes from EDGAR frames (about 10 calls per period, not one per company). ASX
comes from Yahoo, one call per company, which is why it dominates the runtime.
"""

import json
import sys
from datetime import date

from asx import load as asx_load, records_from_statements
from build import write as write_html
from build_data import assemble_name, finalise, write, write_js
from edgar import load_ticker_lookup, normalise_ticker, dedupe_by_cik, submissions
from events import extract_events, LABELS
from fetch_us import sweep, build_records

YEARS = (2024, 2023, 2022, 2021)


def us_history(names, lookup, log):
    kept, dropped = dedupe_by_cik(names, lookup)
    if dropped:
        log(f"dual-class dropped: {dropped}")
    meta = {lookup[normalise_ticker(n['ticker'])]: n for n in kept
            if normalise_ticker(n["ticker"]) in lookup}
    unmapped = [n["ticker"] for n in kept if normalise_ticker(n["ticker"]) not in lookup]
    if unmapped:
        raise ValueError(f"unmapped US tickers, add a verified override: {unmapped}")
    history = {}
    for year in YEARS:
        for r in build_records(year, sweep(year), meta):
            history.setdefault(r.ticker, []).append(r)
        log(f"  US {year} done")
    return history


def asx_history(names, log):
    history, failed = {}, []
    for i, n in enumerate(names, 1):
        try:
            recs = records_from_statements(n["ticker"], n["name"], asx_load(n["ticker"]))
        except Exception as exc:
            failed.append((n["ticker"], str(exc)[:60]))
            continue
        if recs:
            history[n["ticker"]] = recs
        else:
            failed.append((n["ticker"], "no records"))
        if i % 50 == 0:
            log(f"  ASX {i}/{len(names)}")
    if failed:
        log(f"  ASX unavailable for {len(failed)}: {[f[0] for f in failed]}")
    return history, failed


def attach_events(rows, lookup, as_of, log):
    """One call per US name. Unavoidable: submissions are per company."""
    hits = 0
    for row in rows:
        row["events"] = []
        if not row["market"].startswith("United States"):
            continue
        cik = lookup.get(normalise_ticker(row["ticker"]))
        if cik is None:
            continue
        try:
            found = extract_events(submissions(cik)["filings"]["recent"], as_of)
        except Exception as exc:
            log(f"  events failed for {row['ticker']}: {exc}")
            continue
        row["events"] = [{**e, "label": LABELS[e["kind"]]} for e in found]
        hits += 1 if row["events"] else 0
    log(f"  names carrying at least one filing event: {hits}")


def main(as_of=None):
    as_of = as_of or date.today().isoformat()
    log = lambda m: print(m, flush=True)

    names = json.load(open("universe.json"))["names"]
    lookup = load_ticker_lookup()

    history = us_history([n for n in names if n["market"].startswith("United States")],
                         lookup, log)
    au, au_failed = asx_history([n for n in names if n["market"] == "Australia (ASX)"], log)
    history.update(au)

    rows = [x for x in (assemble_name(v) for v in history.values()) if x]
    attach_events(rows, lookup, as_of, log)

    payload = finalise(rows)
    payload["as_of"] = as_of
    payload["asx_unavailable"] = [t for t, _ in au_failed]
    payload["asx_cfo_dropped"] = sorted(
        r["ticker"] for r in payload["names"] + payload["excluded"]
        if r["market"] == "Australia (ASX)"
        and r["flags"]["accruals"]["reason"] == "cash flow could not be derived")

    write(payload)
    write_js(payload)
    write_html(payload)
    log(f"included {len(payload['names'])}, excluded {len(payload['excluded'])}, "
        f"ASX losing accruals to derived-CFO disagreement: "
        f"{len(payload['asx_cfo_dropped'])}")
    return payload


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
