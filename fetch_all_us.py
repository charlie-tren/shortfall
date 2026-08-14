"""One-off driver for the US leg, used to reach the real-data inspection."""
import json, pickle
from edgar import load_ticker_lookup, normalise_ticker, dedupe_by_cik
from fetch_us import sweep, build_records

YEARS = (2024, 2023, 2022, 2021)
lookup = load_ticker_lookup()
names = json.load(open("universe.json"))["names"]
us = [n for n in names if n["market"].startswith("United States")]
us, dropped = dedupe_by_cik(us, lookup)
print(f"US names after dual-class dedupe: {len(us)} (dropped {dropped})")
meta = {lookup[normalise_ticker(n["ticker"])]: n for n in us}
history = {}
for year in YEARS:
    frames = sweep(year)
    for r in build_records(year, frames, meta):
        history.setdefault(r.ticker, []).append(r)
    print(f"  {year} done")
pickle.dump(history, open("us_history.pkl", "wb"))
print("names with history:", len(history))
