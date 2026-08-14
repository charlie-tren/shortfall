from edgar import dedupe_by_cik, TICKER_CIK_OVERRIDES


def names(*tickers):
    return [{"ticker": t, "name": t, "market": "United States (NYSE & Nasdaq)"} for t in tickers]


def test_dual_class_collapses_to_one_name():
    lookup = {"GOOGL": 1652044, "GOOG": 1652044, "AAPL": 320193}
    kept, dropped = dedupe_by_cik(names("GOOGL", "GOOG", "AAPL"), lookup)
    assert [n["ticker"] for n in kept] == ["GOOGL", "AAPL"]
    assert dropped == [("GOOG", "GOOGL")]


def test_first_seen_wins():
    lookup = {"FOXA": 1754301, "FOX": 1754301}
    kept, _ = dedupe_by_cik(names("FOX", "FOXA"), lookup)
    assert [n["ticker"] for n in kept] == ["FOX"]


def test_unmapped_names_are_kept_for_the_loud_failure_later():
    # dedupe must not be the thing that silently drops an unmapped ticker;
    # map_tickers_to_cik is what raises on it.
    kept, dropped = dedupe_by_cik(names("NOSUCH"), {})
    assert [n["ticker"] for n in kept] == ["NOSUCH"]
    assert dropped == []


def test_aep_override_present():
    # company_tickers.json omits AEP; verified against the submissions endpoint.
    assert TICKER_CIK_OVERRIDES["AEP"] == 4904
