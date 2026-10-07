"""US leg: frames sweep, then a companyfacts fallback for the residue only.

The sweep is roughly 10 calls per period rather than 500. The fallback is per
company, so it must only ever run for names the sweep missed - hence the residue
guard.
"""

from edgar import frame, filer_ciks
from panel import Record
from tags import CHAINS, KIND, UNIT, INSTANT

CONCEPT_TO_FIELD = {
    "Revenue": "revenue", "NetIncome": "net_income", "CFO": "cfo",
    "Assets": "assets", "Equity": "equity", "Goodwill": "goodwill",
    "Receivables": "receivables", "Inventory": "inventory",
    "TaxExpense": "tax_expense", "StockComp": "stock_comp",
    "DilutedShares": "diluted_shares", "OperatingIncome": "operating_income",
    "TotalDebt": "total_debt",
}

MAX_RESIDUE_FRACTION = 0.15


def periods_for(year):
    """(duration period, instant period) for a calendar year."""
    return f"CY{year}", f"CY{year}Q4I"


def sweep(year, log=None):
    """{period: {tag: {cik: value}}} for every tag in every chain."""
    duration, instant = periods_for(year)
    out = {duration: {}, instant: {}}
    for concept, chain in CHAINS.items():
        period = instant if KIND[concept] == INSTANT else duration
        unit = UNIT.get(concept, "USD")
        for tag in chain:
            if tag not in out[period]:
                out[period][tag] = frame(tag, unit, period)
                if log:
                    log(f"  {period} {tag}: {len(out[period][tag])} filers")
    return out


def resolve_filers(concept, ciks, frames):
    """resolve() across a company's CIKs, TAG first and CIK second.

    The other order splices two tags into one series. Exxon's old CIK tags both
    AccountsReceivableNetCurrent (35.3bn) and the broader ReceivablesNetCurrent
    (43.7bn); the new one carries only the broader tag. Successor-first took 2025
    from one and 2024 from the other and showed receivables up 26% on a year they
    rose 2%. Walking the chain first keeps every year on the same tag.
    """
    for tag in CHAINS[concept]:
        got = frames.get(tag, {})
        for cik in ciks:
            if cik in got:
                return got[cik], tag
    return None, None


def build_records(year, frames, meta):
    """Panel records for every CIK in `meta`."""
    duration, instant = periods_for(year)
    records = []
    for cik, m in meta.items():
        r = Record(ticker=m["ticker"], name=m["name"], market=m["market"], year=year)
        for concept, field in CONCEPT_TO_FIELD.items():
            period = instant if KIND[concept] == INSTANT else duration
            value, tag = resolve_filers(concept, filer_ciks(cik), frames.get(period, {}))
            if value is not None:
                setattr(r, field, value)
                r.tags[concept] = tag
        records.append(r)
    return records


def residue(records, concept):
    """Tickers missing a concept. Used to decide whether a fallback pass is sane."""
    field = CONCEPT_TO_FIELD[concept]
    return [r.ticker for r in records if getattr(r, field) is None]


def check_residue(records, concept):
    """Frames should not miss a large slice. A big residue means a broken sweep.

    Guard exists so a bug never triggers 500 per-company calls.
    """
    missing = residue(records, concept)
    if len(missing) > MAX_RESIDUE_FRACTION * len(records):
        raise RuntimeError(
            f"{concept}: {len(missing)}/{len(records)} names missing from the frames "
            f"sweep, above the {MAX_RESIDUE_FRACTION:.0%} guard. Fix the sweep rather "
            f"than falling back per company."
        )
    return missing
