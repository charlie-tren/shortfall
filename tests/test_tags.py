from tags import resolve, CHAINS, TRUE_OPERATING_INCOME_TAG, KIND, UNIT


def test_resolve_takes_first_available():
    frames = {"Revenues": {1: 100.0}, "SalesRevenueNet": {1: 999.0}}
    val, tag = resolve("Revenue", 1, frames)
    assert (val, tag) == (100.0, "Revenues")


def test_resolve_falls_through():
    frames = {"Revenues": {}, "RevenueFromContractWithCustomerExcludingAssessedTax": {1: 55.0}}
    val, tag = resolve("Revenue", 1, frames)
    assert (val, tag) == (55.0, "RevenueFromContractWithCustomerExcludingAssessedTax")


def test_resolve_returns_none_when_absent():
    assert resolve("Revenue", 99, {"Revenues": {1: 100.0}}) == (None, None)


def test_operating_income_chain_marks_pretax_fallback():
    # The fallbacks are PRETAX income, not operating income. Callers must be able
    # to tell, because it changes what ROIC means.
    assert CHAINS["OperatingIncome"][0] == TRUE_OPERATING_INCOME_TAG
    assert len(CHAINS["OperatingIncome"]) == 3


def test_every_concept_has_a_kind():
    assert set(KIND) == set(CHAINS)


def test_only_share_counts_are_non_usd():
    assert UNIT == {"DilutedShares": "shares"}
