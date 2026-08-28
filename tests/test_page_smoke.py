"""Rendered-page smoke pass.

Requires: pip install playwright && playwright install chromium
Skipped automatically when playwright is not installed, so CI can ignore it.
"""

import os
import subprocess
import sys
import time

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright   # noqa: E402

PORT = 8901
URL = f"http://localhost:{PORT}/"
DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")


@pytest.fixture(scope="module")
def server():
    if not os.path.exists(os.path.join(DOCS, "index.html")):
        pytest.skip("docs/index.html not built")
    p = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=DOCS,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    yield
    p.terminate()


def page_with(pw, errors):
    browser = pw.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    # pageerror is an UNCAUGHT EXCEPTION and must fail the suite. Listening only for
    # console errors let a null reference through: render() kept writing to a note
    # element that had been deleted with the scatter panel, which threw during init
    # and silently stopped the theme toggle ever being wired up. The page still
    # rendered, so every other assertion passed.
    page.on("pageerror", lambda e: errors.append(f"UNCAUGHT: {e}"))
    page.goto(URL)
    page.wait_for_selector(".card")
    return browser, page


def test_no_uncaught_exceptions_during_init(server):
    with sync_playwright() as pw:
        errors = []
        browser, page = page_with(pw, errors)
        page.wait_for_timeout(400)
        assert not [e for e in errors if e.startswith("UNCAUGHT")], errors
        browser.close()


def test_page_loads_without_application_errors(server):
    with sync_playwright() as pw:
        errors = []
        browser, page = page_with(pw, errors)
        assert page.locator(".card").count() > 10
        # The Cloudflare beacon cannot pass CORS from localhost; that is not ours.
        # This passes in CI only because the analytics gate suppresses BOTH beacons for
        # automation, so a headless browser never requests them and there is no DNS
        # lookup to fail. Before that gate landed this test failed on the runner with a
        # bare "Failed to load resource: net::ERR_NAME_NOT_RESOLVED", which carries no
        # URL and so slips past the filter below. If the gate is ever removed, filter on
        # requestfailed (which does carry a URL) rather than widening this list.
        ours = [e for e in errors if "cloudflareinsights" not in e and "ERR_FAILED" not in e]
        assert ours == [], ours
        browser.close()


