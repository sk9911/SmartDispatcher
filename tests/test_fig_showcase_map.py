import numpy as np
import pytest

from regret import config, planner, replay, sources
from regret.figures import showcase_map as sm
from regret.types import Plan
from regret.units import initial_bearing_deg


@pytest.fixture(scope="module")
def cfg():
    return config.get_config("fixture")


@pytest.fixture(scope="module")
def plans(cfg):
    return sm.showcase_plans(cfg)


@pytest.fixture(scope="module")
def fig(cfg, plans):
    return sm.build_showcase_map(cfg, plans=plans)


def _plan_traces(fig):
    return [t for t in fig.data if (t.meta or {}).get("kind") == "plan"]


def test_plan_traces_per_lead_and_initial_visibility(cfg, fig):
    n_src = len(cfg.sources)
    traces = _plan_traces(fig)
    assert len(traces) == len(cfg.leads_h) * (n_src + 1)
    for lead in cfg.leads_h:
        names = [t.meta["source"] for t in traces if t.meta["lead_h"] == lead]
        assert sorted(names) == sorted(list(cfg.sources) + ["hindsight"])
    for t in traces:
        assert (t.visible in (True, None)) == (t.meta["lead_h"] == 24)
        assert f"{t.meta['lead_h']} h" in t.hovertext


def test_dropdown_has_button_per_lead(cfg, fig):
    menu = fig.layout.updatemenus[0]
    assert len(menu.buttons) == len(cfg.leads_h)
    for btn, lead in zip(menu.buttons, cfg.leads_h):
        vis, layout = btn.args[0]["visible"], btn.args[1]
        assert len(vis) == len(fig.data)
        shown = {i for i, v in enumerate(vis) if v}
        for i, t in enumerate(fig.data):
            if (t.meta or {}).get("kind") == "plan":
                assert (i in shown) == (t.meta["lead_h"] == lead)
        steps = layout["sliders[0].steps"]
        assert len(steps) == 1 + len(cfg.sources)


def test_slider_steps(cfg, fig):
    assert len(fig.layout.sliders[0].steps) == 1 + len(cfg.sources)
    assert fig.layout.sliders[0].steps[0].label == "ERA5"


def test_hindsight_beats_great_circle_along_track(cfg, plans):
    flight, truth, hindsight = plans["flight"], plans["truth"], plans["hindsight"]
    glat, glon = planner.great_circle_path(flight)
    gc = replay.replay(Plan(flight.flight_id, "gc", 0, tuple(glat), tuple(glon), 0.0), flight, truth)

    def mean_along(r):
        lat, lon, t = r.lat_deg, r.lon_deg, r.time
        brg = np.deg2rad(initial_bearing_deg(lat[:-1], lon[:-1], lat[1:], lon[1:]))
        u, v = truth.uv(lat[:-1], lon[:-1], t[:-1])
        return float(np.mean(u * np.sin(brg) + v * np.cos(brg)))

    assert flight.direction == "eastbound"
    assert mean_along(hindsight) > mean_along(gc)


def test_div_id(fig):
    assert 'id="fig-showcase-map"' in fig.to_html(div_id=sm.FIG_ID)


# ---- B4: offline basemap ----
import json
import re


def test_vendored_basemap_loads():
    topo = json.loads(sm.basemap_json())
    assert {"land", "coastlines", "countries"} <= set(topo["objects"])


def test_basemap_key_matches_figure_geo(fig):
    # plotly.js names the topojson "<scope>_<resolution>m"; the figure uses defaults
    scope = fig.layout.geo.scope or "world"
    res = fig.layout.geo.resolution or 110
    assert sm.BASEMAP_KEY == f"{scope}_{res}m"


def test_geo_assets_html_merges_asset():
    html = sm.geo_assets_html()
    assert html.startswith("<script>") and html.endswith("</script>")
    assert "window.PlotlyGeoAssets = window.PlotlyGeoAssets || {topojson: {}};" in html
    assert f"window.PlotlyGeoAssets.topojson.{sm.BASEMAP_KEY} = " in html


