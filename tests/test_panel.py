from panel import Record, years_available, latest_with_history


def test_record_defaults_to_none():
    r = Record(ticker="AAA", name="A", market="m", year=2024)
    assert r.revenue is None and r.tags == {}


def test_years_available_sorted_descending():
    rs = [Record(ticker="A", name="A", market="m", year=y) for y in (2022, 2024, 2023)]
    assert years_available(rs) == [2024, 2023, 2022]


def test_latest_with_history_returns_none_when_too_short():
    rs = [Record(ticker="A", name="A", market="m", year=2024)]
    assert latest_with_history(rs, need=2) is None


def test_latest_with_history_returns_latest_and_priors():
    rs = [Record(ticker="A", name="A", market="m", year=y) for y in (2021, 2022, 2023, 2024)]
    latest, priors = latest_with_history(rs, need=2)
    assert latest.year == 2024
    assert [p.year for p in priors] == [2023, 2022, 2021]


def test_pretax_fallback_detected():
    r = Record(ticker="A", name="A", market="m", year=2024,
               tags={"OperatingIncome": "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"})
    assert r.operating_income_is_pretax_fallback is True


def test_true_operating_income_is_not_a_fallback():
    r = Record(ticker="A", name="A", market="m", year=2024,
               tags={"OperatingIncome": "OperatingIncomeLoss"})
    assert r.operating_income_is_pretax_fallback is False


def test_absent_operating_income_is_not_a_fallback():
    # Absent is absent. Calling it a fallback would put names with NO operating
    # income into the fallback ranking population.
    r = Record(ticker="A", name="A", market="m", year=2024)
    assert r.operating_income_is_pretax_fallback is False
