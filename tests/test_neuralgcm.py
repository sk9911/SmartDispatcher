"""NeuralGCM add-on compute (SPEC 1.5): five sources planned 12-hourly on the matched flights."""
from __future__ import annotations

import dataclasses

import pandas as pd
import pytest
import xarray as xr

from regret import cli, neuralgcm, sources
from regret.config import get_config, matched_flights
from regret.regret import COLUMNS
from regret.figures import headline
from regret.figures.neuralgcm import FIG_ID, build_neuralgcm
from tests.test_fig_lead_regret import make_table

FIXTURE = get_config("fixture")
LEADS = (24, 120)


@pytest.fixture(scope="module")
def cfg(tmp_path_factory):
    """Fixture config with a synthetic neuralgcm cache (a copy of the hres fixture)."""
    d = tmp_path_factory.mktemp("cache")
    for name in ("era5", "hres", "graphcast", "pangu"):
        (d / f"{name}.zarr").symlink_to((FIXTURE.cache_dir / f"{name}.zarr").resolve())
    xr.open_zarr(FIXTURE.cache_dir / "hres.zarr").load().to_zarr(d / "neuralgcm.zarr")
    return dataclasses.replace(FIXTURE, cache_dir=d, results_path=d / "out" / "regret.parquet")


@pytest.fixture(scope="module")
def result(cfg):
    return neuralgcm.run(cfg, flights=matched_flights(cfg, "neuralgcm")[:1], leads_h=LEADS, workers=1)


def test_cli_lists_neuralgcm(capsys):
    assert "neuralgcm" in cli.COMMANDS
    cli.main(["--help"])
    assert "neuralgcm" in capsys.readouterr().out


def test_matched_flight_counts():
    assert len(neuralgcm.addon_flights(FIXTURE)) == 6
    assert len(neuralgcm.addon_flights(get_config("full"))) == 110


def test_rows_use_core_schema_and_five_sources(result, cfg):
    df, _ = result
    assert list(df.columns) == list(COLUMNS)
    assert set(df["source"]) == {"truth", *cfg.sources, "neuralgcm"}
    assert len(df) == 1 + 5 * len(LEADS)
    assert df["regret_fuel_kg"].min() >= 0
    assert df["is_hindsight"].sum() == 1


def test_forecast_plans_use_12_hourly_steps(cfg, monkeypatch):
    calls = []
    real = sources.forecast_winds

    def spy(cfg_, source, flight, lead_h, **kw):
        calls.append((source, lead_h, kw.get("step_h")))
        return real(cfg_, source, flight, lead_h, **kw)

    monkeypatch.setattr(sources, "forecast_winds", spy)
    neuralgcm.run(cfg, flights=matched_flights(cfg, "neuralgcm")[:1], leads_h=(24,), workers=1)
    twelve = {(s, l) for s, l, st in calls if st == 12}
    native = {(s, l) for s, l, st in calls if st is None}
    assert twelve == {(s, 24) for s in (*cfg.sources, "neuralgcm")}
    assert native == {(s, 24) for s in cfg.sources}  # the 6-hourly sensitivity run
    assert all(st in (12, None) for _, _, st in calls)


def test_sensitivity_shape(result, cfg):
    _, sens = result
    assert list(sens.columns) == [
        "source", "lead_h", "n", "regret_6h_kg", "regret_12h_kg", "regret_12h_core_set_kg",
    ]
    assert len(sens) == len(cfg.sources) * len(LEADS)
    assert set(sens["source"]) == set(cfg.sources)
    assert (sens[["regret_6h_kg", "regret_12h_kg", "regret_12h_core_set_kg"]] >= 0).all().all()


def test_workers_identical(cfg):
    fl = matched_flights(cfg, "neuralgcm")[:2]
    a = neuralgcm.run(cfg, flights=fl, leads_h=(24,), workers=1)
    b = neuralgcm.run(cfg, flights=fl, leads_h=(24,), workers=2)
    pd.testing.assert_frame_equal(a[0], b[0])
    pd.testing.assert_frame_equal(a[1], b[1])


