"""Copy for the tests table.

FLAT STATEMENTS, not epigrams. An earlier version gave every cell the same pithy
rhythm - "paying up for engineers, on purpose", "not an inference, the company
disclosed it" - and the uniformity was the tell. Say what the thing is and stop.
"""

EXPLANATIONS = [
    {
        "key": "accruals",
        "flag": "Accruals vs cash",
        "measures": "Profit minus operating cash flow, over assets.",
        "deterioration": "Profit is not converting to cash.",
        "innocent": "Growth ties up cash before it is collected.",
    },
    {
        "key": "working_capital",
        "flag": "Receivables and inventory",
        "measures": "Receivables and stock growing faster than sales.",
        "deterioration": "Customers paying slower, or stock not moving.",
        "innocent": "Stock built for a launch, or bigger customers on longer terms.",
    },
    {
        "key": "share_count_roic",
        "flag": "Share count vs returns",
        "measures": "Share count rising while return on capital falls.",
        "deterioration": "Dilution funding worse returns.",
        "innocent": "A recent acquisition not yet earning.",
    },
    {
        "key": "goodwill",
        "flag": "Goodwill",
        "measures": "Goodwill as a share of assets.",
        "deterioration": "First asset to be written down.",
        "innocent": "A recent acquisition.",
    },
    {
        "key": "tax_rate",
        "flag": "Effective tax rate",
        "measures": "Year-to-year movement in the tax rate.",
        "deterioration": "One-offs flattering reported profit.",
        "innocent": "Changed profit mix, settlements, rate changes.",
    },
    {
        "key": "stock_comp",
        "flag": "Stock compensation",
        "measures": "Share-based pay as a share of revenue.",
        "deterioration": "A cost that dilutes holders without touching cash.",
        "innocent": "Competing for staff.",
    },
    {
        "key": "events",
        "flag": "Filing events",
        "measures": "Restatement, auditor change or late filing in two years.",
        "deterioration": "Disclosed by the company itself.",
        "innocent": "Auditor rotation, or a systems migration.",
    },
]
