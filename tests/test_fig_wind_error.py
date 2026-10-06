from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from regret.figures import style
from regret.figures.headline import SOURCE_LABELS
from regret.figures.wind_error import FIG_ID, build_wind_error

SOURCES = ["hres", "graphcast", "pangu"]
LEADS = [0, 24, 48]
FLIGHTS = ["F1", "F2"]


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for f in FLIGHTS:
        rows.append(dict(flight_id=f, source="truth", lead_h=0,
                         is_truth_optimised=True, wind_error_ms=0.0,
                         regret_fuel_kg=float(rng.random())))
        for s in SOURCES:
            for lead in LEADS:
                rows.append(dict(flight_id=f, source=s, lead_h=lead,
                                 is_truth_optimised=False,
                                 wind_error_ms=float(rng.random() * 5),
                                 regret_fuel_kg=float(rng.random() * 100)))
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def big() -> pd.DataFrame:
    """Full-scale shaped: heavy-tailed regret rising with wind error, persistence ~10x."""
    rng = np.random.default_rng(1)
    rows = []
    for s, scale in [("hres", 1.0), ("graphcast", 1.0), ("pangu", 1.1), ("persistence", 10.0)]:
        err = rng.gamma(2.0, 1.2 * scale, 600)
        reg = err * 4 * rng.lognormal(0, 1.0, 600)
        reg[0] = 3500.0 * scale  # one huge plan
        for i in range(600):
            rows.append(dict(flight_id=f"F{i % 50}", source=s, lead_h=[12, 24, 48, 72, 120][i % 5],
                             is_truth_optimised=False, wind_error_ms=float(err[i]),
                             regret_fuel_kg=float(reg[i])))
    rows.append(dict(flight_id="F0", source="truth", lead_h=0, is_truth_optimised=True,
                     wind_error_ms=0.0, regret_fuel_kg=0.0))
    return pd.DataFrame(rows)


def _kind(t):
    if t.name.endswith("(median)"):
        return "median"
    if t.name.endswith("(above range)"):
        return "pinned"
    return "points"


def traces(fig, kind, source=None):
    return [t for t in fig.data if _kind(t) == kind and (source is None or t.meta == source)]


def panel_forecast(df):
    return df[~df.is_truth_optimised & (df.source != "persistence")]


def test_points_trace_per_source_with_style(df):
    fig = build_wind_error(df)
    assert [t.name for t in traces(fig, "points")] == ["IFS HRES", "GraphCast", "Pangu-Weather"]
    for t in fig.data:
        assert t.marker.color == style.colour(t.meta)
        assert t.marker.symbol == style.symbol(t.meta)
        assert t.meta in SOURCES
    for t in traces(fig, "points"):
        assert t.mode == "markers" and t.marker.opacity <= 0.3 and t.marker.size <= 5


def test_no_plan_lost_at_full_scale(big):
    fig = build_wind_error(big)
    n = int((~big.is_truth_optimised).sum())
    plotted = sum(len(t.x) for t in traces(fig, "points"))
    pinned = sum(len(t.x) for t in traces(fig, "pinned"))
    assert plotted + pinned == n
    assert pinned >= 4  # at least the huge plans


def test_no_plan_lost_on_small_fixture(df):
    fig = build_wind_error(df)
    plotted = sum(len(t.x) for t in traces(fig, "points"))
    pinned = sum(len(t.x) for t in traces(fig, "pinned"))
    assert plotted + pinned == int((~df.is_truth_optimised).sum())
    assert "truth" not in {t.meta for t in fig.data}


def test_pinned_markers_at_top_edge_with_true_values(big):
    fig = build_wind_error(big)
    for ax, srcs in (("y", {"hres", "graphcast", "pangu"}), ("y2", {"persistence"})):
        top = fig.layout["yaxis" + ("" if ax == "y" else "2")].range[1]
        pinned = [t for t in traces(fig, "pinned") if t.yaxis == ax]
        assert {t.meta for t in pinned} <= srcs
        for t in pinned:
            assert all(top * 0.9 <= y <= top for y in t.y)
            assert t.cliponaxis is False
            assert all(c[0] is not None for c in t.customdata)
            assert "true" in t.hovertemplate.lower()
        pts = [t for t in traces(fig, "points") if t.yaxis == ax]
        assert all(max(t.y) <= top for t in pts)
    hres = traces(fig, "pinned", "hres")[0]
    assert max(c[3] for c in hres.customdata) == pytest.approx(3500.0)


