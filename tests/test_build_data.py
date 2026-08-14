from build_data import assemble_name, applicable_coverage, rank_all
from fetch_us import periods_for, build_records
from panel import Record


def rec(year, **kw):
    base = dict(ticker="A", name="A", market="m", year=year)
    base.update(kw)
    return Record(**base)


FULL = dict(net_income=200.0, cfo=100.0, assets=1000.0, revenue=1000.0,
            receivables=200.0, goodwill=300.0, tax_expense=50.0, stock_comp=60.0,
            diluted_shares=110.0, operating_income=80.0, equity=900.0, total_debt=100.0)
PRIOR = dict(net_income=150.0, cfo=140.0, assets=1000.0, revenue=1000.0,
             receivables=180.0, goodwill=200.0, tax_expense=50.0, stock_comp=30.0,
             diluted_shares=100.0, operating_income=120.0, equity=900.0, total_debt=100.0)


def test_periods_for_returns_instant_and_duration():
    assert periods_for(2024) == ("CY2024", "CY2024Q4I")


def test_build_records_populates_and_records_tags():
    frames = {"CY2024": {"Revenues": {1: 1000.0}, "NetIncomeLoss": {1: 100.0}},
              "CY2024Q4I": {"Assets": {1: 5000.0}}}
    meta = {1: {"ticker": "AAA", "name": "Alpha", "market": "United States (NYSE & Nasdaq)"}}
    r = build_records(2024, frames, meta)[0]
    assert (r.revenue, r.net_income, r.assets) == (1000.0, 100.0, 5000.0)
    assert r.tags["Revenue"] == "Revenues"


def test_build_records_leaves_absent_concepts_as_none():
    frames = {"CY2024": {}, "CY2024Q4I": {"Assets": {1: 5000.0}}}
    meta = {1: {"ticker": "AAA", "name": "Alpha", "market": "United States (NYSE & Nasdaq)"}}
    r = build_records(2024, frames, meta)[0]
    assert r.revenue is None and r.assets == 5000.0


def test_assemble_name_reports_applicable_count():
    out = assemble_name([rec(2024, **FULL), rec(2021, **PRIOR)])
    assert out["applicable"] >= 3
    assert "accruals" in out["flags"]
    assert out["flags"]["goodwill"]["applicable"] is True


def test_assemble_name_returns_none_for_single_year():
    assert assemble_name([rec(2024)]) is None


def test_applicable_coverage_is_fraction_of_names_where_flag_applies():
    rows = [{"flags": {"goodwill": {"applicable": True}}},
            {"flags": {"goodwill": {"applicable": False}}},
            {"flags": {"goodwill": {"applicable": True}}}]
    assert abs(applicable_coverage(rows, "goodwill") - 2 / 3) < 1e-9


def test_rank_all_keeps_pretax_fallback_population_separate():
    """A fallback name must not be ranked against true-operating-income names."""
    def row(ticker, value, fallback):
        return {"ticker": ticker, "operating_income_is_pretax_fallback": fallback,
                "flags": {k: {"value": None, "applicable": False, "reason": "x"}
                          for k in ("accruals", "working_capital", "goodwill",
                                    "tax_rate", "stock_comp")}
                | {"share_count_roic": {"value": value, "applicable": True, "reason": ""}}}

    rows = rank_all([row("T1", 1.0, False), row("T2", 9.0, False),
                     row("F1", 5.0, True), row("F2", 6.0, True)])
    by = {r["ticker"]: r["flags"]["share_count_roic"]["rank"] for r in rows}
    # Each population spans the full 0-100 range independently.
    assert by["T1"] == 0.0 and by["T2"] == 100.0
    assert by["F1"] == 0.0 and by["F2"] == 100.0
