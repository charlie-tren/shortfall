"""Orchestrates both legs into docs/data.json."""

import json

from correlations import matrix
from explain import EXPLANATIONS
from flags import ALL_FLAGS, goodwill_exceeds_equity
from panel import latest_with_history
from score import coverage_gate, percentile_ranks, composite, MIN_APPLICABLE_FLAGS


def assemble_name(history):
    """One name's flag results, or None if there is too little history."""
    got = latest_with_history(history, need=2)
    if got is None:
        return None
    latest, priors = got
    flags, applicable = {}, 0
    for key, fn in ALL_FLAGS.items():
        value, ok, reason = fn(latest, priors)
        flags[key] = {"value": value, "applicable": ok, "reason": reason}
        applicable += 1 if ok else 0
    return {
        "ticker": latest.ticker,
        "name": latest.name,
        "market": latest.market,
        "year": latest.year,
        # Size, for the scatter's x axis. Total assets rather than market cap:
        # neither source carries a cap, and assets is the best-covered tag there is.
        "assets": latest.assets,
        "revenue": latest.revenue,
        "flags": flags,
        "applicable": applicable,
        "goodwill_exceeds_equity": goodwill_exceeds_equity(latest),
        "operating_income_is_pretax_fallback": latest.operating_income_is_pretax_fallback,
        "tags": latest.tags,
        "events": [],
    }


def applicable_coverage(rows, flag_key):
    """Fraction of names where the flag applies. This is what the gate tests."""
    if not rows:
        return 0.0
    n = sum(1 for r in rows if r["flags"].get(flag_key, {}).get("applicable"))
    return n / len(rows)


def rank_all(rows):
    """Attach percentile ranks per flag, ranked only among applicable names.

    Flag 3's two populations are ranked SEPARATELY: names resolved on the pretax
    fallback are not comparable to names with true operating income.
    """
    by_ticker = {r["ticker"]: r for r in rows}
    for key in ALL_FLAGS:
        if key == "share_count_roic":
            for fallback in (True, False):
                subset = {r["ticker"]: r["flags"][key]["value"]
                          for r in rows
                          if r["operating_income_is_pretax_fallback"] == fallback}
                for ticker, rank in percentile_ranks(subset).items():
                    by_ticker[ticker]["flags"][key]["rank"] = rank
            continue
        values = {r["ticker"]: r["flags"][key]["value"] for r in rows}
        for ticker, rank in percentile_ranks(values).items():
            by_ticker[ticker]["flags"][key]["rank"] = rank
    return rows


def finalise(rows):
    """Apply the gate, compute equal-weight composites, split out the excluded."""
    coverage = {k: applicable_coverage(rows, k) for k in ALL_FLAGS}
    warnings = coverage_gate(coverage)

    ranked = rank_all(rows)
    included, excluded = [], []
    for r in ranked:
        scores = {k: r["flags"][k].get("rank") for k in ALL_FLAGS
                  if r["flags"][k]["applicable"]}
        r["composite"] = composite(scores, weights=None, enforce_minimum=True)
        if r["composite"] is None:
            r["excluded_reason"] = (
                f"only {r['applicable']} of 6 flags applicable, "
                f"minimum is {MIN_APPLICABLE_FLAGS}"
            )
            excluded.append(r)
        else:
            included.append(r)

    included.sort(key=lambda r: r["composite"], reverse=True)
    return {
        "names": included,
        "excluded": excluded,
        "coverage": coverage,
        "coverage_warnings": warnings,
        "explanations": EXPLANATIONS,
        "correlations": matrix(included),
    }


def write(payload, path="docs/data.json"):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)


def write_js(payload, path="docs/data.js"):
    """A JS global, so the page works from file:// as well as over http."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("window.SHORTFALL = " + json.dumps(payload) + ";\n")
