from __future__ import annotations

import pandas as pd
import pytest

from regret.figures.sanity import FIG_ID, build_sanity

COLS = ["flight_id", "direction", "source", "lead_h", "is_truth_optimised",
        "time_min", "fuel_flow_min_kgh", "fuel_flow_max_kgh",
        "optimiser_gap_fuel_kg"]
NAN = float("nan")
# (flight, direction, source, lead, truth, time, ffmin, ffmax, gap)
ROWS = [
    ("E1", "eastbound", "truth", 0, True, 300.0, 1000.0, 2000.0, NAN),
    ("E1", "eastbound", "hres", 0, False, 310.0, 1100.0, 2100.0, 40.0),
    ("E1", "eastbound", "pangu", 0, False, 320.0, 1200.0, 2200.0, NAN),
    ("W1", "westbound", "truth", 0, True, 400.0, 900.0, 1900.0, NAN),
    ("W1", "westbound", "hres", 0, False, 410.0, 950.0, 1950.0, 10.0),
    ("W1", "westbound", "pangu", 0, False, 420.0, 980.0, 1980.0, 20.0),
]


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(ROWS, columns=COLS)


def _by_name(fig, name):
    return [t for t in fig.data if t.name == name]


def test_four_subplots_with_titles(df):
    fig = build_sanity(df)
    titles = [a.text for a in fig.layout.annotations][:4]  # later annotations are notes
    assert titles == [
        "replay time by direction",
        "fuel-flow range",
        "optimiser-gap count",
        "optimiser-gap size",
    ]
    assert {t.xaxis for t in fig.data} == {"x", "x2", "x3", "x4"}


def test_time_traces_hold_direction_values(df):
    fig = build_sanity(df)
    (east,) = _by_name(fig, "eastbound")
    (west,) = _by_name(fig, "westbound")
    assert sorted(east.y) == [300.0, 310.0, 320.0]
    assert sorted(west.y) == [400.0, 410.0, 420.0]
    assert east.boxmean is not None  # mean/median visible


def test_fuel_flow_traces(df):
    fig = build_sanity(df)
    (lo,) = _by_name(fig, "minimum fuel flow")
    (hi,) = _by_name(fig, "maximum fuel flow")
    assert sorted(lo.y) == [900.0, 950.0, 980.0, 1000.0, 1100.0, 1200.0]
    assert max(hi.y) == 2200.0


def test_gap_count_and_size(df):
    fig = build_sanity(df)
    (count,) = [t for t in fig.data if t.xaxis == "x3"]
    (size,) = [t for t in fig.data if t.xaxis == "x4"]
    assert list(count.x) == ["hres", "pangu"]  # ids stay the data; labels are tick text
    for ax in (fig.layout.xaxis3, fig.layout.xaxis4):
        assert list(ax.tickvals) == ["hres", "pangu"]
        # long labels wrap onto two lines so horizontal ticks do not collide
        assert [t.replace("<br>", "") .replace(" ", "") for t in ax.ticktext] == ["IFSHRES", "Pangu-Weather"]
    assert list(count.y) == [2, 1]
    assert list(size.y) == [25.0, 20.0]  # mean kg per source


def test_gap_all_zero_sources_still_listed(df):
    df["optimiser_gap_fuel_kg"] = NAN
    fig = build_sanity(df)
    (count,) = [t for t in fig.data if t.xaxis == "x3"]
    assert list(count.y) == [0, 0]


def test_axis_titles_have_units(df):
    fig = build_sanity(df)
    assert fig.layout.yaxis.title.text == "replay time (min)"
    assert fig.layout.yaxis2.title.text == "fuel flow (kg/h)"
    assert fig.layout.yaxis3.title.text == "gap count (plans)"
    assert fig.layout.yaxis4.title.text == "mean gap size (kg)"


def test_div_id(df):
    assert FIG_ID == "fig-sanity"
    assert 'id="fig-sanity"' in build_sanity(df).to_html(div_id=FIG_ID)


def _texts(fig):
    return [a.text for a in fig.layout.annotations]


def test_explicit_height_and_spacing(df):
    fig = build_sanity(df)
    assert fig.layout.height >= 650
    assert fig.layout.margin.t is not None and fig.layout.margin.b is not None
    # plot area at the explicit height: both rows >= 180 px
    inner = fig.layout.height - fig.layout.margin.t - fig.layout.margin.b
    top = fig.layout.yaxis.domain
    bottom = fig.layout.yaxis3.domain
    assert (top[1] - top[0]) * inner >= 180
    assert (bottom[1] - bottom[0]) * inner >= 180
    assert top[0] - bottom[1] >= 0.1  # room for x tick labels, axis title and subplot title


def test_source_ticks_horizontal(df):
    fig = build_sanity(df)
    assert fig.layout.xaxis3.tickangle == 0
    assert fig.layout.xaxis4.tickangle == 0


def test_zero_gap_sources_labelled(df):
    df["optimiser_gap_fuel_kg"] = NAN
    df.loc[df["source"] == "hres", "optimiser_gap_fuel_kg"] = 5.0
    fig = build_sanity(df)
    zero = [t for t in _texts(fig) if t == "0 gaps"]
    assert len(zero) == 2  # pangu in both gap panels, hres has gaps
    xs = [a.x for a in fig.layout.annotations if a.text == "0 gaps"]
    assert xs == ["pangu", "pangu"]


def test_gap_size_bars_show_n(df):
    fig = build_sanity(df)
    (size,) = [t for t in fig.data if t.xaxis == "x4"]
    assert list(size.text) == ["n=2", "n=1"]


def test_flat_max_annotation(df):
    fig = build_sanity(df)
    assert any("max equal for all plans" in t for t in _texts(fig))


def test_box_traces_neutral_colours(df):
    from regret.figures import style
    fig = build_sanity(df)
    boxes = [t for t in fig.data if t.type == "box"]
    colours = [t.marker.color for t in boxes]
    assert all(c is not None for c in colours)
    assert not set(colours) & set(style.SOURCE_COLOURS.values())


def test_box_hover_has_units(df):
    fig = build_sanity(df)
    (east,) = _by_name(fig, "eastbound")
    (lo,) = _by_name(fig, "minimum fuel flow")
    assert "min" in east.hovertemplate and ":.1f" in east.hovertemplate
    assert "kg/h" in lo.hovertemplate and ".0f" in lo.hovertemplate


def test_gap_count_axis_has_integer_ticks(df):
    fig = build_sanity(df)
    ax = fig.layout.yaxis3
    assert ax.dtick == 1 and ax.tick0 == 0
