"""How much do the six tests agree with each other?

Measured 17/08/2026 across the built universe: mean absolute Spearman 0.058, and the
strongest pair of fifteen is +0.169. They are effectively independent.

That is a finding, not a footnote. It means there is no single underlying "accounting
quality" factor here: a company scores high by being mildly unusual on several unrelated
dimensions, not by exhibiting a coherent syndrome. Which is the strongest support the
page has for "a flag is not a thesis" - the tests do not corroborate one another, and
the matrix says so with a number instead of a disclaimer.
"""

import statistics
from itertools import combinations

FLAG_ORDER = ["accruals", "working_capital", "share_count_roic",
              "goodwill", "tax_rate", "stock_comp"]

SHORT = {
    "accruals": "Accruals",
    "working_capital": "Recv/inv",
    "share_count_roic": "Shares",
    "goodwill": "Goodwill",
    "tax_rate": "Tax",
    "stock_comp": "Stock comp",
}

MIN_PAIRS = 30


def spearman(xs, ys):
    """Rank correlation. Inputs are already percentile ranks, so this is close to
    Pearson on them, but ranking again costs nothing and handles ties in the tails."""
    n = len(xs)
    if n < MIN_PAIRS:
        return None
    rx = {v: i for i, v in enumerate(sorted(xs))}
    ry = {v: i for i, v in enumerate(sorted(ys))}
    x = [rx[v] for v in xs]
    y = [ry[v] for v in ys]
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((i - mx) * (j - my) for i, j in zip(x, y))
    den = (sum((i - mx) ** 2 for i in x) * sum((j - my) ** 2 for j in y)) ** 0.5
    return num / den if den else None


def _both(rows, a, b):
    out = []
    for r in rows:
        fa, fb = r["flags"].get(a, {}), r["flags"].get(b, {})
        if fa.get("applicable") and fb.get("applicable") \
                and fa.get("rank") is not None and fb.get("rank") is not None:
            out.append((fa["rank"], fb["rank"]))
    return out


def matrix(rows):
    """{pairs: [{a,b,rho,n}], mean_abs, strongest} for the page."""
    pairs = []
    for a, b in combinations(FLAG_ORDER, 2):
        both = _both(rows, a, b)
        rho = spearman([p[0] for p in both], [p[1] for p in both])
        if rho is None:
            continue
        pairs.append({"a": a, "b": b, "rho": round(rho, 3), "n": len(both)})
    if not pairs:
        return {"pairs": [], "mean_abs": None, "strongest": None, "order": FLAG_ORDER,
                "short": SHORT}
    strongest = max(pairs, key=lambda p: abs(p["rho"]))
    return {
        "pairs": pairs,
        "mean_abs": round(sum(abs(p["rho"]) for p in pairs) / len(pairs), 3),
        "strongest": strongest,
        "order": FLAG_ORDER,
        "short": SHORT,
    }
