"""Concept -> ordered tag chain.

Single-tag coverage badly understates what EDGAR holds, because filers fragment
across synonymous tags. Revenue is the proof: `Revenues` alone covers 47.3% of the
S&P 500, the four-tag union covers 97.4%. All figures measured 14/08/2026.

ORDER MATTERS. For OperatingIncome it is also a semantic downgrade: entries 2 and 3
are PRETAX income, which sits below interest and other non-operating items. Anything
consuming this must branch on the returned tag name, not just the value.
"""

INSTANT = "instant"
DURATION = "duration"

CHAINS = {
    "Revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ],
    "NetIncome": ["NetIncomeLoss"],
    "CFO": ["NetCashProvidedByUsedInOperatingActivities"],
    "Assets": ["Assets"],
    # 93.8% -> 99.8%. The fallback INCLUDES non-controlling interests, so it is
    # slightly larger than parent-only equity. For invested capital that is arguably
    # the better measure anyway, and it is the safe direction: a larger denominator
    # lowers ROIC, which makes flag 3 less likely to fire.
    # Caterpillar and Archer-Daniels-Midland both need it - neither tags the
    # parent-only figure at all, which left them with no ROIC before this.
    "Equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "Goodwill": ["Goodwill"],
    "TaxExpense": ["IncomeTaxExpenseBenefit"],
    # 81.4% -> 93.8%. `ShareBasedCompensation` is the cash-flow-statement add-back;
    # plenty of filers only tag the income-statement expense instead. Caterpillar,
    # Progressive and Newmont all showed "no share-based compensation reported"
    # before the fallback, which is plainly wrong for companies that all pay in stock.
    "StockComp": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "DilutedShares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "Receivables": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
        "AccountsReceivableGrossCurrent",
    ],
    "Inventory": ["InventoryNet", "InventoryGross"],
    "OperatingIncome": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "TotalDebt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "DebtLongtermAndShorttermCombinedAmount",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
}

# The first tag of the OperatingIncome chain is true operating income; the rest are
# pretax income. flags.py ranks the two populations separately rather than mixing them.
TRUE_OPERATING_INCOME_TAG = "OperatingIncomeLoss"

# Whether the concept is a point-in-time (balance sheet) or a period (flow) figure.
KIND = {
    "Revenue": DURATION, "NetIncome": DURATION, "CFO": DURATION,
    "TaxExpense": DURATION, "StockComp": DURATION, "OperatingIncome": DURATION,
    "DilutedShares": DURATION,
    "Assets": INSTANT, "Equity": INSTANT, "Goodwill": INSTANT,
    "Receivables": INSTANT, "Inventory": INSTANT, "TotalDebt": INSTANT,
}

UNIT = {"DilutedShares": "shares"}  # everything else is USD

# Tags whose absence means the concept does not apply, rather than data missing.
# A company with no goodwill has no goodwill; it has not failed to report it.
ABSENCE_MEANS_NA = {"Goodwill", "Inventory", "Receivables"}


def resolve(concept, cik, frames):
    """(value, tag_used) for one company, or (None, None).

    `frames` is {tag: {cik: value}} already fetched for the relevant period.
    """
    for tag in CHAINS[concept]:
        got = frames.get(tag, {})
        if cik in got:
            return got[cik], tag
    return None, None
