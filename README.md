# Shortfall

Six tests of accounting quality, run across the S&P 500 and the S&P/ASX 200.

**https://charlietrenorden.com/shortfall/**

In progress. The numbers are real; the presentation is not finished.

## What it does

Every company is scored on six ratio flags, and US companies additionally carry three
event badges taken from filing metadata. The reader can reweight the six flags and the
ranking updates live, always against the equal-weight baseline.

A flag is a question, not an answer. Every flag on the page is published alongside a
plain statement of why it can be perfectly innocent.

| Flag | What it measures |
|---|---|
| Accruals vs cash | Reported profit less cash generated, over average assets |
| Receivables and inventory | Working capital growing faster than sales |
| Share count vs returns | Dilution while return on invested capital falls |
| Goodwill | Goodwill rising as a share of total assets |
| Effective tax rate | Volatility in the tax rate |
| Stock compensation | Share-based pay rising as a share of revenue |
| Filing events (badge, US only) | Restatement, auditor change or late filing in 24 months |

Filing events are badges, not weighted components. An SEC Item 4.02 is a categorical
fact, and averaging it into a composite dilutes the only unarguable signal on the page.

## Data

- **United States** - SEC EDGAR XBRL frames. One call returns one tag for every filer,
  so the whole panel is roughly 200 calls rather than one per company. No document
  parsing, no language model: frames are numeric and filing events are metadata.
- **Australia** - Yahoo Finance. ASX cash flow statements carry no operating cash flow
  row, so it is derived by two independent routes and used only where they agree.

## Known limitations

Stated on the page, not buried here:

- **The screen has not been backtested.** Nobody knows whether these flags predict
  anything.
- The three event flags are **US only**.
- Inventory is scaled by revenue, not cost of sales, which is not reliably tagged.
- Companies with fewer than three applicable flags are listed separately, not ranked.
- Not applicable is shown as not applicable, never as a pass. A bank has no inventory.

## Running it

```
pip install -r requirements.txt
python build_universe.py     # refresh index membership from Wikipedia
python run_build.py          # fetch, compute, render into docs/
python -m pytest tests/      # 94 tests
```

`tests/inspect_real.py` prints computed flags for a deliberately varied sample, and
`tests/fairness_check.py` is the pre-publish gate over the top of the ranking. Both are
meant to be read, not just run - three real defects in this repo were invisible to the
unit tests and were caught by reading actual output.

Edit the generator, never the built HTML: a scheduled run overwrites `docs/`.

## Licence

Figures are as filed with the SEC and as published by Yahoo Finance. This is not
investment advice and not a recommendation about any company.
