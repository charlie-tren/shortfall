"""Copy for the explanation table. DRAFT - Charlie rewrites this, per BRIEF.md.

The fourth column is not a hedge. Every one of these flags has a benign reading, and
publishing it beside the flag is both the honest version and what makes the page
defensible when it names a real company.
"""

EXPLANATIONS = [
    {
        "key": "accruals",
        "flag": "Accruals vs cash",
        "measures": "The gap between reported profit and the cash actually collected, scaled by assets.",
        "deterioration": "Profit that never turns into cash is the oldest warning in accounting. The gap has to close eventually, usually by profit falling.",
        "innocent": "A company growing quickly funds working capital before it collects. Fast growth and early-stage contracts both widen the gap without anything being wrong.",
    },
    {
        "key": "working_capital",
        "flag": "Receivables and inventory",
        "measures": "Whether money owed by customers, or stock on hand, is growing faster than sales.",
        "deterioration": "Customers paying more slowly, or stock that is not selling, often show up here before they reach the profit line.",
        "innocent": "Stock builds ahead of a genuine demand ramp or a new product launch, and a shift towards larger customers lengthens payment terms by agreement.",
    },
    {
        "key": "share_count_roic",
        "flag": "Share count vs returns",
        "measures": "Whether the number of shares is rising while the return on invested capital falls.",
        "deterioration": "Issuing shares into falling returns dilutes existing holders to fund something earning less than it used to.",
        "innocent": "A company issuing stock to fund an acquisition or a build-out will show lower returns while the investment is still being made.",
    },
    {
        "key": "goodwill",
        "flag": "Goodwill",
        "measures": "Whether goodwill, the premium paid over book value in acquisitions, is growing as a share of total assets.",
        "deterioration": "Goodwill is the asset most likely to be written off. A rising share means more of the balance sheet rests on deals having worked.",
        "innocent": "A company that has just made a large acquisition it will do perfectly well out of looks exactly like this.",
    },
    {
        "key": "tax_rate",
        "flag": "Effective tax rate",
        "measures": "How much the tax rate moves around from year to year.",
        "deterioration": "A rate that jumps about can point to one-off items or aggressive positions holding up reported profit.",
        "innocent": "Where profits are earned changes, and one-off settlements and rate changes move the rate for entirely ordinary reasons.",
    },
    {
        "key": "stock_comp",
        "flag": "Stock compensation",
        "measures": "Whether pay issued in shares is growing as a share of revenue.",
        "deterioration": "Stock compensation is a real cost that does not leave the bank account. Rising fast, it flatters cash flow while diluting holders.",
        "innocent": "Competing for engineers means paying in stock. Plenty of good companies pay this way on purpose.",
    },
    {
        "key": "events",
        "flag": "Restatements, auditor changes, late filings",
        "measures": "Whether the company told the SEC it restated its accounts, changed auditor, or could not file on time in the last two years.",
        "deterioration": "These are not inferences. They are events the company disclosed itself, and they are the most direct evidence on this page.",
        "innocent": "Auditors are changed for cost and rotation rules, and a late filing can follow an acquisition or a system migration rather than a problem with the numbers.",
    },
]
