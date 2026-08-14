"""The ASX leg. EDGAR is US-only, so Australia comes from Yahoo.

MEASURED WEAKNESS, 14/08/2026: ASX cash flow statements returned by yfinance carry
NO `Operating Cash Flow` row - only Free Cash Flow, Investing, Financing and Changes
In Cash. Verified on WES.AX and CSL.AX. Since flag 1 is the strongest flag and needs
CFO, CFO is DERIVED by two independent routes and used only when they agree.

It is never guessed. A name whose routes disagree loses flag 1 and is counted in the
disclosure on the page.
"""

import warnings

import yfinance as yf

from panel import Record

TOLERANCE_FRACTION_OF_ASSETS = 0.02


def derive_cfo(fcf, capex, change_in_cash, investing, financing, assets):
    """(value, status). status is agreed | disagree | single_route | no_route.

    Route A: CFO = free cash flow + capex   (capex is reported negative)
    Route B: CFO = change in cash - investing - financing
    """
    route_a = None
    if fcf is not None and capex is not None:
        route_a = fcf - capex

    route_b = None
    if change_in_cash is not None and investing is not None and financing is not None:
        route_b = change_in_cash - investing - financing

    if route_a is None and route_b is None:
        return None, "no_route"
    if route_a is None or route_b is None:
        return None, "single_route"

    if assets and abs(route_a - route_b) <= TOLERANCE_FRACTION_OF_ASSETS * abs(assets):
        return route_a, "agreed"
    return None, "disagree"


def _row(df, *names):
    """First matching row label, or None. yfinance label sets vary by market."""
    if df is None or getattr(df, "empty", True):
        return None
    for n in names:
        if n in df.index:
            return df.loc[n]
    return None


def _at(df, col, names):
    row = _row(df, *names)
    if row is None or col not in row.index:
        return None
    value = row[col]
    if value is None or value != value:      # NaN check
        return None
    return float(value)


# yfinance row labels, in preference order, mirroring the EDGAR chains.
BALANCE_ROWS = {
    "assets":       ("Total Assets",),
    "equity":       ("Stockholders Equity", "Total Equity Gross Minority Interest"),
    "goodwill":     ("Goodwill", "Goodwill And Other Intangible Assets"),
    "receivables":  ("Accounts Receivable", "Receivables", "Gross Accounts Receivable"),
    "inventory":    ("Inventory",),
    "total_debt":   ("Total Debt", "Long Term Debt"),
}
INCOME_ROWS = {
    "revenue":          ("Total Revenue", "Operating Revenue"),
    "net_income":       ("Net Income", "Net Income Common Stockholders"),
    "tax_expense":      ("Tax Provision",),
    "diluted_shares":   ("Diluted Average Shares",),
    "operating_income": ("Operating Income", "Total Operating Income As Reported"),
}
CASHFLOW_ROWS = {
    "stock_comp": ("Stock Based Compensation",),
}


def load(ticker):
    """Raw yfinance statements for one ASX name."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = yf.Ticker(ticker)
        return {"balance": t.balance_sheet, "cashflow": t.cashflow, "income": t.income_stmt}


def records_from_statements(ticker, name, statements):
    """Panel records for one ASX name, newest year first."""
    bs, inc, cf = statements["balance"], statements["income"], statements["cashflow"]
    if bs is None or getattr(bs, "empty", True):
        return []
    out = []
    for col in bs.columns:
        r = Record(ticker=ticker, name=name, market="Australia (ASX)", year=int(col.year))
        for field, names in BALANCE_ROWS.items():
            value = _at(bs, col, names)
            if value is not None:
                setattr(r, field, value)
        for field, names in INCOME_ROWS.items():
            value = _at(inc, col, names)
            if value is not None:
                setattr(r, field, value)
        for field, names in CASHFLOW_ROWS.items():
            value = _at(cf, col, names)
            if value is not None:
                setattr(r, field, value)
        r.cfo, r.cfo_status = derive_cfo(
            fcf=_at(cf, col, ("Free Cash Flow",)),
            capex=_at(cf, col, ("Capital Expenditure", "Purchase Of PPE")),
            change_in_cash=_at(cf, col, ("Changes In Cash",)),
            investing=_at(cf, col, ("Investing Cash Flow",)),
            financing=_at(cf, col, ("Financing Cash Flow",)),
            assets=r.assets,
        )
        # The ASX leg has no XBRL tag names, so record the source for traceability.
        r.tags = {"_source": "yfinance"}
        out.append(r)
    return out