def test_sliders_reorder_and_reset_restores(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        # Compare the whole page, not just the top name. Several companies tie at
        # exactly 100 once severity is a cohort percentile, so the first ticker can
        # legitimately stay put while everything under it reorders.
        first = page.locator(".card .ticker").all_text_contents()
        sliders = page.locator("#sliders input")
        sliders.nth(3).fill("3")
        sliders.nth(3).dispatch_event("input")
        sliders.nth(0).fill("0")
        sliders.nth(0).dispatch_event("input")
        page.wait_for_timeout(300)
        skewed = page.locator(".card .ticker").all_text_contents()
        assert skewed != first, "reweighting did not change the ranking"
        page.click("#resetWeights")
        page.wait_for_timeout(300)
        assert page.locator(".card .ticker").all_text_contents() == first
        browser.close()


def test_equal_weight_baseline_is_shown_when_weights_move(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        # 20 cards a page now, so this asserts SOME card shows the default score,
        # not a count that assumed the old 100-card list.
        assert page.locator(".card .base").count() == 0
        sliders = page.locator("#sliders input")
        sliders.nth(3).fill("3")
        sliders.nth(3).dispatch_event("input")
        sliders.nth(5).fill("0")
        sliders.nth(5).dispatch_event("input")
        page.wait_for_timeout(300)
        assert page.locator(".card .base").count() > 0
        browser.close()


def test_explanation_table_has_four_columns_and_every_flag(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.wait_for_selector("#explainBody tr")
        assert page.locator("#explainBody tr").count() == 7
        assert page.locator("#explainBody tr").first.locator("td").count() == 4
        browser.close()


def test_not_applicable_is_shown_as_such_never_as_a_score(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        na = page.locator(".card dd.na")
        assert na.count() > 0
        # Shown as n/a with the reason on hover - distinct from a score, never a pass.
        assert na.first.text_content().strip() == "n/a"
        assert na.first.get_attribute("title")
        browser.close()


def test_market_filter_drives_the_list(server):
    """Assert on CONTENT, not count: the card list is capped at 100 and both
    markets have more than 100 ranked names, so the count cannot move."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        options = page.locator("#filters select option")
        if options.count() < 3:
            pytest.skip("only one market in this build")
        before = page.locator(".card .ticker").first.text_content()
        page.select_option("#filters select", label="Australia (ASX)")
        page.wait_for_timeout(300)
        tickers = page.locator(".card .ticker").all_text_contents()
        assert tickers, "filter emptied the list"
        assert all(t.endswith(".AX") for t in tickers), \
            f"non-ASX names survived the Australia filter: {[t for t in tickers if not t.endswith('.AX')][:5]}"
        page.select_option("#filters select", label="United States (NYSE & Nasdaq)")
        page.wait_for_timeout(300)
        us = page.locator(".card .ticker").all_text_contents()
        assert us and not any(t.endswith(".AX") for t in us)
        page.select_option("#filters select", value="all")
        page.wait_for_timeout(300)
        assert page.locator(".card .ticker").first.text_content() == before
        browser.close()


def test_events_filter_shows_only_names_with_a_disclosed_event(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.check("#filters input[type=checkbox]")
        page.wait_for_timeout(300)
        cards = page.locator(".card")
        assert cards.count() > 0, "no company carries a filing event"
        # Every remaining card must show at least one badge.
        for i in range(cards.count()):
            assert cards.nth(i).locator(".badge").count() > 0
        browser.close()


def test_both_themes_render(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        start = page.locator("html").get_attribute("data-theme")
        page.click("#themeBtn")
        page.wait_for_timeout(150)
        assert page.locator("html").get_attribute("data-theme") != start
        assert page.locator(".card").count() > 10
        browser.close()


def test_pager_walks_the_list(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        assert page.locator(".card").count() == 20
        first = page.locator("#pageInfo").text_content()
        assert page.locator("#prevPage").is_disabled()
        page.click("#nextPage")
        page.wait_for_timeout(300)
        assert page.locator("#pageInfo").text_content() != first
        assert not page.locator("#prevPage").is_disabled()
        page.click("#prevPage")
        page.wait_for_timeout(300)
        assert page.locator("#pageInfo").text_content() == first
        browser.close()


def test_filtering_returns_to_page_one(server):
    """Otherwise you sit on page 6 of a list that now has two entries."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.click("#nextPage")
        page.click("#nextPage")
        page.wait_for_timeout(300)
        assert page.locator("#pageInfo").text_content().startswith("41-")
        page.select_option("#filters select", label="Australia (ASX)")
        page.wait_for_timeout(300)
        assert page.locator("#pageInfo").text_content().startswith("1-")
        browser.close()


def names_on_page(page):
    return page.eval_on_selector_all("#cards .card h3", "ns => ns.map(n => n.textContent)")


def test_lookup_matches_from_the_start_not_the_middle(server):
    """A substring lookup is quietly useless on a list of 652 companies: "AMD" also
    returns Camden Property Trust and "ON" returns twenty names, because both sit
    inside longer words. Matching only from the start of the ticker or of a word in
    the name is what makes three letters name a company rather than describe one."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        box = page.locator("#filters input[type=search]")
        box.fill("AMD")
        page.wait_for_timeout(250)
        assert names_on_page(page) == ["Advanced Micro Devices"]
        box.fill("ON")
        page.wait_for_timeout(250)
        got = names_on_page(page)
        assert "ON Semiconductor" in got
        assert not any("Constellation" in n or "Regeneron" in n for n in got), got
        browser.close()


def test_a_query_in_the_url_lands_on_that_company(server):
    """The whole point of the lookup: Consensus Drift and DCF Studio hand a ticker
    over by URL, and a handoff that lands on the unfiltered list is not a handoff."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(URL + "?q=CBA.AX")
        page.wait_for_selector("#cards .card")
        page.wait_for_timeout(250)
        assert names_on_page(page) == ["Commonwealth Bank"]
        assert page.locator("#filters input[type=search]").input_value() == "CBA.AX"
        browser.close()


def test_an_empty_lookup_leaves_no_trace_in_the_url(server):
    """Never write the default state to the URL - a shared link must not carry an
    empty filter."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        box = page.locator("#filters input[type=search]")
        box.fill("CBA")
        page.wait_for_timeout(250)
        assert "q=CBA" in page.url
        box.fill("")
        page.wait_for_timeout(250)
        assert "q=" not in page.url, page.url
        browser.close()


def test_also_on_links_carry_the_ticker(server):
    """The handoff: same company, sibling site, ticker in the URL."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.fill("#filters input[type=search]", "CBA.AX")
        page.wait_for_timeout(250)
        hrefs = page.eval_on_selector_all(
            "#cards .card .alsoon a", "ns => ns.map(a => a.href)")
        assert any("consensus-drift/?q=CBA.AX" in h for h in hrefs), hrefs
        assert any(h.endswith("dcf.charlietrenorden.com/CBA.AX") for h in hrefs), hrefs
        browser.close()


def test_a_sibling_that_lacks_the_company_is_omitted_not_shown(server):
    """Consensus Drift drops about a hundred names a week where estimate history is
    too sparse, so 37 of these 652 have no reading to link to. Charlie's choice was to
    omit the link rather than grey it - which only works if the code actually checks."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.fill("#filters input[type=search]", "4DX.AX")
        page.wait_for_timeout(250)
        labels = page.eval_on_selector_all(
            "#cards .card .alsoon a", "ns => ns.map(a => a.textContent)")
        assert labels == ["DCF Studio"], labels
        browser.close()


def test_no_peer_list_means_no_links_rather_than_broken_ones(server):
    """A build that could not reach the siblings must show nothing, not guess. The
    failure this guards is a link that lands on a page without the company."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.evaluate("() => { window.SHORTFALL_PEERS = {}; render(); }")
        page.wait_for_timeout(250)
        labels = page.eval_on_selector_all(
            "#cards .card .alsoon a", "ns => ns.map(a => a.textContent)")
        assert set(labels) == {"DCF Studio"}, labels
        browser.close()


def test_a_lookup_leaves_the_charts_populated(server):
    """The bug this fixes: arriving from Consensus Drift or DCF Studio filtered the
    page to one company, which emptied the cross-plot and the distributions - both are
    about a POPULATION and one company has no distribution. The charts now keep the
    population and mark the company instead, which is also the more useful answer,
    since where a company sits against its peers is Shortfall's whole subject."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_selector("#cards .card")
        page.wait_for_timeout(400)
        before = page.eval_on_selector_all("#quadSvg .dot", "ns => ns.length")
        assert before > 100

        page.goto(URL + "?q=AMD")
        page.wait_for_selector("#cards .card")
        page.wait_for_timeout(400)
        assert page.eval_on_selector_all("#cards .card", "ns => ns.length") == 1
        assert page.eval_on_selector_all("#quadSvg .dot", "ns => ns.length") == before
        assert page.eval_on_selector_all("#quadSvg .dot.found", "ns => ns.length") == 1
        assert page.eval_on_selector_all(".ridgefound", "ns => ns.length") > 0
        assert "what you searched for" in page.locator("#quadKey").text_content()
        browser.close()


def test_the_other_filters_still_narrow_the_charts(server):
    """Only the LOOKUP is exempt. A market or sector filter must still drive the
    charts, or the page would show a population the reader did not ask for."""
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        page.wait_for_timeout(300)
        before = page.eval_on_selector_all("#quadSvg .dot", "ns => ns.length")
        page.select_option("#filters select", label="Australia (ASX)")
        page.wait_for_timeout(400)
        assert page.eval_on_selector_all("#quadSvg .dot", "ns => ns.length") < before
        browser.close()


def test_a_match_missing_from_the_pair_says_so(server):
    """Short interest is a US disclosure, so no ASX name appears against it. Absent
    and unmarked is indistinguishable from present and unfound - the note has to say
    which, or the reader concludes the mark is broken."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(URL + "?q=CBA.AX")
        page.wait_for_selector("#cards .card")
        page.wait_for_timeout(400)
        assert page.eval_on_selector_all("#quadSvg .dot.found", "ns => ns.length") == 0
        note = page.locator("#quadNote").text_content()
        assert "not on this pair" in note, note
        assert "Commonwealth Bank" in note, note
        browser.close()