def test_write_html_puts_assets_before_figure(fig, tmp_path):
    out = tmp_path / "fig.html"
    sm.write_html(fig, out)
    text = out.read_text()
    assert text.lower().startswith("<!doctype html>") and 'charset="utf-8"' in text.lower()
    assert text.index("PlotlyGeoAssets") < text.index(f'id="{sm.FIG_ID}"')


def _render(path):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception as exc:  # Chrome not installed
            pytest.skip(f"Chrome unavailable: {exc}")
        page = browser.new_page()
        requests, errors = [], []
        page.on("request", lambda r: requests.append(r.url))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(path.as_uri())
        page.wait_for_timeout(2500)
        paths = page.evaluate("""['land', 'coastlines'].reduce((n, c) => n +
            [...document.querySelectorAll('.geo .layer.' + c + ' path')]
              .filter(p => (p.getAttribute('d') || '').length > 100).length, 0)""")
        browser.close()
    return requests, errors, paths


def _outside(requests):
    return [u for u in requests if not u.startswith(("file:", "data:"))]


def test_render_plain_write_html_fetches_cdn(fig, tmp_path):
    out = tmp_path / "plain.html"
    fig.write_html(out, include_plotlyjs=True, div_id=sm.FIG_ID)
    requests, _, _ = _render(out)
    assert any("cdn.plot.ly" in u for u in _outside(requests))


def test_render_write_html_is_offline_and_draws_land(fig, tmp_path):
    out = tmp_path / "offline.html"
    sm.write_html(fig, out)
    requests, errors, paths = _render(out)
    assert _outside(requests) == []
    assert errors == []
    assert paths > 0


# ---- B7: interaction and layout fixes ----
def test_lead_buttons_reset_background_to_era5(cfg, fig):
    for btn in fig.layout.updatemenus[0].buttons:
        args = btn.args
        assert args[1]["sliders[0].active"] == 0
        assert args[1]["sliders[0].steps"][0]["label"] == "ERA5"
        bg = args[0]
        assert bg["marker.color"][0] is not None and len(bg["marker.color"][0]) == len(fig.data[0].lat)
        assert "ERA5" in bg["marker.colorbar.title.text"][0]
        assert list(bg["marker.color"][0]) == list(fig.data[0].marker.color)
        assert len(args[0]["visible"]) == len(fig.data)


def test_every_plan_trace_in_legend_with_group(fig):
    for t in _plan_traces(fig):
        assert t.showlegend is True
        assert t.legendgroup


def test_hindsight_drawn_first_as_wide_translucent_band(cfg, fig):
    assert fig.data[0].meta["kind"] == "background"
    for lead in cfg.leads_h:
        traces = [t for t in _plan_traces(fig) if t.meta["lead_h"] == lead]
        assert traces[0].meta["source"] == "hindsight"
        assert traces[0].line.width >= 7 and traces[0].opacity <= 0.5
        assert all(t.line.width < traces[0].line.width for t in traces[1:])


def test_hindsight_names_equal_forecast_plan(cfg, plans, fig):
    h = plans["hindsight"]
    same = [p for p in plans["plans"] if p.source == h.source and p.lead_h == h.lead_h][0]
    for lead in cfg.leads_h:
        t = [t for t in _plan_traces(fig) if t.meta["lead_h"] == lead and t.meta["source"] == "hindsight"][0]
        twins = [p.source for p in plans["plans"]
                 if p.source in cfg.sources and p.lead_h == lead
                 and np.allclose(p.lat_deg, same.lat_deg) and np.allclose(p.lon_deg, same.lon_deg)]
        if twins:
            assert t.name.startswith("Hindsight plan (= ") and f"{lead} h" in t.name
            assert t.name in t.hovertext
        else:
            assert "=" not in t.name


