"""ASX leg driver. ~200 yfinance calls, so it runs separately from the US sweep.

NOTE ON CURRENCY: some ASX filers report in USD (CSL, BHP) and some in AUD (WES).
Every flag is a RATIO, so the mix is harmless - but nothing here may ever present
a raw currency amount without resolving it first.
"""
import json, pickle
from asx import load, records_from_statements

names = [n for n in json.load(open("universe.json"))["names"]
         if n["market"] == "Australia (ASX)"]
history, failed, tally = {}, [], {}
for i, n in enumerate(names, 1):
    try:
        recs = records_from_statements(n["ticker"], n["name"], load(n["ticker"]))
    except Exception as exc:
        failed.append((n["ticker"], str(exc)[:60])); continue
    if not recs:
        failed.append((n["ticker"], "no records")); continue
    history[n["ticker"]] = recs
    for r in recs:
        tally[r.cfo_status] = tally.get(r.cfo_status, 0) + 1
    if i % 50 == 0:
        print(f"  {i}/{len(names)}", flush=True)
pickle.dump(history, open("asx_history.pkl", "wb"))
print("ASX names with history:", len(history))
print("derived-CFO status tally:", tally)
print("failed:", len(failed), failed[:10])
