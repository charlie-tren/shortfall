"""Is there a COMBINATION of these variables that explains short interest or return?

Pairwise correlation cannot answer this - it tests one variable at a time. This fits
each target on every predictor at once and reports how much of the variation is
explained, against the honest benchmark: size alone.

Everything is rank-transformed first, so a single outlier cannot manufacture a fit,
and the result is comparable across variables on wildly different scales.
"""
import json
import math
import statistics


def ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    for r, i in enumerate(order):
        out[i] = r / max(len(vals) - 1, 1)
    return out


def ols(X, y):
    """Least squares by normal equations with ridge damping, no numpy."""
    n, k = len(X), len(X[0])
    XtX = [[sum(X[r][i] * X[r][j] for r in range(n)) + (1e-6 if i == j else 0)
            for j in range(k)] for i in range(k)]
    Xty = [sum(X[r][i] * y[r] for r in range(n)) for i in range(k)]
    # gaussian elimination
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            continue
        for r in range(k):
            if r == c:
                continue
            f = M[r][c] / M[c][c]
            for j in range(c, k + 1):
                M[r][j] -= f * M[c][j]
    beta = [M[i][k] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(k)]
    fit = [sum(X[r][i] * beta[i] for i in range(k)) for r in range(n)]
    my = statistics.mean(y)
    ss_res = sum((y[r] - fit[r]) ** 2 for r in range(n))
    ss_tot = sum((v - my) ** 2 for v in y)
    return beta, (1 - ss_res / ss_tot if ss_tot else 0.0)


def adj_r2(r2, n, k):
    return 1 - (1 - r2) * (n - 1) / max(n - k - 1, 1)


P = json.load(open("docs/data.json"))
rows = P["names"]


def flag(k):
    return lambda r: (r["flags"][k]["value"] if r["flags"][k]["applicable"] else None)


def lvl(k):
    return lambda r: (r.get("levels") or {}).get(k)


PREDICTORS = {
    "log assets": lambda r: math.log10(r["assets"]) if r.get("assets") else None,
    "revenue/assets": lambda r: (r["revenue"] / r["assets"]) if r.get("revenue") and r.get("assets") else None,
    "accruals (level)": flag("accruals"),
    "chg receivables/inv": flag("working_capital"),
    "chg goodwill": flag("goodwill"),
    "chg stock comp": flag("stock_comp"),
    "tax volatility": flag("tax_rate"),
    "dilution x roic fall": flag("share_count_roic"),
    "recv/revenue": lvl("receivables_to_revenue"),
    "inventory/revenue": lvl("inventory_to_revenue"),
    "goodwill/assets": lvl("goodwill_to_assets"),
    "stockcomp/revenue": lvl("stock_comp_to_revenue"),
    "eff tax rate": lvl("effective_tax_rate"),
    "roic": lvl("roic"),
    "debt/assets": lvl("debt_to_assets"),
}

TARGETS = {
    "short interest": lambda r: r.get("short_interest"),
    "12-month return": lambda r: r.get("ret_1y"),
}


def run(target_name, target_fn):
    names = list(PREDICTORS)
    data = []
    for r in rows:
        y = target_fn(r)
        xs = [PREDICTORS[n](r) for n in names]
        if y is None or any(v is None for v in xs):
            continue
        data.append((xs, y))
    if len(data) < 60:
        print(f"\n{target_name}: only {len(data)} complete rows, skipping")
        return
    n = len(data)
    cols = [ranks([d[0][i] for d in data]) for i in range(len(names))]
    y = ranks([d[1] for d in data])

    print(f"\n=== {target_name} ===  complete rows: {n}")
    # benchmark: size alone
    X1 = [[1.0, cols[0][r]] for r in range(n)]
    _, r2_size = ols(X1, y)
    print(f"  size alone                 R2 {r2_size:6.3f}")

    Xall = [[1.0] + [cols[i][r] for i in range(len(names))] for r in range(n)]
    beta, r2_all = ols(Xall, y)
    print(f"  everything ({len(names):2d} vars)        R2 {r2_all:6.3f}   adjusted {adj_r2(r2_all, n, len(names)):6.3f}")

    Xnos = [[1.0] + [cols[i][r] for i in range(1, len(names))] for r in range(n)]
    _, r2_nosize = ols(Xnos, y)
    print(f"  everything EXCEPT size     R2 {r2_nosize:6.3f}")
    print(f"  --> the accounting variables add {r2_all - r2_size:+.3f} over size alone")

    print("  largest standardised coefficients:")
    ordered = sorted(zip(names, beta[1:]), key=lambda t: -abs(t[1]))[:6]
    for nm, b in ordered:
        print(f"    {b:+7.3f}  {nm}")


for t, fn in TARGETS.items():
    run(t, fn)

print("\nNOTE: R2 here is IN-SAMPLE and on a single cross-section. It measures fit,")
print("not predictive power. A high number would need testing out of sample before")
print("it meant anything at all.")