def test_cap_is_data_derived_percentile(big):
    fig = build_wind_error(big)
    pan = panel_forecast(big)
    top = fig.layout.yaxis.range[1]
    p99 = float(np.percentile(pan.regret_fuel_kg, 99))
    assert p99 <= top <= p99 * 1.25
    assert fig.layout.yaxis.range[0] <= 0


def test_annotation_count_and_max(big):
    fig = build_wind_error(big)
    texts = [a.text for a in fig.layout.annotations]
    pan = panel_forecast(big)
    top = fig.layout.yaxis.range[1]
    above = pan[pan.regret_fuel_kg > top]
    ann = [t for t in texts if "above" in t and "top edge" in t]
    assert len(ann) == 2  # one per panel
    assert any(f"{len(above)} plans above" in t.replace("<br>", " ") and f"{above.regret_fuel_kg.max():,.0f} kg" in t
               for t in ann)


def test_no_annotation_when_nothing_above_cap():
    d = pd.DataFrame([
        dict(flight_id="F", source="hres", lead_h=24, is_truth_optimised=False,
             wind_error_ms=float(i), regret_fuel_kg=10.0) for i in range(20)])
    fig = build_wind_error(d)
    assert not [a for a in fig.layout.annotations if "top edge" in a.text]
    assert traces(fig, "pinned") == []


def test_medians_per_forecast_source_common_bins_and_min_count(big):
    fig = build_wind_error(big)
    med = traces(fig, "median")
    assert [t.meta for t in med] == ["hres", "graphcast", "pangu"]
    pan = panel_forecast(big)
    edges = np.quantile(pan.wind_error_ms, np.linspace(0, 1, 9))
    for t in med:
        assert t.mode == "lines+markers" and t.line.width >= 3
        assert t.xaxis == "x"
        rows = pan[pan.source == t.meta]
        b = np.clip(np.digitize(rows.wind_error_ms, edges[1:-1]), 0, 7)
        exp = [(float(g.wind_error_ms.median()), float(g.regret_fuel_kg.median()))
               for _, g in rows.groupby(b) if len(g) >= 15]
        assert list(zip(t.x, t.y)) == pytest.approx(exp)
        assert len(exp) >= 6
        assert t.y[-1] > t.y[0]
    assert "median" in med[0].name


def test_median_bins_below_15_dropped():
    rng = np.random.default_rng(3)
    rows = [dict(flight_id="F", source=s, lead_h=24, is_truth_optimised=False,
                 wind_error_ms=float(e), regret_fuel_kg=float(e * 2))
            for s in ("hres", "graphcast") for e in rng.random(160) * 10]
    # pangu has only 4 points (< the 5-point floor), all in the top bin
    rows += [dict(flight_id="F", source="pangu", lead_h=24, is_truth_optimised=False,
                  wind_error_ms=9.9 + i * 0.001, regret_fuel_kg=1.0) for i in range(4)]
    fig = build_wind_error(pd.DataFrame(rows))
    assert all(len(t.x) == 0 for t in traces(fig, "median", "pangu"))  # legend-only stand-in
    assert len(traces(fig, "median", "hres")) == 1


def test_persistence_in_own_panel_with_own_axes(big):
    fig = build_wind_error(big)
    by = {t.meta: t for t in traces(fig, "points")}
    assert by["hres"].xaxis == "x" and by["persistence"].xaxis == "x2"
    assert by["hres"].yaxis == "y" and by["persistence"].yaxis == "y2"
    assert traces(fig, "median", "persistence") == []
    assert fig.layout.xaxis.matches is None and fig.layout.yaxis2.matches is None
    assert fig.layout.xaxis.type in (None, "linear")
    assert "Persistence baseline" in [a.text for a in fig.layout.annotations]
    assert fig.layout.title.text


def test_axis_titles(df):
    fig = build_wind_error(df)
    for ax in ("xaxis", "xaxis2"):
        assert fig.layout[ax].title.text == "wind error (m/s)"
    assert fig.layout.yaxis.title.text == "fuel regret (kg)"
    assert fig.layout.yaxis2.title.text == "fuel regret (kg)"


def test_hover_uses_source_labels(big):
    fig = build_wind_error(big)
    for t in traces(fig, "points") + traces(fig, "pinned"):
        h = t.hovertemplate.lower()
        assert "flight" in h and "source" in h and "lead (h)" in h
        assert "wind error" in h and "fuel regret" in h
        assert {c[1] for c in t.customdata} == {SOURCE_LABELS[t.meta]}
        assert t.customdata[0][2] in (12, 24, 48, 72, 120)


def test_median_labelled_as_medians_not_means(big):
    fig = build_wind_error(big)
    assert [t.name for t in traces(fig, "median")] == [
        "IFS HRES (median)", "GraphCast (median)", "Pangu-Weather (median)"]
    assert any("median" in a.text.lower() and "lines" in a.text.lower() for a in fig.layout.annotations)


