from build import render

BASE = {"names": [], "excluded": [], "coverage": {}, "coverage_warnings": [],
        "explanations": []}


def row(**kw):
    base = {"ticker": "AAA", "name": "Alpha", "market": "Australia (ASX)",
            "composite": 90.0, "applicable": 5, "flags": {},
            "goodwill_exceeds_equity": False, "events": []}
    base.update(kw)
    return base


def test_render_includes_title_and_the_backtest_disclosure():
    html = render({**BASE, "names": [row()]})
    assert "Shortfall" in html
    assert "has not been backtested" in html


def test_render_counts_asx_names_for_the_us_only_disclosure():
    html = render({**BASE, "names": [row(), row(ticker="BBB")],
                   "excluded": [row(ticker="CCC")]})
    # 3 ASX names across included and excluded.
    assert "The\n    3 Australian names" in html or "3 Australian names" in html


def test_render_reports_the_excluded_count():
    html = render({**BASE, "names": [row()], "excluded": [row(ticker="X"), row(ticker="Y")]})
    assert "There are 2 of them" in html


def test_render_escapes_company_names():
    html = render({**BASE, "names": [row(name="A & B <script>alert(1)</script>")]})
    assert "<script>alert(1)</script>" not in html


def test_render_does_not_hardcode_a_market_count():
    # The disclosure must come from the data, not a literal.
    html = render({**BASE, "names": [row(market="United States (NYSE & Nasdaq)")]})
    assert "0 Australian names" in html