def test_background_hover_and_colourscale(fig):
    bg = fig.data[0]
    assert "ERA5" in bg.hovertemplate and "m/s" in bg.hovertemplate
    assert "viridis" not in str(bg.marker.colorscale).lower()
    assert bg.marker.colorscale is not None


def _slow_hover_names(fig):
    return [s.label for s in fig.layout.sliders[0].steps]


def test_render_interactions_legend_and_layout(cfg, fig, tmp_path):
    pw = pytest.importorskip("playwright.sync_api")
    out = tmp_path / "b7.html"
    sm.write_html(fig, out)
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception as exc:
            pytest.skip(f"Chrome unavailable: {exc}")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.goto(out.as_uri())
        page.wait_for_selector(".legend .traces")
        page.wait_for_timeout(1500)
        n = len(cfg.sources) + 1
        title = lambda: page.text_content(".cbtitle")
        # desync sequence: slider to GraphCast at 24 h, then the 72 h button, background must be ERA5
        steps = page.locator(".slider-group .slider-label, .slider-group .slider-rect")  # noqa: F841
        page.evaluate("Plotly.relayout('fig-showcase-map', {'sliders[0].active': 2})")
        page.evaluate("""() => { const d = document.getElementById('fig-showcase-map');
            const s = d.layout.sliders[0].steps[2]; return Plotly.restyle(d, s.args[0], s.args[1]); }""")
        assert "GraphCast, lead 24 h" in title()
        page.evaluate("""() => { const d = document.getElementById('fig-showcase-map');
            const b = d.layout.updatemenus[0].buttons[%d]; return Plotly.update(d, b.args[0], b.args[1]); }"""
                      % list(cfg.leads_h).index(72))
        page.wait_for_timeout(500)
        assert "ERA5" in title()
        assert page.evaluate("document.getElementById('fig-showcase-map').layout.sliders[0].active") == 0
        page.evaluate("""() => { const d = document.getElementById('fig-showcase-map');
            const s = d.layout.sliders[0].steps[1]; return Plotly.restyle(d, s.args[0], s.args[1]); }""")
        assert "lead 72 h" in title()
        for i, lead in enumerate(cfg.leads_h):
            page.evaluate("""(i) => { const d = document.getElementById('fig-showcase-map');
                const b = d.layout.updatemenus[0].buttons[i]; return Plotly.update(d, b.args[0], b.args[1]); }""", i)
            page.wait_for_timeout(300)
            assert page.locator(".legend .traces").count() == n, lead
        boxes = {k: page.evaluate("""(sel) => [...document.querySelectorAll(sel)].map(e => {
            const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })""", sel)
                 for k, sel in {"title": ".gtitle", "menu": ".updatemenu-container", "legend": ".legend",
                                "slider": ".slider-container", "bar": ".colorbar"}.items()}
        browser.close()
    assert errors == []
    names = list(boxes)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            for r1 in boxes[names[a]]:
                for r2 in boxes[names[b]]:
                    assert r1[2] <= r2[0] or r2[2] <= r1[0] or r1[3] <= r2[1] or r2[3] <= r1[1], (names[a], names[b])


# ---- B7 attempt 2: narrow-width layout, wording, contrast ----
def _lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_legend_below_map_left_anchored_and_slider_below_legend(fig):
    lg, sl = fig.layout.legend, fig.layout.sliders[0]
    assert lg.orientation == "h" and lg.x == 0 and lg.xanchor == "left"
    assert lg.y < 0 and lg.yanchor == "top"
    assert sl.y < lg.y - 0.05  # room for a 2-row legend
    assert fig.layout.updatemenus[0].x >= 0.12  # clear of the "Lead time" label


