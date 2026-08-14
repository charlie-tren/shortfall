import pytest

from edgar import normalise_ticker, map_tickers_to_cik


def test_normalise_dotted_tickers():
    # EDGAR writes class shares with a hyphen; Wikipedia uses a dot.
    assert normalise_ticker("BRK.B") == "BRK-B"
    assert normalise_ticker("AAPL") == "AAPL"


def test_map_tickers_raises_on_unmapped():
    lookup = {"AAPL": 320193}
    with pytest.raises(ValueError) as e:
        map_tickers_to_cik(["AAPL", "NOSUCH"], lookup)
    assert "NOSUCH" in str(e.value)


def test_map_tickers_returns_cik():
    lookup = {"AAPL": 320193, "BRK-B": 1067983}
    assert map_tickers_to_cik(["AAPL", "BRK.B"], lookup) == {"AAPL": 320193, "BRK.B": 1067983}