def test_legend_horizontal(df):
    assert build_wind_error(df).layout.legend.orientation == "h"


def test_html_has_stable_div_id(df):
    assert 'id="fig-wind-error"' in build_wind_error(df).to_html(div_id=FIG_ID)


def test_cap_annotations_outside_plot_area(big):
    fig = build_wind_error(big)
    ann = [a for a in fig.layout.annotations if "top edge" in a.text]
    assert len(ann) == 2
    for a, ax in zip(ann, ("yaxis", "yaxis2")):
        dom = fig.layout[ax].domain
        assert a.yref == "paper"
        assert a.y >= dom[1] or a.y <= dom[0]
        assert a.bgcolor is None
        # anchored so the text body stays outside the domain (above: anchor bottom, below: anchor top)
        assert (a.y >= dom[1] and a.yanchor == "bottom") or (a.y <= dom[0] and a.yanchor == "top")


FIXTURE_PARQUET = "tests/fixture_results/regret.parquet"
FULL_PARQUET = "data/results/regret.parquet"
LABELS = [SOURCE_LABELS[s] for s in ("hres", "graphcast", "pangu", "persistence")]


def _legend_names(fig):
    return {t.name for t in fig.data if t.showlegend is not False}


def _legend_groups(fig):
    return {t.legendgroup for t in fig.data if t.showlegend is not False}


def test_fixture_every_source_has_median_with_points_and_two_bins():
    d = pd.read_parquet(FIXTURE_PARQUET)
    fig = build_wind_error(d)
    med = traces(fig, "median")
    fc = d[~d.is_truth_optimised & (d.source != "persistence")]
    assert {t.meta for t in med} == set(fc.source.unique())
    assert all(len(t.x) >= 1 for t in med)
    assert max(len(t.x) for t in med) == 2


def test_legend_entry_for_every_forecast_source_fixture_and_synthetic(df, big):
    for d in (pd.read_parquet(FIXTURE_PARQUET), df, big):
        fig = build_wind_error(d)
        srcs = set(d[~d.is_truth_optimised].source)
        assert srcs <= _legend_groups(fig)
        for s in srcs - {"persistence"}:
            assert any(t.legendgroup == s and t.showlegend is not False and "median" in t.name
                       for t in fig.data)


def test_legend_entry_even_when_no_median_points():
    rng = np.random.default_rng(3)
    rows = [dict(flight_id="F", source=s, lead_h=24, is_truth_optimised=False,
                 wind_error_ms=float(e), regret_fuel_kg=float(e * 2))
            for s in ("hres", "graphcast") for e in rng.random(160) * 10]
    rows += [dict(flight_id="F", source="pangu", lead_h=24, is_truth_optimised=False,
                  wind_error_ms=9.9 + i * 0.001, regret_fuel_kg=1.0) for i in range(4)]
    fig = build_wind_error(pd.DataFrame(rows))
    assert [t.name for t in fig.data if t.legendgroup == "pangu" and t.showlegend is not False] == [
        "Pangu-Weather (median)"]


def test_full_results_bins_and_medians_unchanged():
    import os
    if not os.path.exists(FULL_PARQUET):
        pytest.skip("full results absent")
    d = pd.read_parquet(FULL_PARQUET)
    fig = build_wind_error(d)
    med = {t.meta: t for t in traces(fig, "median")}
    assert all(len(t.x) == 8 for t in med.values())
    for s, kg in (("hres", 226.8), ("graphcast", 131.1), ("pangu", 158.8)):
        assert round(med[s].y[-1], 1) == kg
    assert set(_legend_groups(fig)) >= {"hres", "graphcast", "pangu", "persistence"}


def _fc_panel(d):
    return d[~d.is_truth_optimised & (d.source != "persistence")]


def test_fixture_every_source_median_is_a_line():
    fig = build_wind_error(pd.read_parquet(FIXTURE_PARQUET))
    med = traces(fig, "median")
    assert len(med) == 3
    assert all(len(t.x) >= 2 for t in med)


def test_per_bin_minimum_scales_with_data():
    from regret.figures.wind_error import _min_bin_points, _n_bins
    fx = _fc_panel(pd.read_parquet(FIXTURE_PARQUET))
    assert _min_bin_points(fx, _n_bins(fx)) == 7
    import os
    if not os.path.exists(FULL_PARQUET):
        pytest.skip("full results absent")
    full = _fc_panel(pd.read_parquet(FULL_PARQUET))
    assert _n_bins(full) == 8
    assert _min_bin_points(full, 8) == 15