def test_no_avoided_words_in_ui_text(fig):
    texts = [fig.data[0].hovertemplate, fig.data[0].marker.colorbar.title.text, fig.layout.title.text]
    texts += [s.args[0]["hovertemplate"][0] + s.args[0]["marker.colorbar.title.text"][0] for s in fig.layout.sliders[0].steps]
    assert all("analysis" not in t.lower() for t in texts)
    assert "ERA5 (truth)" in fig.data[0].hovertemplate


def test_hindsight_band_colour_unused_by_sources_and_dotted(cfg, fig):
    from regret.figures import style
    h = [t for t in _plan_traces(fig) if t.meta["source"] == "hindsight"][0]
    assert h.line.dash == "dot" and h.line.width >= 7
    assert h.line.color.startswith("rgba(255,127,14")
    assert h.line.color not in [style.colour(s) for s in cfg.sources]


# ---- B7 contrast tweak ----
def _grey(colour):
    h = colour.lstrip("#")
    return int(h[0:2], 16)


def _scale_grey_at(fig, speed):
    m = fig.data[0].marker
    pts = [(v, _grey(c)) for v, c in m.colorscale]
    x = (speed - m.cmin) / (m.cmax - m.cmin)
    return float(np.interp(x, [v for v, _ in pts], [g for _, g in pts]))


def test_background_scale_monotone_and_quiet_is_white(fig):
    greys = [_grey(c) for _, c in fig.data[0].marker.colorscale]
    assert all(a >= b for a, b in zip(greys, greys[1:]))  # luminance never rises with speed
    assert _scale_grey_at(fig, 5) >= 245  # quiet stays near white


def test_background_scale_grades_speed(fig):
    g = [(_scale_grey_at(fig, s),) * 3 for s in (20, 60, 100)]
    assert _ratio(g[0], g[1]) >= 1.3  # moderate clearly darker than the quiet edge
    assert _ratio(g[1], g[2]) >= 1.3  # jet core clearly darker than moderate


def test_persistence_has_white_halo_per_lead(cfg, fig):
    for lead in cfg.leads_h:
        idx = [i for i, t in enumerate(fig.data) if (t.meta or {}).get("source") == "persistence"
               and t.meta["lead_h"] == lead]
        assert len(idx) == 1
        line, halo = fig.data[idx[0]], fig.data[idx[0] - 1]
        assert halo.line.color == "#ffffff" and halo.line.width > line.line.width
        assert list(halo.lat) == list(line.lat) and list(halo.lon) == list(line.lon)
        assert halo.showlegend is False and halo.hoverinfo == "skip"
        assert halo.legendgroup == line.legendgroup and halo.visible == line.visible


def test_halo_follows_lead_buttons_and_legend_stays_five(cfg, fig):
    for btn, lead in zip(fig.layout.updatemenus[0].buttons, cfg.leads_h):
        vis = btn.args[0]["visible"]
        legend = [t for i, t in enumerate(fig.data) if vis[i] and t.showlegend]
        assert len(legend) == len(cfg.sources) + 1
        halos = [i for i, t in enumerate(fig.data) if t.hoverinfo == "skip"]
        assert halos and all(vis[i] == (fig.data[i + 1].meta["lead_h"] == lead) for i in halos)


def test_persistence_plan_is_dashed_not_dotted(fig):
    traces = [t for t in _plan_traces(fig) if t.meta["source"] == "persistence"]
    assert traces
    assert all(t.line.dash == "dash" for t in traces)
    others = [t for t in _plan_traces(fig) if t.meta["source"] not in ("persistence", "hindsight")]
    assert all(t.line.dash in (None, "solid") for t in others)


def test_era5_colourbar_title_says_truth(fig):
    assert "(truth)" in fig.data[0].marker.colorbar.title.text


def test_title_is_readable_not_raw_id(fig):
    text = fig.layout.title.text
    assert "JFK-LHR-20200209T0000" not in text
    assert "JFK→LHR, 2020-02-09 00:00 UTC" in text
    assert "over the 250 hPa wind at departure" in text
