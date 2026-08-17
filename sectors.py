"""Sector for every company, so tests can be ranked against peers.

WHY THIS EXISTS: ranking every company against the whole universe produces
structural false positives that have nothing to do with accounting quality.

- A REIT must distribute nearly all its income, so it funds itself by issuing
  equity. "Share count rising while returns fall" fires on the business model,
  every year, for every REIT. Prologis sat 4th on the page for exactly this.
- An acquisitive company's goodwill rises as a share of assets because it bought
  something. AMD's goodwill flag is the Xilinx deal.

Neither is a signal that the accounts are deteriorating. Ranking within sector
does not make them disappear - it stops them being compared to a manufacturer
that did nothing of the sort.

US sector comes from the SIC code already present in the submissions payload we
fetch for filing events, so it costs no extra request. Australia comes from
Yahoo's sector field.
"""

# SIC major groups -> the bucket used for peer ranking. Coarse on purpose: the
# point is separating business models whose ratios behave differently, not
# building a taxonomy.
def sector_from_sic(sic):
    try:
        code = int(sic)
    except (TypeError, ValueError):
        return "Unclassified"
    if code == 6798:
        return "Real estate"
    if 6000 <= code <= 6499 or 6700 <= code <= 6799:
        return "Financials"
    if 6500 <= code <= 6599:
        return "Real estate"
    if 4900 <= code <= 4999:
        return "Utilities"
    if 1000 <= code <= 1499:
        return "Resources"
    if 2830 <= code <= 2836 or 8000 <= code <= 8099:
        return "Healthcare"
    if 7370 <= code <= 7379 or 3570 <= code <= 3579 or 3670 <= code <= 3679:
        return "Technology"
    # Measured gap: 57 names were landing in "Other", the largest groups being
    # business services (73xx), hotels (70xx), drug wholesale (51xx), contract
    # research (873x) and construction (15xx-17xx). Each has a natural home.
    if 7300 <= code <= 7399:
        return "Technology"          # 73xx is software and business services
    if 8730 <= code <= 8739:
        return "Healthcare"          # contract research
    if 7000 <= code <= 7099 or 5800 <= code <= 5899 or 7900 <= code <= 7999:
        return "Consumer"            # hotels, eating places, entertainment
    if 5000 <= code <= 5199:
        return "Consumer"            # wholesale
    if 1500 <= code <= 1799:
        return "Industrials"         # construction and trades
    if 8200 <= code <= 8299 or 8700 <= code <= 8749:
        return "Industrials"         # education, engineering and management services
    if 2000 <= code <= 3999:
        return "Industrials"
    if 5200 <= code <= 5999:
        return "Consumer"
    if 4000 <= code <= 4899:
        return "Transport & comms"
    return "Other"


# Yahoo's sector strings -> the same buckets.
YAHOO_SECTOR = {
    "Real Estate": "Real estate",
    "Financial Services": "Financials",
    "Utilities": "Utilities",
    "Basic Materials": "Resources",
    "Energy": "Resources",
    "Healthcare": "Healthcare",
    "Technology": "Technology",
    "Communication Services": "Transport & comms",
    "Industrials": "Industrials",
    "Consumer Cyclical": "Consumer",
    "Consumer Defensive": "Consumer",
}


def sector_from_yahoo(name):
    return YAHOO_SECTOR.get(name, "Other" if name else "Unclassified")


# Below this many companies a sector cannot support its own percentile ranking,
# so its members fall back to the whole universe and the card says so.
MIN_PEERS = 12