def test_main_writes_both_files(cfg, monkeypatch, caplog):
    real = neuralgcm.run
    monkeypatch.setattr(neuralgcm, "get_config", lambda *a, **k: cfg)
    monkeypatch.setattr(
        neuralgcm, "run", lambda c: real(c, flights=matched_flights(c, "neuralgcm")[:1], leads_h=(24,), workers=1)
    )
    with caplog.at_level("INFO"):
        assert neuralgcm.main([]) == 0
    out = cfg.results_path.parent
    assert list(pd.read_parquet(out / "neuralgcm_regret.parquet").columns) == list(COLUMNS)
    assert len(pd.read_parquet(out / "neuralgcm_sensitivity.parquet")) == len(cfg.sources)
    assert "elapsed_s=" in caplog.text


# --- figure ---

SOURCES = ("hres", "graphcast", "pangu", "persistence", "neuralgcm")


def figure_table() -> pd.DataFrame:
    base = make_table()
    parts = [base]
    for s in ("graphcast", "pangu", "neuralgcm"):
        extra = base[base.source == "hres"].copy()
        extra["source"] = s
        parts.append(extra)
    return pd.concat(parts, ignore_index=True)


def test_fig_id_and_html():
    assert FIG_ID == "fig-neuralgcm"
    assert f'id="{FIG_ID}"' in build_neuralgcm(figure_table()).to_html(div_id=FIG_ID)


def test_five_sources_with_labels_and_title_from_data():
    fig = build_neuralgcm(figure_table())
    names = {t.name for t in fig.data if t.mode and "lines" in t.mode and t.fill != "toself"}
    assert names == {headline.SOURCE_LABELS[s] for s in SOURCES}
    assert fig.layout.title.text == "5-source comparison on 4 flights, 12-hourly planning"


def test_structure_persistence_row_ci_annotation_and_width():
    fig = build_neuralgcm(figure_table())
    assert fig.layout.height and (fig.layout.width or 0) <= headline.REPORT_WIDTH
    assert fig.layout.legend.orientation == "h"
    assert list(fig.layout.xaxis.tickvals) == [12, 24, 48, 72, 120]
    assert any("90% CI" in a.text for a in fig.layout.annotations)
    pers = [t for t in fig.data if t.legendgroup == "persistence"]
    assert pers and {t.yaxis for t in pers} <= {"y3", "y4"}


def _plot_h(fig) -> float:
    return fig.layout.height - fig.layout.margin.t - fig.layout.margin.b


def test_hover_is_x_unified_with_ci_and_bands_skipped():
    fig = build_neuralgcm(figure_table())
    assert fig.layout.hovermode == "x unified"
    bands = [t for t in fig.data if t.fill == "toself"]
    lines = [t for t in fig.data if t.fill != "toself"]
    assert bands and all(t.hoverinfo == "skip" for t in bands)
    for t in lines:
        assert t.hovertemplate.startswith(t.name) and "[%{customdata[0]" in t.hovertemplate and "kg" in t.hovertemplate
        assert len(t.customdata) == len(t.x)
        assert all(lo <= m <= hi for (lo, hi), m in zip(t.customdata, t.y))


def test_forecast_row_is_tall_and_regret_axes_start_at_zero():
    fig = build_neuralgcm(figure_table())
    top = fig.layout.yaxis.domain
    assert (top[1] - top[0]) * _plot_h(fig) >= 320
    for name in ("yaxis", "yaxis2", "yaxis3", "yaxis4"):
        assert fig.layout[name].rangemode == "tozero"
    assert fig.layout.yaxis.type in (None, "linear")


def test_ci_note_lies_inside_the_figure_below_the_legend():
    fig = build_neuralgcm(figure_table())
    note = next(a for a in fig.layout.annotations if "90% CI" in a.text)
    plot_h = _plot_h(fig)
    top_px = fig.layout.margin.t + (1 - note.y) * plot_h  # yanchor "top": the text hangs down from here
    assert note.yanchor == "top"
    text_px = 2 * note.font.size  # room for the text
    assert 0 <= top_px and top_px + text_px <= fig.layout.height
    legend_top = fig.layout.margin.t + (1 - fig.layout.legend.y) * plot_h
    assert top_px >= legend_top + 3 * 20  # below a legend that wraps to three rows on a narrow page
