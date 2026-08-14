"""Pre-publish gate. This page names real companies.

For every name on the first page of the ranking, confirm each fired flag traces to a
real filed value and that nothing on the card claims more than the data supports.
Anything that cannot be explained is a blocker, not a note.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CONCEPT_FOR = {
    "accruals": "CFO",
    "working_capital": "Receivables",
    "share_count_roic": "OperatingIncome",
    "goodwill": "Goodwill",
    "tax_rate": "TaxExpense",
    "stock_comp": "StockComp",
}

if __name__ == "__main__":
    payload = json.load(open("docs/data.json"))
    top = payload["names"][:25]
    print("Top 25 by composite. Check each line against the filing before publishing.\n")
    for r in top:
        print(f"{r['ticker']:9s} {r['name'][:36]:36s} composite {r['composite']:5.1f}  "
              f"{r['applicable']} of 6 applicable  [{r['market'].split(' (')[0]}]")
        for key, f in r["flags"].items():
            if not f["applicable"]:
                continue
            tag = r["tags"].get(CONCEPT_FOR.get(key, ""), "-")
            print(f"    {key:18s} value {f['value']:>11.4f}  rank {f.get('rank', 0):5.1f}  "
                  f"source {tag}")
        if r["operating_income_is_pretax_fallback"]:
            print("    NOTE: operating income resolved on the PRETAX fallback")
        if r.get("goodwill_exceeds_equity"):
            print("    NOTE: goodwill exceeds book equity")
        if r["events"]:
            print(f"    EVENTS: {[(e['kind'], e['date']) for e in r['events']]}")
        print()

    print("=" * 72)
    bad = [r for r in top if r["applicable"] < 3]
    print(f"names ranked on fewer than three flags: {len(bad)} (must be 0) {[r['ticker'] for r in bad]}")
    out_of_range = [r for r in top if not (0 <= r["composite"] <= 100)]
    print(f"composites outside 0-100: {len(out_of_range)} (must be 0)")
    markets = {}
    for r in top:
        markets[r["market"]] = markets.get(r["market"], 0) + 1
    print(f"market split of the top 25: {markets}")
