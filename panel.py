"""One normalised record shape for both markets.

flags.py consumes only this, so it never branches on data source. `tags` records
WHICH tag satisfied each concept, which is what lets the page trace any number back
to the filing line it came from - and lets flag 3 tell true operating income from
the pretax fallback.
"""

from dataclasses import dataclass, field
from typing import Optional

from tags import TRUE_OPERATING_INCOME_TAG


@dataclass
class Record:
    ticker: str
    name: str
    market: str
    year: int
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    cfo: Optional[float] = None
    cfo_status: str = "direct"        # ASX only: agreed | disagree | single_route
    assets: Optional[float] = None
    equity: Optional[float] = None
    goodwill: Optional[float] = None
    receivables: Optional[float] = None
    inventory: Optional[float] = None
    tax_expense: Optional[float] = None
    stock_comp: Optional[float] = None
    diluted_shares: Optional[float] = None
    operating_income: Optional[float] = None
    total_debt: Optional[float] = None
    tags: dict = field(default_factory=dict)   # concept -> tag that satisfied it

    @property
    def operating_income_is_pretax_fallback(self):
        """True when operating income came from a PRETAX tag.

        Pretax income sits below interest and other non-operating items, so a ROIC
        built on it is not comparable to one built on true operating income. The
        two populations are ranked separately rather than silently mixed.

        A record with no operating income at all is not a fallback - it is absent.
        """
        used = self.tags.get("OperatingIncome")
        if used is None:
            return False
        return used != TRUE_OPERATING_INCOME_TAG


def years_available(records):
    return sorted({r.year for r in records}, reverse=True)


def latest_with_history(records, need=2):
    """(latest_record, [prior records newest first]) or None if too short.

    A company with fewer than `need` years cannot be assessed on trend, and scoring
    it on a single observation would be the easiest way to be unfair to a named
    business.
    """
    ordered = sorted(records, key=lambda r: r.year, reverse=True)
    if len(ordered) < need:
        return None
    return ordered[0], ordered[1:]
