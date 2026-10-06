"""SPEC §6.5: the exported fixture report, opened from file:// in Chrome.

Run with: pytest tests/test_report_browser.py --browser chromium --browser-channel chrome
"""
import pytest

import regret.report
from regret.config import get_config

EXPECTED_FIGURES = 8  # five core figures plus the geostrophic, NeuralGCM add-on and ensemble sections
RENDER_TIMEOUT_MS = 60_000


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """SPEC §6.5: always Google Chrome, whatever the command line says."""
    return {**browser_type_launch_args, "channel": "chrome"}


@pytest.fixture(scope="session")
def report_path(tmp_path_factory):
    out = tmp_path_factory.mktemp("report") / "report-fixture.html"
    return regret.report.export(get_config("fixture"), out)


@pytest.fixture(scope="module")
def loaded(report_path, browser):
    """Open the report once; record console errors and requests from before navigation."""
    page = browser.new_page()
    console_errors, requests = [], []
    page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
    page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
    page.on("request", lambda r: requests.append(r.url))
    page.goto(report_path.resolve().as_uri())
    page.wait_for_function(
        "n => document.querySelectorAll('.js-plotly-plot .main-svg').length >= n",
        arg=EXPECTED_FIGURES,
        timeout=RENDER_TIMEOUT_MS,
    )
    yield page, console_errors, requests
    page.close()


def test_no_console_errors(loaded):
    _, console_errors, _ = loaded
    assert console_errors == []


def test_figures_rendered(loaded):
    page, _, _ = loaded
    figs = page.locator(".js-plotly-plot")
    assert figs.count() == EXPECTED_FIGURES
    for i in range(EXPECTED_FIGURES):
        assert figs.nth(i).locator(".main-svg").count() >= 1, f"figure {i} has no .main-svg"


def test_no_network_requests(loaded):
    _, _, requests = loaded
    assert requests, "request capture saw nothing; listener not working"
    outside = [u for u in requests if not u.startswith(("file:", "data:"))]
    assert outside == []


def test_browser_is_google_chrome(loaded):
    page, _, _ = loaded
    browser = page.context.browser
    assert browser.browser_type.name == "chromium"
    brands = page.evaluate("navigator.userAgentData.brands.map(b => b.brand)")
    assert "Google Chrome" in brands, brands
