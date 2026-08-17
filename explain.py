"""Copy for the explanation table.

Kept SHORT on purpose. An earlier version ran three full sentences per cell across
four columns and nobody was going to read it. The columns are a reference you scan
while looking at a card, not an essay.
"""

EXPLANATIONS = [
    {
        "key": "accruals",
        "flag": "Accruals vs cash",
        "measures": "Profit not backed by cash, over assets.",
        "deterioration": "The gap has to close, usually by profit falling.",
        "innocent": "Growth funds working capital before it collects.",
    },
    {
        "key": "working_capital",
        "flag": "Receivables and inventory",
        "measures": "Working capital growing faster than sales.",
        "deterioration": "Slower payers, or stock that is not selling.",
        "innocent": "Stock ahead of a launch. Bigger customers, longer terms.",
    },
    {
        "key": "share_count_roic",
        "flag": "Share count vs returns",
        "measures": "Dilution while return on capital falls.",
        "deterioration": "Issuing shares into worse economics.",
        "innocent": "Funding an acquisition that has not paid off yet.",
    },
    {
        "key": "goodwill",
        "flag": "Goodwill",
        "measures": "Acquisition premium as a share of assets.",
        "deterioration": "The asset most likely to be written off.",
        "innocent": "A big deal that will work out fine.",
    },
    {
        "key": "tax_rate",
        "flag": "Effective tax rate",
        "measures": "How much the rate moves year to year.",
        "deterioration": "One-offs propping up reported profit.",
        "innocent": "Profit mix shifts. Settlements. Rate changes.",
    },
    {
        "key": "stock_comp",
        "flag": "Stock compensation",
        "measures": "Share-based pay as a share of revenue.",
        "deterioration": "A real cost that never leaves the bank account.",
        "innocent": "Paying up for engineers, on purpose.",
    },
    {
        "key": "events",
        "flag": "Filing events",
        "measures": "Restatement, auditor change or late filing, two years.",
        "deterioration": "Not an inference. The company disclosed it.",
        "innocent": "Auditor rotation. A systems migration.",
    },
]
