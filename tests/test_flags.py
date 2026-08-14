from flags import (flag_accruals, flag_working_capital, flag_share_count_vs_roic,
                   flag_goodwill, flag_tax_rate, flag_stock_comp,
                   goodwill_exceeds_equity, ALL_FLAGS)
from panel import Record


def rec(year=2024, **kw):
    base = dict(ticker="A", name="A", market="m", year=year)
    base.update(kw)
    return Record(**base)


# --- flag 1: accruals -------------------------------------------------------

def test_accruals_positive_when_income_exceeds_cash():
    value, applicable, _ = flag_accruals(
        rec(net_income=200.0, cfo=100.0, assets=1000.0), [rec(2023, assets=1000.0)])
    assert applicable
    assert abs(value - 0.1) < 1e-9


def test_accruals_uses_average_assets():
    value, _, _ = flag_accruals(
        rec(net_income=200.0, cfo=100.0, assets=1200.0), [rec(2023, assets=800.0)])
    assert abs(value - 0.1) < 1e-9


def test_accruals_not_applicable_without_cfo():
    value, applicable, reason = flag_accruals(
        rec(net_income=200.0, cfo=None, assets=1000.0), [rec(2023, assets=1000.0)])
    assert (value, applicable) == (None, False)
    assert reason == "no cash flow figure"


def test_accruals_not_applicable_when_asx_cfo_disagreed():
    _, applicable, reason = flag_accruals(
        rec(net_income=200.0, cfo=None, cfo_status="disagree", assets=1000.0),
        [rec(2023, assets=1000.0)])
    assert not applicable
    assert reason == "cash flow could not be derived"


# --- flag 2: working capital ------------------------------------------------

def test_working_capital_takes_the_larger_deterioration():
    value, applicable, _ = flag_working_capital(
        rec(revenue=1000.0, receivables=200.0, inventory=100.0),
        [rec(2023, revenue=1000.0, receivables=180.0, inventory=99.0)])
    assert applicable
    assert abs(value - 0.1111) < 1e-3


def test_working_capital_applies_with_receivables_only():
    _, applicable, _ = flag_working_capital(
        rec(revenue=1000.0, receivables=200.0, inventory=None),
        [rec(2023, revenue=1000.0, receivables=180.0, inventory=None)])
    assert applicable


def test_working_capital_not_applicable_with_neither():
    _, applicable, reason = flag_working_capital(
        rec(revenue=1000.0, receivables=None, inventory=None), [rec(2023, revenue=1000.0)])
    assert not applicable
    assert reason == "no receivables or inventory reported"


# --- flag 3: share count vs ROIC -------------------------------------------

def test_fires_when_shares_grow_and_roic_falls():
    latest = rec(diluted_shares=110.0, operating_income=80.0, equity=900.0,
                 total_debt=100.0, tax_expense=20.0, net_income=60.0)
    priors = [rec(2021, diluted_shares=100.0, operating_income=120.0, equity=900.0,
                  total_debt=100.0, tax_expense=30.0, net_income=90.0)]
    value, applicable, _ = flag_share_count_vs_roic(latest, priors)
    assert applicable and value > 0


def test_does_not_fire_when_roic_rises():
    latest = rec(diluted_shares=110.0, operating_income=200.0, equity=900.0,
                 total_debt=100.0, tax_expense=50.0, net_income=150.0)
    priors = [rec(2021, diluted_shares=100.0, operating_income=100.0, equity=900.0,
                  total_debt=100.0, tax_expense=25.0, net_income=75.0)]
    value, applicable, _ = flag_share_count_vs_roic(latest, priors)
    assert applicable and value == 0.0


def test_falls_back_to_equity_when_debt_missing():
    latest = rec(diluted_shares=110.0, operating_income=80.0, equity=1000.0,
                 total_debt=None, tax_expense=20.0, net_income=60.0)
    priors = [rec(2021, diluted_shares=100.0, operating_income=120.0, equity=1000.0,
                  total_debt=None, tax_expense=30.0, net_income=90.0)]
    _, applicable, reason = flag_share_count_vs_roic(latest, priors)
    assert applicable
    assert reason == "invested capital excludes debt"


