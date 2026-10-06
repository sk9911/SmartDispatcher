from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from regret import geostrophic as g
from regret.config import FULL, get_config
from regret.figures import style
from regret.figures.geostrophic import FIG_ID, build_geostrophic
from regret.figures.headline import SOURCE_LABELS

R, OMEGA = g.EARTH_RADIUS_M, g.OMEGA
LAT = np.arange(25.5, 75.01, 1.5)
LON = np.arange(-99.0, 20.0, 1.5)


def analytic_phi_and_wind():
    """Phi = a sin(2 lam) cos^2(phi) + b sin(2 phi) and its exact geostrophic wind."""
    a, b, k = 3000.0, 8000.0, 2.0
    la, lo = np.deg2rad(LAT)[:, None], np.deg2rad(LON)[None, :]
    phi = a * np.sin(k * lo) * np.cos(la) ** 2 + b * np.sin(2 * la) + 0 * lo
    dphi_dy = (a * np.sin(k * lo) * (-2 * np.cos(la) * np.sin(la)) + 2 * b * np.cos(2 * la)) / R
    dphi_dx = a * k * np.cos(k * lo) * np.cos(la) ** 2 / (R * np.cos(la))
    f = 2 * OMEGA * np.sin(la)
    return phi, -dphi_dy / f, dphi_dx / f


def test_balanced_field_has_tiny_ageostrophic_fraction():
    phi, u, v = analytic_phi_and_wind()
    assert np.hypot(u, v).max() > 20  # a real jet, not a trivial zero field
    assert g.ageostrophic_fraction(u, v, phi, LAT, LON) < 0.01


def test_added_divergent_wind_breaks_balance():
    phi, u, v = analytic_phi_and_wind()
    assert g.ageostrophic_fraction(u + 10.0, v, phi, LAT, LON) > 0.1


def test_f_varies_with_latitude_per_grid_point():
    phi, _, _ = analytic_phi_and_wind()
    ug, vg = g.geostrophic_wind(phi, LAT, LON)
    # uniform phi gradient in y: u_g = -(1/f) dphi/dy must scale as 1/sin(lat)
    p = np.tile(-100.0 * np.deg2rad(LAT)[:, None] * R, (1, len(LON)))  # dphi/dy = -100
    ug, _ = g.geostrophic_wind(p, LAT, LON)
    expected = 100.0 / (2 * OMEGA * np.sin(np.deg2rad(LAT)))
    assert np.allclose(ug[1:-1, 5], expected[1:-1], rtol=1e-6)
    assert ug[1, 5] > ug[-2, 5] * 1.5  # f is larger poleward, so u_g is smaller there


def test_region_is_30_to_70_north_interior_only():
    phi, u, v = analytic_phi_and_wind()
    # corrupt winds outside 30-70N: the fraction must not change
    bad = u.copy()
    bad[(LAT < 30) | (LAT > 70), :] += 50.0
    assert g.ageostrophic_fraction(bad, v, phi, LAT, LON) == pytest.approx(
        g.ageostrophic_fraction(u, v, phi, LAT, LON)
    )
    mask = g.region_mask(LAT)
    assert LAT[mask].min() >= 30 and LAT[mask].max() <= 70
    assert LAT[mask].min() < 31.5 and LAT[mask].max() > 68.5


# ---- parquet from a tiny synthetic cache ----

DEP = datetime(2020, 2, 9, 0)


def _write_cache(tmp_path: Path):
    phi, u, v = analytic_phi_and_wind()
    lat, lon = LAT, LON
    leads = [12, 24]
    steps = np.array([0, 6, 12, 18, 24, 30, 36], dtype="timedelta64[h]").astype("timedelta64[ns]")
    inits = [np.datetime64(DEP - pd.Timedelta(hours=h), "ns") for h in leads]
    cfg = _tiny_cfg(tmp_path)
    coords = dict(latitude=lat, longitude=lon)
    for name in ("hres", "graphcast", "pangu"):
        shape = (len(inits), len(steps), len(lat), len(lon))
        P = np.broadcast_to(phi, shape).copy()
        U = np.broadcast_to(u, shape).copy() + (10.0 if name == "pangu" else 0.0)
        V = np.broadcast_to(v, shape).copy()
        c = dict(time=inits, prediction_timedelta=steps, **coords)
        dims = ("time", "prediction_timedelta", "latitude", "longitude")
        xr.Dataset({"geopotential": (dims, P.astype("float32"))}, c).to_zarr(
            tmp_path / f"geopotential_{name}.zarr"
        )
        xr.Dataset(
            {"u_component_of_wind": (dims, U.astype("float32")), "v_component_of_wind": (dims, V.astype("float32"))}, c
        ).to_zarr(tmp_path / f"{name}.zarr")
    t = np.array([np.datetime64(DEP, "ns")])
    dims = ("time", "latitude", "longitude")
    c = dict(time=t, **coords)
    xr.Dataset({"geopotential": (dims, phi[None].astype("float32"))}, c).to_zarr(tmp_path / "geopotential_era5.zarr")
    xr.Dataset(
        {"u_component_of_wind": (dims, u[None].astype("float32")), "v_component_of_wind": (dims, v[None].astype("float32"))},
        c,
    ).to_zarr(tmp_path / "era5.zarr")
    return cfg


def _tiny_cfg(tmp_path: Path):
    import dataclasses

    return dataclasses.replace(
        FULL,
        first_departure_date=DEP.date(),
        last_departure_date=DEP.date(),
        leads_h=(12, 24),
        legs=FULL.legs[:1],
        cache_dir=tmp_path,
        results_path=tmp_path / "out" / "regret.parquet",
    )


