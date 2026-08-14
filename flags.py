"""The six weighted flags.

Every flag returns (value, applicable, reason). Higher value means more
deteriorated. NOT APPLICABLE IS A FIRST-CLASS OUTCOME: a bank has no inventory and
a company with no goodwill has no goodwill flag. Treating those as zero would show
a clean bill of health where no test was run.
"""

import statistics

ETR_MIN, ETR_MAX = -1.0, 1.5


def _na(reason):
    return (None, False, reason)


def _ratio(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return numerator / denominator


def flag_accruals(latest, priors):
    """Sloan accruals: (net income - CFO) / average total assets."""
    if latest.cfo is None:
        if latest.cfo_status in ("disagree", "single_route", "no_route"):
            return _na("cash flow could not be derived")
        return _na("no cash flow figure")
    if latest.net_income is None:
        return _na("no net income figure")
    if latest.assets is None:
        return _na("no total assets figure")
    prior_assets = priors[0].assets if priors else None
    avg_assets = (latest.assets + prior_assets) / 2 if prior_assets else latest.assets
    if not avg_assets:
        return _na("total assets is zero")
    return ((latest.net_income - latest.cfo) / avg_assets, True, "")


def flag_working_capital(latest, priors):
    """Receivables and inventory growing faster than revenue.

    Inventory is scaled by REVENUE, not COGS, which is the textbook denominator.
    GrossProfit covers only 37.1% of the universe on a single tag, so COGS cannot be
    resolved reliably. The consequence - the ratio moves with gross margin too - is
    stated in the explanation table on the page.
    """
    if not priors:
        return _na("no prior year")
    prior = priors[0]
    changes = []
    for field in ("receivables", "inventory"):
        now = _ratio(getattr(latest, field), latest.revenue)
        was = _ratio(getattr(prior, field), prior.revenue)
        if now is not None and was:
            changes.append(now / was - 1.0)
    if not changes:
        return _na("no receivables or inventory reported")
    return (max(changes), True, "")


def _etr(record):
    """Effective tax rate, reconstructing pretax income from two tags we already need.

    PRETAX MUST BE POSITIVE. A loss-maker with a small tax charge produces a small
    NEGATIVE rate that sits happily inside the sanity bounds - -500 of net income
    against 10 of tax gives -2%, which looks like a perfectly ordinary number and is
    not a rate at all. Ranking that against profitable companies compares things that
    are not comparable, so it returns None instead.
    """
    if record.tax_expense is None or record.net_income is None:
        return None
    pretax = record.net_income + record.tax_expense
    if pretax <= 0:
        return None
    return record.tax_expense / pretax


def _roic(record):
    """(roic, used_debt). Falls back to equity-only invested capital.

    Excluding debt OVERSTATES ROIC, which makes the flag LESS likely to fire. That is
    the safe direction to fail in on a page that names companies.
    """
    if record.operating_income is None or record.equity is None:
        return None, False
    etr = _etr(record)
    nopat = record.operating_income * (1 - etr) if etr is not None else record.operating_income
    used_debt = record.total_debt is not None
    invested = record.equity + (record.total_debt or 0.0)
    if not invested:
        return None, used_debt
    return nopat / invested, used_debt


def flag_share_count_vs_roic(latest, priors):
    """Issuing stock is not a flag. Issuing stock while returns fall is."""
    if not priors:
        return _na("no prior year")
    oldest = priors[-1]
    if latest.diluted_shares is None or not oldest.diluted_shares:
        return _na("no diluted share count")
    roic_now, used_debt_now = _roic(latest)
    roic_then, used_debt_then = _roic(oldest)
    if roic_now is None or roic_then is None:
        return _na("return on invested capital could not be computed")
    share_growth = latest.diluted_shares / oldest.diluted_shares - 1.0
    roic_change = roic_now - roic_then
    value = share_growth * abs(roic_change) if (share_growth > 0 and roic_change < 0) else 0.0
    reason = "" if (used_debt_now and used_debt_then) else "invested capital excludes debt"
    return (value, True, reason)


def flag_goodwill(latest, priors):
    """Goodwill rising as a share of assets."""
    if latest.goodwill is None:
        return _na("no goodwill reported")
    if not priors:
        return _na("no prior year")
    oldest = priors[-1]
    now = _ratio(latest.goodwill, latest.assets)
    was = _ratio(oldest.goodwill, oldest.assets)
    if now is None or was is None:
        return _na("no total assets figure")
    return (now - was, True, "")


def goodwill_exceeds_equity(record):
    """Surfaced on the card: a full impairment would wipe out book equity."""
    if record.goodwill is None or record.equity is None:
        return False
    return record.goodwill > record.equity


def flag_tax_rate(latest, priors):
    """Volatile or sharply falling effective tax rate.

    Bounds exist because loss-making years make the ratio meaningless rather than
    interesting.
    """
    series = []
    for r in [latest] + list(priors):
        etr = _etr(r)
        if etr is None or not (ETR_MIN <= etr <= ETR_MAX):
            if r is latest:
                return _na("effective tax rate not meaningful")
            continue
        series.append(etr)
    if len(series) < 2:
        return _na("not enough tax history")
    return (statistics.pstdev(series), True, "")


def flag_stock_comp(latest, priors):
    """Share-based compensation rising as a share of revenue."""
    if latest.stock_comp is None:
        return _na("no share-based compensation reported")
    if not priors:
        return _na("no prior year")
    oldest = priors[-1]
    now = _ratio(latest.stock_comp, latest.revenue)
    was = _ratio(oldest.stock_comp, oldest.revenue)
    if now is None or was is None:
        return _na("no revenue figure")
    return (now - was, True, "")


ALL_FLAGS = {
    "accruals": flag_accruals,
    "working_capital": flag_working_capital,
    "share_count_roic": flag_share_count_vs_roic,
    "goodwill": flag_goodwill,
    "tax_rate": flag_tax_rate,
    "stock_comp": flag_stock_comp,
}
