import pandas as pd

from asx import derive_cfo, records_from_statements


# --- derived CFO ------------------------------------------------------------

def test_uses_value_when_both_routes_agree():
    got = derive_cfo(fcf=100.0, capex=-20.0, change_in_cash=95.0,
                     investing=-30.0, financing=5.0, assets=1000.0)
    # Route A: 100 + 20 = 120. Route B: 95 + 30 - 5 = 120.
    assert got == (120.0, "agreed")


def test_marks_unavailable_when_routes_disagree():
    got = derive_cfo(fcf=100.0, capex=-20.0, change_in_cash=500.0,
                     investing=-30.0, financing=5.0, assets=1000.0)
    assert got == (None, "disagree")


def test_tolerance_is_two_percent_of_assets():
    # Route A 120, Route B 135: a 15 gap on 1000 assets is 1.5%, inside tolerance.
    got = derive_cfo(fcf=100.0, capex=-20.0, change_in_cash=110.0,
                     investing=-30.0, financing=5.0, assets=1000.0)
    assert got[1] == "agreed"


def test_unavailable_when_only_one_route_resolves():
    got = derive_cfo(fcf=100.0, capex=-20.0, change_in_cash=None,
                     investing=None, financing=None, assets=1000.0)
    assert got == (None, "single_route")


def test_no_route_when_nothing_resolves():
    assert derive_cfo(None, None, None, None, None, 1000.0) == (None, "no_route")


# --- record building --------------------------------------------------------

COLS = [pd.Timestamp("2025-06-30"), pd.Timestamp("2024-06-30")]


def statements(**overrides):
    bs = pd.DataFrame({COLS[0]: [1000.0, 200.0], COLS[1]: [900.0, 180.0]},
                      index=["Total Assets", "Accounts Receivable"])
    inc = pd.DataFrame({COLS[0]: [5000.0], COLS[1]: [4500.0]}, index=["Total Revenue"])
    cf = pd.DataFrame({COLS[0]: [300.0], COLS[1]: [280.0]}, index=["Free Cash Flow"])
    return {"balance": bs, "income": inc, "cashflow": cf, **overrides}


def test_builds_one_record_per_year():
    recs = records_from_statements("AAA.AX", "Alpha", statements())
    assert [r.year for r in recs] == [2025, 2024]
    assert recs[0].assets == 1000.0
    assert recs[0].revenue == 5000.0
    assert recs[0].market == "Australia (ASX)"


def test_cfo_marked_when_not_derivable():
    recs = records_from_statements("AAA.AX", "Alpha", statements())
    assert recs[0].cfo is None
    assert recs[0].cfo_status in ("single_route", "no_route")


def test_empty_balance_sheet_yields_no_records():
    assert records_from_statements("AAA.AX", "Alpha",
                                   {"balance": pd.DataFrame(), "income": pd.DataFrame(),
                                    "cashflow": pd.DataFrame()}) == []


def test_nan_values_are_treated_as_absent():
    bs = pd.DataFrame({COLS[0]: [1000.0, float("nan")]},
                      index=["Total Assets", "Inventory"])
    recs = records_from_statements("AAA.AX", "Alpha",
                                   {"balance": bs, "income": pd.DataFrame(),
                                    "cashflow": pd.DataFrame()})
    assert recs[0].inventory is None
    assert recs[0].assets == 1000.0