def test_compute_table_schema_and_values(tmp_path):
    cfg = _write_cache(tmp_path)
    df = g.run(cfg)
    assert list(df.columns) == ["source", "lead_h", "ageostrophic_fraction", "n_fields"]
    assert set(df["source"]) == {"era5", "hres", "graphcast", "pangu"}
    era5 = df[df["source"] == "era5"]
    assert len(era5) == 2 and set(era5["lead_h"]) == {12, 24}
    assert (era5["ageostrophic_fraction"] < 0.01).all()
    pangu = df[df["source"] == "pangu"]
    assert (pangu["ageostrophic_fraction"] > 0.1).all()
    assert (df["n_fields"] == 1).all()  # one flight on DEP's date


def test_main_writes_parquet(tmp_path, monkeypatch):
    cfg = _write_cache(tmp_path)
    monkeypatch.setattr(g, "get_config", lambda: cfg)
    assert g.main([]) == 0
    out = pd.read_parquet(tmp_path / "out" / "geostrophic.parquet")
    assert {"source", "lead_h", "ageostrophic_fraction", "n_fields"} <= set(out.columns)


@pytest.mark.skipif(not Path("data/results/geostrophic.parquet").exists(), reason="no real results")
def test_real_results_plausible():
    df = pd.read_parquet("data/results/geostrophic.parquet")
    assert df["ageostrophic_fraction"].between(0, 1).all()


# ---- figure ----


@pytest.fixture(scope="module")
def df():
    rows = []
    for lead in (12, 24, 48, 72, 120):
        rows.append(dict(source="era5", lead_h=lead, ageostrophic_fraction=0.20, n_fields=100))
        for i, s in enumerate(("hres", "graphcast", "pangu")):
            rows.append(dict(source=s, lead_h=lead, ageostrophic_fraction=0.20 + 0.01 * i + lead / 2000, n_fields=100))
    return pd.DataFrame(rows)


def test_figure_traces_labels_and_axes(df):
    fig = build_geostrophic(df)
    lines = [t for t in fig.data if t.mode and "lines" in t.mode and t.name != SOURCE_LABELS.get("era5", "ERA5 (reference)")]
    names = [t.name for t in fig.data]
    for s in ("hres", "graphcast", "pangu"):
        t = next(t for t in fig.data if t.name == SOURCE_LABELS[s])
        assert t.line.color == style.colour(s)
        assert t.marker.symbol == style.symbol(s)
        assert list(t.x) == [12, 24, 48, 72, 120]
    assert len(fig.data) == 4 and len(names) == len(set(names))
    assert any("ERA5" in n for n in names)
    assert fig.layout.xaxis.title.text == "lead time (h)"
    assert fig.layout.yaxis.title.text == "ageostrophic fraction (axis does not start at 0)"
    assert list(fig.layout.xaxis.tickvals) == [12, 24, 48, 72, 120]
    assert fig.layout.height >= 450
    assert fig.layout.title.text
    assert lines


def test_figure_html_has_stable_id(df):
    assert FIG_ID == "fig-geostrophic"
    assert 'id="fig-geostrophic"' in build_geostrophic(df).to_html(div_id=FIG_ID, include_plotlyjs=False)


# ---- B14: caption from the data, readable axis, unified hover ----


def _frame(era5, **per_source):
    rows = []
    for lead in (12, 24):
        rows.append(dict(source="era5", lead_h=lead, ageostrophic_fraction=era5, n_fields=10))
        for s, vals in per_source.items():
            rows.append(dict(source=s, lead_h=lead, ageostrophic_fraction=vals[lead], n_fields=10))
    return pd.DataFrame(rows)


def test_summary_all_forecasts_lower():
    from regret.figures.geostrophic import geostrophic_summary

    d = _frame(0.21, hres={12: 0.20, 24: 0.205}, pangu={12: 0.19, 24: 0.186})
    text = geostrophic_summary(d)
    assert "about 0.21" in text
    assert "0.024" in text  # largest gap: 0.21 - 0.186
    assert "all forecast sources are slightly more balanced (lower) than ERA5" in text
    assert "possible explanation, not a finding" in text


def test_summary_names_the_source_and_lead_above_era5():
    from regret.figures.geostrophic import geostrophic_summary

    d = _frame(0.2129, hres={12: 0.2100, 24: 0.2137}, graphcast={12: 0.2031, 24: 0.2035})
    text = geostrophic_summary(d)
    assert "about 0.21" in text
    assert "IFS HRES at 24 h sits just above ERA5" in text
    assert "all forecast sources" not in text
    assert "not a finding" not in text
    assert "0.010" in text  # largest gap: 0.2129 - 0.2031 = 0.0098


def test_axis_is_linear_zoomed_labelled_and_covers_the_data(df):
    fig = build_geostrophic(df)
    y = fig.layout.yaxis
    assert y.type in (None, "linear")
    assert y.rangemode is None
    lo, hi = y.range
    vals = df["ageostrophic_fraction"]
    assert lo < vals.min() and hi > vals.max() and lo > 0.1  # zoomed, not from 0
    pad = (hi - lo - (vals.max() - vals.min())) / 2 / (vals.max() - vals.min())
    assert 0.1 <= pad <= 0.25
    assert "does not start at 0" in y.title.text
    assert list(build_geostrophic(df).layout.yaxis.range) == [lo, hi]


def test_hover_is_x_unified_and_every_source_is_named(df):
    fig = build_geostrophic(df)
    assert fig.layout.hovermode == "x unified"
    assert all("%{fullData.name}" in (t.hovertemplate or "") or t.name for t in fig.data)
    assert all(t.hoverinfo != "skip" for t in fig.data)
