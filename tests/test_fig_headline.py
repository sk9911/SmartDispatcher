"""Headline table figure on a small synthetic table shaped like the CONTRACTS section 4 schema."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from regret.figures import headline

# fuel_kg per flight for (source, lead_h); "truth" is the truth-optimised plan.
PLANS = [("truth", 0), ("hres", 6), ("hres", 12), ("persistence", 6), ("persistence", 12)]
FUEL = {
    "F1": [100, 100, 105, 110, 120],
    "F2": [200, 190, 210, 200, 205],
    "F3": [300, 310, 300, 320, 300],
    "F4": [400, 395, 395, 410, 420],
}
DIRECTION = {"F1": "eastbound", "F2": "eastbound", "F3": "westbound", "F4": "westbound"}


def make_table() -> pd.DataFrame:
    rows = []
    for fid, fuels in FUEL.items():
        best = min(fuels)
        winner = fuels.index(best)
        for i, ((src, lead), fuel) in enumerate(zip(PLANS, fuels)):
            truth = src == "truth"
            rows.append(
                dict(
                    flight_id=fid, direction=DIRECTION[fid],
                    departure_time=pd.Timestamp("2020-02-09"),
                    source=src, lead_h=lead,
                    is_truth_optimised=truth, is_hindsight=i == winner,
                    fuel_kg=float(fuel), time_min=fuel / 10, co2_kg=3.16 * fuel,
                    regret_fuel_kg=float(fuel - best),
                    regret_fuel_pct=100.0 * (fuel - best) / best,
                    regret_time_min=(fuel - best) / 10,
                    regret_co2_kg=3.16 * (fuel - best),
                    wind_error_ms=0.0, fuel_flow_min_kgh=1.0, fuel_flow_max_kgh=2.0,
                    optimiser_gap_fuel_kg=np.nan,
                )
            )
    df = pd.DataFrame(rows)
    df["lead_h"] = df["lead_h"].astype("int64")
    return df


@pytest.fixture
def fig() -> go.Figure:
    return headline.build_headline(make_table())


def tables(fig: go.Figure) -> list:
    assert len(fig.data) == 2 and all(isinstance(t, go.Table) for t in fig.data)
    return list(fig.data)


def table(fig: go.Figure) -> go.Table:
    """Both bands merged into one table view (header, cells, columnwidth concatenated)."""
    a, b = tables(fig)
    return go.Table(
        header=dict(values=list(a.header.values) + list(b.header.values)),
        cells=dict(values=[list(c) for c in a.cells.values] + [list(c) for c in b.cells.values],
                   height=a.cells.height),
        columnwidth=list(a.columnwidth) + list(b.columnwidth),
    )


def test_header_lists_the_contract_columns(fig):
    header = " | ".join(str(h) for h in table(fig).header.values)
    for metric in ("Fuel (kg)", "Fuel (%)", "Time (min)", "CO\u2082 (kg)"):
        for stat in ("mean (90% CI)", "median", "p90"):
            assert f"{metric}<br>{stat}" in header
    assert "Zero-regret<br>share" in header


def column(fig: go.Figure, name_part: str) -> list:
    for t in tables(fig):
        for i, h in enumerate(t.header.values):
            if name_part in h:
                return list(t.cells.values[i])
    raise AssertionError(name_part)


def test_one_row_per_source_and_lead(fig):
    assert list(zip(column(fig, "Forecast source"), column(fig, "Lead time"))) == [
        ("IFS HRES", 6), ("IFS HRES", 12), ("Persistence baseline", 6), ("Persistence baseline", 12)
    ]


def test_known_mean_in_the_right_cell(fig):
    # HRES at 6 h: regrets 0, 0, 10, 0 kg over the four flights -> mean 2.5 kg
    cell = column(fig, "Fuel (kg)<br>mean")[0]
    assert cell.startswith("2.5<br>[")
    # median 0, p90 of [0,0,0,10] = 7 (linear interpolation)
    assert column(fig, "Fuel (kg)<br>median")[0] == "0.0"
    assert column(fig, "Fuel (kg)<br>p90")[0] == "7.0"
    # persistence at 12 h: regrets 20, 15, 0, 25 -> mean 15
    assert column(fig, "Fuel (kg)<br>mean")[3].startswith("15.0<br>[")
    # zero-regret share: HRES 6 h is exactly zero on 3 of 4 flights
    assert column(fig, "Zero-regret<br>share")[0] == "75%"


def test_ci_bracket_format(fig):
    import re
    assert re.fullmatch(r"-?\d+\.\d<br>\[-?\d+\.\d, -?\d+\.\d\]", column(fig, "Fuel (kg)<br>mean")[0])


def test_co2_header_uses_unicode_subscript(fig):
    assert any("CO\u2082" in h for h in table(fig).header.values)


def test_html_has_stable_div_id(fig):
    assert 'id="fig-headline"' in fig.to_html(div_id=headline.FIG_ID)


def test_column_widths_and_two_line_headers_are_set(fig):
    t = table(fig)
    assert len(t.columnwidth) == len(t.header.values) == len(t.cells.values)
    assert all("<br>" in h for a in tables(fig) for h in a.header.values[2:])


def test_mean_cells_use_fixed_decimals():
    assert headline._num(53.0, 1) == "53.0"
    assert headline._ci(29.4, 6.9, 53.0, 1) == "29.4<br>[6.9, 53.0]"


def test_small_nonzero_fuel_pct_does_not_render_as_zero():
    df = make_table()
    df.loc[~df["is_truth_optimised"], "regret_fuel_pct"] = 0.004
    t = headline.build_headline(df)
    assert column(t, "Fuel (%)<br>median")[0] == "0.004"


def est_px(line: str) -> float:
    return len(line) * 7.5 + 16


def _col_names(t):
    return [h.split("<br>")[0] for h in t.header.values]


def test_mean_cells_are_exactly_two_lines_and_others_one(fig):
    t = table(fig)
    for h, col in zip(t.header.values, t.cells.values):
        for v in col:
            n = str(v).count("<br>")
            assert n == (1 if "mean (90% CI)" in h else 0), (h, v)


def synthetic_full_scale(fig_table):
    """Copy of the fixture table with full-scale CO2 / fuel strings in every mean cell."""
    t = go.Table(fig_table)
    vals = [list(c) for c in t.cells.values]
    for i, h in enumerate(t.header.values):
        if "CO\u2082" in h and "mean" in h:
            vals[i] = ["12071.9<br>[6083.4, 18755.4]"] * len(vals[i])
        if "Fuel (kg)" in h and "mean" in h:
            vals[i] = ["3820.2<br>[2100.0, 5600.0]"] * len(vals[i])
    return t, vals


def _assert_fits(fig, overrides=None):
    for t in tables(fig):
        vals = [list(c) for c in t.cells.values]
        if overrides:
            for i, h in enumerate(t.header.values):
                for key, v in overrides.items():
                    if key in h and "mean" in h:
                        vals[i] = [v] * len(vals[i])
        for h, w in zip(t.header.values, t.columnwidth):
            for line in h.split("<br>"):
                assert est_px(line) <= w, (line, w)
        for i, col in enumerate(vals):
            for v in col:
                for line in str(v).split("<br>"):
                    assert est_px(line) <= t.columnwidth[i], (line, t.columnwidth[i])


def test_every_cell_line_fits_its_column_on_fixture_results():
    import pathlib
    df = pd.read_parquet(pathlib.Path(__file__).parent / "fixture_results" / "regret.parquet")
    _assert_fits(headline.build_headline(df))


FULL_SCALE = {"CO\u2082": "12071.9<br>[6083.4, 18755.4]", "Fuel (kg)": "3820.2<br>[2100.0, 5600.0]"}


def test_every_cell_line_fits_its_column_at_full_scale(fig):
    _assert_fits(fig, FULL_SCALE)


def test_two_bands_with_the_right_column_sets(fig):
    a, b = tables(fig)
    heads = lambda t: " ".join(t.header.values)
    assert "Fuel (kg)" in heads(a) and "Fuel (%)" in heads(a) and "Time" not in heads(a)
    assert "Time (min)" in heads(b) and "CO\u2082 (kg)" in heads(b) and "Fuel" not in heads(b)
    for t in (a, b):
        assert t.header.values[0] == "Forecast source" and t.header.values[1].startswith("Lead time")
    assert sum("Zero-regret" in h for t in (a, b) for h in t.header.values) == 1
    assert "CO2" not in heads(b)


def test_each_band_width_fits_the_report_output_area(fig):
    for t in tables(fig):
        assert sum(t.columnwidth) + 2 * headline.MARGIN <= headline.REPORT_WIDTH
    assert fig.layout.width <= headline.REPORT_WIDTH


@pytest.mark.parametrize("n", [20, 25])
def test_layout_height_fits_every_row_in_both_bands(n):
    h = headline.layout_height(n)
    assert h >= 2 * (headline.HEADER_H + n * headline.ROW_H) + 2 * headline.MARGIN


def test_bands_are_stacked_in_separate_domains_that_hold_every_row(fig):
    a, b = tables(fig)
    n = len(a.cells.values[0])
    H = fig.layout.height
    assert a.domain.y[0] >= b.domain.y[1]  # band 1 above band 2
    for t in (a, b):
        assert (t.domain.y[1] - t.domain.y[0]) * H >= headline.HEADER_H + n * headline.ROW_H


def test_layout_height_holds_the_fixture_figure(fig):
    n = len(tables(fig)[0].cells.values[0])
    assert fig.layout.height == headline.layout_height(n)


FONT_LINE = 16


def test_row_and_header_height_hold_two_lines(fig):
    t = tables(fig)[0]
    assert t.cells.height >= 2 * FONT_LINE + 8
    assert t.header.height >= 2 * FONT_LINE + 8


def test_neuralgcm_label():
    assert headline.SOURCE_LABELS["neuralgcm"] == "NeuralGCM"
