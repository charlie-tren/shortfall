"""Renderer tests.

These assert on the DISCLOSURES, not on the prose around them. Copy gets rewritten;
what must not silently change is that the caveats are computed from the data rather
than typed as literals, and that company names are escaped.
"""

from build import render

BASE = {"names": [], "excluded": [], "coverage": {}, "coverage_warnings": [],
        "explanations": [], "correlations": {"pairs": [], "mean_abs": None,
                                             "strongest": None, "order": [], "short": {}}}


def row(**kw):
    base = {"ticker": "AAA", "name": "Alpha", "market": "Australia (ASX)",
            "composite": 90.0, "applicable": 5, "flags": {},
            "goodwill_exceeds_equity": False, "events": [], "assets": 1e9}
    base.update(kw)
    return base


def test_render_includes_the_name_and_the_backtest_caveat():
    html = render({**BASE, "names": [row()]})
    assert "Shortfall" in html
    assert "No backtest" in html


def test_asx_count_in_the_us_only_caveat_comes_from_the_data():
    html = render({**BASE, "names": [row(), row(ticker="BBB")],
                   "excluded": [row(ticker="CCC")]})
    assert "3\n      Australian names" in html or "3 Australian names" in html


def test_asx_count_is_zero_when_there_are_no_asx_names():
    html = render({**BASE, "names": [row(market="United States (NYSE & Nasdaq)")]})
    assert "0\n      Australian names" in html or "0 Australian names" in html


def test_unranked_count_comes_from_the_data():
    html = render({**BASE, "names": [row()],
                   "excluded": [row(ticker="X"), row(ticker="Y")]})
    assert "2 companies are unranked" in html


def test_render_escapes_company_names():
    html = render({**BASE, "names": [row(name="A & B <script>alert(1)</script>")]})
    assert "<script>alert(1)</script>" not in html


def test_chart_and_pager_containers_exist():
    html = render({**BASE, "names": [row()]})
    assert 'id="quadSvg"' in html
    assert 'id="strips"' in html
    assert 'id="tip"' in html
    assert 'id="pager"' in html
