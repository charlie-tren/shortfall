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
    page.goto(URL)
    page.wait_for_selector(".card")
    return browser, page


def test_page_loads_without_application_errors(server):
    with sync_playwright() as pw:
        errors = []
        browser, page = page_with(pw, errors)
        assert page.locator(".card").count() > 10
        # The Cloudflare beacon cannot pass CORS from localhost; that is not ours.
        ours = [e for e in errors if "cloudflareinsights" not in e and "ERR_FAILED" not in e]
        assert ours == [], ours
        browser.close()


def test_sliders_reorder_and_reset_restores(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        first = page.locator(".card .ticker").first.text_content()
        sliders = page.locator("#sliders input")
        sliders.nth(3).fill("3")
        sliders.nth(3).dispatch_event("input")
        sliders.nth(0).fill("0")
        sliders.nth(0).dispatch_event("input")
        page.wait_for_timeout(250)
        skewed = page.locator(".card .ticker").first.text_content()
        assert skewed != first, "reweighting did not change the ranking"
        page.click("#resetWeights")
        page.wait_for_timeout(250)
        assert page.locator(".card .ticker").first.text_content() == first
        browser.close()


def test_equal_weight_baseline_is_shown_when_weights_move(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        assert page.locator(".card .base").count() == 0
        sliders = page.locator("#sliders input")
        sliders.nth(3).fill("3")
        sliders.nth(3).dispatch_event("input")
        page.wait_for_timeout(250)
        assert page.locator(".card .base").count() > 10
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
        assert "not applicable" in na.first.text_content()
        browser.close()


def test_market_filter_drives_the_list(server):
    with sync_playwright() as pw:
        browser, page = page_with(pw, [])
        before = page.locator(".card").count()
        options = page.locator("#filters select option").count()
        if options < 3:
            pytest.skip("only one market in this build")
        page.select_option("#filters select", index=1)
        page.wait_for_timeout(250)
        assert page.locator(".card").count() != before
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