def test_share_count_uses_the_OLDEST_prior_not_the_newest():
    # The window is deliberately 3 years, so the comparison must reach the oldest
    # record. Using priors[0] would silently make it a 1-year flag.
    latest = rec(diluted_shares=130.0, operating_income=80.0, equity=1000.0,
                 total_debt=0.0, tax_expense=20.0, net_income=60.0)
    priors = [rec(2023, diluted_shares=125.0, operating_income=90.0, equity=1000.0,
                  total_debt=0.0, tax_expense=20.0, net_income=70.0),
              rec(2021, diluted_shares=100.0, operating_income=120.0, equity=1000.0,
                  total_debt=0.0, tax_expense=30.0, net_income=90.0)]
    value, _, _ = flag_share_count_vs_roic(latest, priors)
    # Against the 2021 base: 30% share growth, ROIC 0.09 -> 0.06, so 0.30 * 0.03.
    # Against the 2023 base it would be 0.04 * 0.01 = 0.0004, twenty times smaller.
    assert abs(value - 0.009) < 1e-6


# --- flag 4: goodwill -------------------------------------------------------

def test_goodwill_share_rising():
    value, applicable, _ = flag_goodwill(
        rec(goodwill=300.0, assets=1000.0, equity=500.0),
        [rec(2021, goodwill=200.0, assets=1000.0, equity=500.0)])
    assert applicable
    assert abs(value - 0.1) < 1e-9


def test_goodwill_not_applicable_when_absent():
    _, applicable, reason = flag_goodwill(rec(goodwill=None, assets=1000.0),
                                          [rec(2021, assets=1000.0)])
    assert not applicable
    assert reason == "no goodwill reported"


def test_goodwill_exceeds_equity_is_reported():
    assert goodwill_exceeds_equity(rec(goodwill=600.0, equity=500.0)) is True
    assert goodwill_exceeds_equity(rec(goodwill=400.0, equity=500.0)) is False
    assert goodwill_exceeds_equity(rec(goodwill=None, equity=500.0)) is False


# --- flag 5: tax rate -------------------------------------------------------

def test_tax_flag_fires_on_volatility():
    latest = rec(net_income=80.0, tax_expense=20.0)
    priors = [rec(2023, net_income=95.0, tax_expense=5.0),
              rec(2022, net_income=60.0, tax_expense=40.0),
              rec(2021, net_income=90.0, tax_expense=10.0)]
    value, applicable, _ = flag_tax_rate(latest, priors)
    assert applicable and value > 0.1


def test_tax_flag_low_for_stable_rate():
    latest = rec(net_income=75.0, tax_expense=25.0)
    priors = [rec(y, net_income=75.0, tax_expense=25.0) for y in (2023, 2022, 2021)]
    value, applicable, _ = flag_tax_rate(latest, priors)
    assert applicable and value < 1e-9


def test_tax_flag_not_applicable_for_loss_maker():
    _, applicable, reason = flag_tax_rate(rec(net_income=-500.0, tax_expense=10.0),
                                          [rec(2023, net_income=75.0, tax_expense=25.0)])
    assert not applicable
    assert reason == "effective tax rate not meaningful"


# --- flag 6: stock comp -----------------------------------------------------

def test_stock_comp_rising_against_revenue():
    value, applicable, _ = flag_stock_comp(rec(stock_comp=60.0, revenue=1000.0),
                                           [rec(2021, stock_comp=30.0, revenue=1000.0)])
    assert applicable
    assert abs(value - 0.03) < 1e-9


def test_stock_comp_not_applicable_when_absent():
    _, applicable, reason = flag_stock_comp(rec(stock_comp=None, revenue=1000.0),
                                            [rec(2021, revenue=1000.0)])
    assert not applicable
    assert reason == "no share-based compensation reported"


# --- shape ------------------------------------------------------------------

def test_every_flag_returns_the_same_triple_shape():
    latest, priors = rec(), [rec(2021)]
    for name, fn in ALL_FLAGS.items():
        result = fn(latest, priors)
        assert len(result) == 3, name
        value, applicable, reason = result
        assert isinstance(applicable, bool), name
        if not applicable:
            assert value is None and reason, name
