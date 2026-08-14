"""The three filing-event signals, from submissions metadata.

No document parsing. `items` on an 8-K is a structured comma-separated field, and
the form type is a string. Verified 14/08/2026: NVDA returns 5.02 and 5.07, XOM
returns "2.02,7.01".

These are qualitatively different from the ratio flags: they are facts the company
itself disclosed, not inferences drawn about it. That is why they are badges rather
than weighted components.
"""

from datetime import date

ITEM_KINDS = {
    "4.02": "restatement",     # Non-reliance on previously issued financial statements
    "4.01": "auditor_change",  # Change in certifying accountant
}
LATE_FORMS = {"NT 10-K", "NT 10-Q"}

LABELS = {
    "restatement": "Restated accounts",
    "auditor_change": "Auditor changed",
    "late_filing": "Filed late",
}


def _months_between(earlier, later):
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def extract_events(recent, as_of, months=24):
    """[{kind, date, form}] within the lookback window.

    `recent` is submissions.json -> filings -> recent: parallel arrays.
    """
    as_of = date.fromisoformat(as_of)
    forms = recent.get("form", [])
    items = recent.get("items", [""] * len(forms))
    dates = recent.get("filingDate", [])
    out = []
    for i, form in enumerate(forms):
        try:
            filed = date.fromisoformat(dates[i])
        except (IndexError, ValueError):
            continue
        if _months_between(filed, as_of) > months:
            continue
        if form in LATE_FORMS:
            out.append({"kind": "late_filing", "date": dates[i], "form": form})
            continue
        raw = items[i] if i < len(items) else ""
        for code in [c.strip() for c in (raw or "").split(",") if c.strip()]:
            if code in ITEM_KINDS:
                out.append({"kind": ITEM_KINDS[code], "date": dates[i], "form": form})
    return out


def fetch_events(cik, as_of, get_submissions, months=24):
    """Wrapper taking an injected fetcher, so tests never hit the network."""
    return extract_events(get_submissions(cik)["filings"]["recent"], as_of, months)
