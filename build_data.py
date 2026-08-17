"""Orchestrates both legs into docs/data.json."""

import json

from correlations import matrix
from explain import EXPLANATIONS
from sectors import MIN_PEERS
from returns import load as load_returns
from short_interest import load as load_short_interest
from flags import ALL_FLAGS, goodwill_exceeds_equity
from panel import latest_with_history
from score import coverage_gate, percentile_ranks, composite, MIN_APPLICABLE_FLAGS


try:
    SECTORS = json.load(open("sectors.json", encoding="utf-8"))
except (OSError, ValueError):
    SECTORS = {}

# US only, and absent means absent - never defaulted to zero. "Nobody is short it"
# and "we do not know" must not be drawn as the same point.
SHORT_INTEREST = load_short_interest()

# CONTEXT ONLY. Composite against 1-year return is rho -0.025 - this is not
# evidence the screen predicts anything, and the page must not imply it does.
RETURNS = load_returns()


def levels(latest):
    """LEVELS, not changes - "high" rather than "rising".

    Measured 17/08/2026: level-vs-level pairs correlate at mean |rho| 0.308 while
    change-vs-change pairs manage 0.075. Differencing removes the shared component,
    which is most of what two financial ratios have in common. Five of the six tests
    are changes, so the page had almost nothing left to correlate.

    These are the same quantities the tests are built on, before the difference is
    taken, so a reader can ask "high, rising, or both".
    """
    def ratio(n, d):
        if n is None or not d:
            return None
        return n / d

    etr = None
    if latest.tax_expense is not None and latest.net_income is not None:
        pretax = latest.net_income + latest.tax_expense
        if pretax > 0:
            etr = latest.tax_expense / pretax

    roic = None
    if latest.operating_income is not None and latest.equity:
        invested = latest.equity + (latest.total_debt or 0.0)
        if invested:
            roic = latest.operating_income / invested

    return {
        "receivables_to_revenue": ratio(latest.receivables, latest.revenue),
        "inventory_to_revenue": ratio(latest.inventory, latest.revenue),
        "goodwill_to_assets": ratio(latest.goodwill, latest.assets),
        "stock_comp_to_revenue": ratio(latest.stock_comp, latest.revenue),
        "effective_tax_rate": etr,
        "roic": roic,
        "debt_to_assets": ratio(latest.total_debt, latest.assets),
    }


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
        "sector": SECTORS.get(latest.ticker, {}).get("sector", "Unclassified"),
        "levels": levels(latest),
        "short_interest": SHORT_INTEREST.get(latest.ticker),
        "ret_1y": RETURNS.get(latest.ticker),
        "flags": flags,
        "applicable": applicable,
        "goodwill_exceeds_equity": goodwill_exceeds_equity(latest),
        "operating_income_is_pretax_fallback": latest.operating_income_is_pretax_fallback,
        "tags": latest.tags,
        "events": [],
    }


# How serious a disclosure is, for ordering the disclosed list only. This never
# enters a score - it decides which of two disclosed companies is listed first.
EVENT_SEVERITY = {"restatement": 3, "auditor_change": 2, "late_filing": 1}


def EVENT_WEIGHT(row):
    return max((EVENT_SEVERITY.get(e["kind"], 0) for e in row["events"]), default=0)


def applicable_coverage(rows, flag_key):
    """Fraction of names where the flag applies. This is what the gate tests."""
    if not rows:
        return 0.0
    n = sum(1 for r in rows if r["flags"].get(flag_key, {}).get("applicable"))
    return n / len(rows)


def rank_all(rows):
    """Attach percentile ranks per test, ranked WITHIN SECTOR.

    Sector-relative because ranking everything against the whole universe produced
    structural false positives that say nothing about accounting quality:

    - A REIT must distribute nearly all its income, so it funds itself by issuing
      equity. "Share count rising while returns fall" fires on the business model
      every single year. Prologis reached 4th on the page on exactly this.
    - An acquisitive company's goodwill share rises because it bought something.
      AMD's goodwill flag is the Xilinx deal, not deterioration.

    Ranking within sector does not make either disappear - a REIT issuing far more
    equity than other REITs is still interesting - it stops them being scored against
    a manufacturer that did nothing of the sort.

    A sector with fewer than MIN_PEERS members cannot support its own percentiles, so
    those names fall back to the whole universe and carry `ranked_against: universe`.

    Flag 3's two populations stay separate on top of that: names resolved on the
    pretax fallback are not comparable to names with true operating income.
    """
    by_ticker = {r["ticker"]: r for r in rows}

    groups = {}
    for r in rows:
        groups.setdefault(r.get("sector") or "Unclassified", []).append(r)
    small = [s for s, m in groups.items() if len(m) < MIN_PEERS]
    pool = [r for s in small for r in groups[s]]
    peer_groups = {s: m for s, m in groups.items() if len(m) >= MIN_PEERS}
    if pool:
        peer_groups["__universe__"] = pool
    for r in pool:
        r["ranked_against"] = "universe"
    for s in peer_groups:
        if s != "__universe__":
            for r in peer_groups[s]:
                r["ranked_against"] = s

    for members in peer_groups.values():
        for key in ALL_FLAGS:
            if key == "share_count_roic":
                for fallback in (True, False):
                    subset = {r["ticker"]: r["flags"][key]["value"]
                              for r in members
                              if r["operating_income_is_pretax_fallback"] == fallback}
                    for ticker, rank in percentile_ranks(subset).items():
                        by_ticker[ticker]["flags"][key]["rank"] = rank
                continue
            values = {r["ticker"]: r["flags"][key]["value"] for r in members}
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

    # MEASURED BIAS, now corrected: taking the worst TWO tests rewards having more
    # tests to draw from. Median severity ran 63.6 with three applicable tests against
    # 73.8 with five, so banks, insurers and REITs - which have the fewest applicable
    # tests - were structurally under-flagged, and financials are where accounting
    # quality matters most. Severity is therefore re-expressed as a percentile WITHIN
    # each applicable-count cohort: 90 means "worse than 90% of companies scored on the
    # same number of tests".
    cohorts = {}
    for r in included:
        cohorts.setdefault(r["applicable"], []).append(r)
    for members in cohorts.values():
        raw = {r["ticker"]: r["composite"] for r in members}
        ranked = percentile_ranks(raw)
        for r in members:
            r["severity_raw"] = round(r["composite"], 2)
            if len(members) >= 20:
                r["composite"] = ranked[r["ticker"]]
                r["cohort_ranked"] = True
            else:
                r["cohort_ranked"] = False

    included.sort(key=lambda r: r["composite"], reverse=True)

    # Companies that TOLD the regulator something went wrong get their own list rather
    # than a number blended into the ratio score. They are a different kind of evidence:
    # a restatement is a disclosed fact, not a percentile, and any exchange rate between
    # the two would be invented. Ordered by how serious the disclosure is, then severity.
    disclosed = [r for r in included if r["events"]]
    disclosed.sort(key=lambda r: (EVENT_WEIGHT(r), r["composite"]), reverse=True)

    return {
        "disclosed": disclosed,
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
