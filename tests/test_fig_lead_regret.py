"""Regret vs lead time figure on a small synthetic table shaped like the CONTRACTS section 4 schema."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from regret.figures import lead_regret
from regret.figures.lead_regret import FIG_ID, build_lead_regret

# regret_fuel_kg per flight for (source, lead_h)
LEADS = (6, 12)
SOURCES = ("hres", "persistence")
REGRET = {  # flight -> {(source, lead): regret}
    "F1": {("hres", 6): 0.0, ("hres", 12): 5.0, ("persistence", 6): 10.0, ("persistence", 12): 20.0},
    "F2": {("hres", 6): 10.0, ("hres", 12): 15.0, ("persistence", 6): 30.0, ("persistence", 12): 40.0},
    "F3": {("hres", 6): 4.0, ("hres", 12): 8.0, ("persistence", 6): 6.0, ("persistence", 12): 12.0},
    "F4": {("hres", 6): 8.0, ("hres", 12): 12.0, ("persistence", 6): 10.0, ("persistence", 12): 14.0},
}
DIRECTION = {"F1": "eastbound", "F2": "eastbound", "F3": "westbound", "F4": "westbound"}


def make_table() -> pd.DataFrame:
    rows = []
    for fid, reg in REGRET.items():
        plans = [("truth", 0, 0.0)] + [(s, h, reg[(s, h)]) for s in SOURCES for h in LEADS]
        for src, lead, r in plans:
            fuel = 1000.0 + r
            rows.append(
                dict(
                    flight_id=fid, direction=DIRECTION[fid],
                    departure_time=pd.Timestamp("2020-02-09"),
                    source=src, lead_h=lead,
                    is_truth_optimised=src == "truth", is_hindsight=src == "truth",
                    fuel_kg=fuel, time_min=fuel / 10, co2_kg=3.16 * fuel,
                    regret_fuel_kg=r, regret_fuel_pct=r / 10, regret_time_min=r / 10,
                    regret_co2_kg=3.16 * r,
                    wind_error_ms=0.0, fuel_flow_min_kgh=1.0, fuel_flow_max_kgh=2.0,
                    optimiser_gap_fuel_kg=float("nan"),
                )
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fig() -> go.Figure:
    return build_lead_regret(make_table())


def _xaxis(fig, trace):
    return trace.xaxis


def lines(fig):
    return [t for t in fig.data if t.mode and "lines" in t.mode and t.fill != "toself"]


def bands(fig):
    return [t for t in fig.data if t.fill == "toself"]


def test_fig_id():
    assert FIG_ID == "fig-lead-regret"


TOP = {"y", "y2"}
BOTTOM = {"y3", "y4"}
DIR_OF_X = {"x": "eastbound", "x2": "westbound", "x3": "eastbound", "x4": "westbound"}


def test_four_subplots_east_west_columns(fig):
    assert {t.xaxis for t in lines(fig)} <= {"x", "x2", "x3", "x4"}
    assert {t.xaxis for t in bands(fig)} <= {"x", "x2", "x3", "x4"}
    titles = [a.text for a in fig.layout.annotations]
    assert "Eastbound" in titles and "Westbound" in titles


def test_persistence_only_on_bottom_row_others_only_on_top(fig):
    for t in lines(fig) + bands(fig):
        if t.legendgroup == "persistence":
            assert t.yaxis in BOTTOM
        else:
            assert t.yaxis in TOP


def test_one_line_and_one_band_per_source_per_direction_panel(fig):
    for src in SOURCES:
        for axis in (("x", "y"), ("x2", "y2")) if src != "persistence" else (("x3", "y3"), ("x4", "y4")):
            ls = [t for t in lines(fig) if t.legendgroup == src and (t.xaxis, t.yaxis) == axis]
            bs = [t for t in bands(fig) if t.legendgroup == src and (t.xaxis, t.yaxis) == axis]
            assert len(ls) == len(bs) == 1


def test_lead_ticks(fig):
    for name in ("xaxis", "xaxis2", "xaxis3", "xaxis4"):
        assert list(fig.layout[name].tickvals) == [12, 24, 48, 72, 120]


def test_ci_label_is_annotation_not_legend_entry(fig):
    assert not [t for t in fig.data if t.showlegend and t.name and "CI" in t.name]
    assert not [t for t in fig.data if t.legendgroup == "ci"]
    assert [a.text for a in fig.layout.annotations if "90% CI of the mean" in a.text]


def test_legend_horizontal(fig):
    assert fig.layout.legend.orientation == "h"


def test_rows_share_y_between_columns(fig):
    assert fig.layout.yaxis2.matches == "y"
    assert fig.layout.yaxis4.matches == "y3"
    assert fig.layout.yaxis3.matches is None


def test_legend_toggles_source_in_all_panels(fig):
    for src in SOURCES:
        shown = [t for t in lines(fig) if t.legendgroup == src and t.showlegend]
        assert len(shown) == 1  # one legend entry per source
    assert all(t.showlegend is False for t in bands(fig))


def test_axis_titles_have_units(fig):
    assert "h" in fig.layout.xaxis3.title.text and "h" in fig.layout.xaxis4.title.text
    assert "kg" in fig.layout.yaxis.title.text and "kg" in fig.layout.yaxis3.title.text


def test_top_row_range_set_by_forecast_sources_at_full_scale():
    df = make_table()
    df.loc[df.source == "persistence", ["regret_fuel_kg"]] *= 1000.0
    fig = build_lead_regret(df)
    top = [t for t in lines(fig) + bands(fig) if t.yaxis in TOP]
    pers = [t for t in lines(fig) + bands(fig) if t.yaxis in BOTTOM]
    assert top and pers
    assert max(max(t.y) for t in top) < min(min(t.y) for t in pers)


def test_new_source_lands_in_top_row():
    df = make_table()
    extra = df[df.source == "hres"].copy()
    extra["source"] = "neuralgcm"
    fig = build_lead_regret(pd.concat([df, extra]))
    assert {t.yaxis for t in lines(fig) if t.legendgroup == "neuralgcm"} == TOP


def test_known_mean_in_right_trace(fig):
    # eastbound hres: lead 6 regrets {0, 10} -> mean 5; lead 12 {5, 15} -> 10
    east = [t for t in lines(fig) if t.xaxis == "x" and t.legendgroup == "hres"][0]
    assert list(east.x) == [6, 12]
    assert list(east.y) == pytest.approx([5.0, 10.0])
    # westbound persistence: lead 6 {6, 10} -> 8
    west = [t for t in lines(fig) if t.xaxis == "x4" and t.legendgroup == "persistence"][0]
    assert west.y[0] == pytest.approx(8.0)


def test_band_spans_ci(fig):
    east_line = [t for t in lines(fig) if t.xaxis == "x" and t.legendgroup == "hres"][0]
    east_band = [t for t in bands(fig) if t.xaxis == "x" and t.legendgroup == "hres"][0]
    assert len(east_band.x) == 2 * len(east_line.x)
    # band y covers the mean at each lead
    assert min(east_band.y) <= min(east_line.y) and max(east_band.y) >= max(east_line.y)


def test_labels_use_context_terms(fig):
    names = {t.name for t in lines(fig)}
    assert names == {lead_regret.SOURCE_LABELS["hres"], lead_regret.SOURCE_LABELS["persistence"]}


def test_html_has_stable_div_id(fig):
    assert 'id="fig-lead-regret"' in fig.to_html(div_id=FIG_ID)
