"""Print real computed flags for a deliberately varied sample. READ THE OUTPUT.

The sample spans the business models that break naive accounting screens:
a bank and an insurer (no inventory, no conventional ROIC), a software company
(no inventory, heavy stock comp), a manufacturer and a retailer (both should have
full applicability), a miner (heavy assets), and a REIT.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SAMPLE = [
    ("JPM",    "bank, US"),
    ("PGR",    "insurer, US"),
    ("CRM",    "software, US"),
    ("CAT",    "manufacturer, US"),
    ("COST",   "retailer, US"),
    ("NEM",    "miner, US"),
    ("PLD",    "REIT, US"),
    ("ADM",    "restated 2024, US"),
    ("CBA.AX", "bank, AU"),
    ("WES.AX", "conglomerate, AU"),
    ("CSL.AX", "healthcare, AU"),
]

if __name__ == "__main__":
    payload = json.load(open("docs/data.json"))
    rows = {r["ticker"]: r for r in payload["names"] + payload["excluded"]}
    print(f"{'ticker':10s} {'kind':22s} {'appl':>4s} {'composite':>9s}  flags")
    for ticker, kind in SAMPLE:
        r = rows.get(ticker)
        if r is None:
            print(f"{ticker:10s} {kind:22s}  NOT IN DATASET")
            continue
        fired = ", ".join(
            f"{k}={r['flags'][k]['value']:.3f}" if r["flags"][k]["applicable"]
            else f"{k}=n/a({r['flags'][k]['reason']})"
            for k in r["flags"])
        comp = "excluded" if r["composite"] is None else f"{r['composite']:.1f}"
        print(f"{ticker:10s} {kind:22s} {r['applicable']:4d} {comp:>9s}  {fired}")
    print("\ncoverage by flag:")
    for k, v in sorted(payload["coverage"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:6.1%}  {k}")
