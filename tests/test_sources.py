"""Forecast sources on a synthetic cache in the CONTRACTS 2.5 layout."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta

import numpy as np
import pytest
import xarray as xr

from regret import sources
from regret.config import FIXTURE, cache_path, flights
from regret.types import Dataset

LAT = np.array([30.0, 40.0, 50.0, 60.0])
LON = np.array([-90.0, -60.0, -30.0, 0.0, 15.0])
STEPS_H = np.arange(0, 133, 6)
ERA5_TIMES = np.arange(
    np.datetime64("2020-02-03T00", "ns"), np.datetime64("2020-02-11T13", "ns"),
    np.timedelta64(6, "h"),
)


def _field(seed, shape):
    return np.random.default_rng(seed).uniform(-40, 40, shape)


def _write_era5(path):
    shape = (len(ERA5_TIMES), len(LAT), len(LON))
    xr.Dataset(
        {
            "u_component_of_wind": (("time", "latitude", "longitude"), _field(1, shape)),
            "v_component_of_wind": (("time", "latitude", "longitude"), _field(2, shape)),
        },
        coords={"time": ERA5_TIMES, "latitude": LAT, "longitude": LON, "level": 250},
    ).to_zarr(path, mode="w")


def _inits(cfg):
    deps = {f.departure_time for f in flights(cfg)}
    return np.array(
        sorted({np.datetime64(d - timedelta(hours=h), "ns") for d in deps for h in cfg.leads_h}),
        dtype="datetime64[ns]",
    )


def _write_forecast(path, inits, seed):
    shape = (len(inits), len(STEPS_H), len(LAT), len(LON))
    dims = ("time", "prediction_timedelta", "latitude", "longitude")
    xr.Dataset(
        {
            "u_component_of_wind": (dims, _field(seed, shape)),
            "v_component_of_wind": (dims, _field(seed + 1, shape)),
        },
        coords={
            "time": inits,
            "prediction_timedelta": STEPS_H.astype("timedelta64[h]").astype("timedelta64[ns]"),
            "latitude": LAT,
            "longitude": LON,
            "level": 250,
        },
    ).to_zarr(path, mode="w")


@pytest.fixture
def cfg(tmp_path):
    base = dataclasses.replace(FIXTURE, cache_dir=tmp_path)
    extra = Dataset("fakecast", "", ("u_component_of_wind", "v_component_of_wind"), False, "forecast", ())
    cfg = dataclasses.replace(
        base, datasets=base.datasets + (extra,), sources=base.sources + ("fakecast",)
    )
    sources._open.cache_clear()
    sources._member_ds.cache_clear()
    _write_era5(cache_path(cfg, "era5"))
    for i, name in enumerate(["hres", "graphcast", "pangu", "fakecast"]):
        _write_forecast(cache_path(cfg, name), _inits(cfg), 10 * (i + 1))
    return cfg


def _era5(cfg):
    return xr.open_zarr(cache_path(cfg, "era5")).load()


def test_truth_winds_equal_era5_at_grid_points(cfg):
    ds = _era5(cfg)
    w = sources.truth_winds(cfg)
    lat, lon, t = LAT[1], LON[2], ds["time"].values[5]
    u, v = w.uv(lat, lon, t)
    assert u == ds["u_component_of_wind"].sel(time=t, latitude=lat, longitude=lon).item()
    assert v == ds["v_component_of_wind"].sel(time=t, latitude=lat, longitude=lon).item()


FORECASTS = ["hres", "graphcast", "pangu", "fakecast"]


@pytest.mark.parametrize("source", FORECASTS)
@pytest.mark.parametrize("lead_h", [12, 48, 120])
def test_forecast_equals_stored_value_for_right_init_and_step(cfg, source, lead_h):
    flight = flights(cfg)[3]
    init = np.datetime64(flight.departure_time - timedelta(hours=lead_h), "ns")
    stored = xr.open_zarr(cache_path(cfg, source)).load().sel(time=init)
    w = sources.forecast_winds(cfg, source, flight, lead_h)
    for step_h in (lead_h, lead_h + 6, lead_h + 12):
        valid = init + np.timedelta64(step_h, "h")
        sel = stored.sel(prediction_timedelta=np.timedelta64(step_h, "h"), latitude=LAT[2], longitude=LON[1])
        u, v = w.uv(LAT[2], LON[1], valid)
        assert u == sel["u_component_of_wind"].item()
        assert v == sel["v_component_of_wind"].item()


@pytest.mark.parametrize("lead_h", [12, 24, 48, 72, 120])
def test_persistence_is_era5_at_init_constant_in_time(cfg, lead_h):
    flight = flights(cfg)[0]  # first flight: 120 h lead reaches the ERA5 window start
    init = np.datetime64(flight.departure_time - timedelta(hours=lead_h), "ns")
    ds = _era5(cfg).sel(time=init)
    w = sources.forecast_winds(cfg, "persistence", flight, lead_h)
    for step_h in (lead_h, lead_h + 6, lead_h + 12):
        valid = init + np.timedelta64(step_h, "h")
        u, v = w.uv(LAT[1], LON[3], valid)
        assert u == ds["u_component_of_wind"].sel(latitude=LAT[1], longitude=LON[3]).item()
        assert v == ds["v_component_of_wind"].sel(latitude=LAT[1], longitude=LON[3]).item()


def test_missing_init_names_source_init_and_path(cfg):
    flight = flights(cfg)[0]
    with pytest.raises(sources.MissingForecastError) as e:
        sources.forecast_winds(cfg, "hres", flight, 7)  # 7 h lead: init not cached
    msg = str(e.value)
    assert "hres" in msg and "2020-02-07T17" in msg and str(cache_path(cfg, "hres")) in msg


def test_missing_cache_names_source_and_path(cfg):
    flight = flights(cfg)[0]
    gone = dataclasses.replace(cfg, cache_dir=cfg.cache_dir / "nowhere")
    with pytest.raises(sources.MissingForecastError) as e:
        sources.forecast_winds(gone, "pangu", flight, 12)
    assert "pangu" in str(e.value) and str(cache_path(gone, "pangu")) in str(e.value)


def test_each_zarr_opened_once(cfg, monkeypatch):
    calls = []
    real = xr.open_zarr
    monkeypatch.setattr(xr, "open_zarr", lambda *a, **k: calls.append(a[0]) or real(*a, **k))
    for f in flights(cfg)[:4]:
        sources.forecast_winds(cfg, "hres", f, 12)
    assert len(calls) == 1


# --- N1b: step_h and member -------------------------------------------------

def _uv(w, t):
    return w.uv(LAT[2], LON[1], t)


@pytest.mark.parametrize("source", ["hres", "persistence"])
def test_default_equals_explicit_none_and_native_steps(cfg, source):
    flight = flights(cfg)[3]
    a = sources.forecast_winds(cfg, source, flight, 24)
    b = sources.forecast_winds(cfg, source, flight, 24, step_h=None)
    init = np.datetime64(flight.departure_time - timedelta(hours=24), "ns")
    for h in (24, 30, 36):
        t = init + np.timedelta64(h, "h")
        assert _uv(a, t) == _uv(b, t)


def test_default_matches_real_fixture_value():
    import dataclasses as dc
    from regret.config import get_config
    cfg = get_config("fixture")
    if not cache_path(cfg, "hres").exists():
        pytest.skip("no fixture cache")
    flight = flights(cfg)[0]
    sources._open.cache_clear()
    sources._member_ds.cache_clear()
    w = sources.forecast_winds(cfg, "hres", flight, 24)
    init = np.datetime64(flight.departure_time - timedelta(hours=24), "ns")
    ds = xr.open_zarr(cache_path(cfg, "hres")).sel(time=init)
    lat, lon = float(ds.latitude[5]), float(ds.longitude[7])
    t = init + np.timedelta64(30, "h")
    exp = ds["u_component_of_wind"].sel(prediction_timedelta=np.timedelta64(30, "h")).isel(latitude=5, longitude=7).item()
    assert w.uv(lat, lon, t)[0] == pytest.approx(exp)


def test_step_12_uses_only_two_steps_linear(cfg):
    flight = flights(cfg)[3]
    lead = 24
    init = np.datetime64(flight.departure_time - timedelta(hours=lead), "ns")
    w = sources.forecast_winds(cfg, "hres", flight, lead, step_h=12)
    t0, t1, mid = (init + np.timedelta64(h, "h") for h in (lead, lead + 12, lead + 6))
    u0, v0 = _uv(w, t0)
    u1, v1 = _uv(w, t1)
    um, vm = _uv(w, mid)
    assert um == pytest.approx((u0 + u1) / 2) and vm == pytest.approx((v0 + v1) / 2)
    native = sources.forecast_winds(cfg, "hres", flight, lead)
    assert _uv(native, mid)[0] != pytest.approx(um)  # the 6 h step was not used


def test_step_12_persistence_frozen_at_init(cfg):
    flight = flights(cfg)[0]
    lead = 24
    init = np.datetime64(flight.departure_time - timedelta(hours=lead), "ns")
    w = sources.forecast_winds(cfg, "persistence", flight, lead, step_h=12)
    ds = _era5(cfg).sel(time=init, latitude=LAT[1], longitude=LON[3])
    for h in (lead, lead + 6, lead + 12):
        assert _uv(w, init + np.timedelta64(h, "h"))[0] == pytest.approx(
            w.uv(LAT[2], LON[1], init)[0])
    assert w.uv(LAT[1], LON[3], init)[0] == ds["u_component_of_wind"].item()


def _write_ens(path, inits, members=3):
    steps = np.arange(12, 49, 12)
    shape = (len(inits), len(steps), members, len(LAT), len(LON))
    dims = ("time", "prediction_timedelta", "member", "latitude", "longitude")
    xr.Dataset(
        {
            "u_component_of_wind": (dims, _field(7, shape)),
            "v_component_of_wind": (dims, _field(8, shape)),
        },
        coords={
            "time": inits,
            "prediction_timedelta": steps.astype("timedelta64[h]").astype("timedelta64[ns]"),
            "member": np.arange(members),
            "latitude": LAT, "longitude": LON, "level": 250,
        },
    ).to_zarr(path, mode="w")


@pytest.fixture
def ens_cfg(cfg):
    extra = Dataset("neuralgcm_ens", "", ("u_component_of_wind", "v_component_of_wind"), False, "ensemble", ())
    c = dataclasses.replace(cfg, datasets=cfg.datasets + (extra,))
    _write_ens(cache_path(c, "neuralgcm_ens"), _inits(c))
    _write_ens_twin = None
    return c


def test_member_selection(ens_cfg):
    cfg = ens_cfg
    flight = flights(cfg)[3]
    lead = 24
    init = np.datetime64(flight.departure_time - timedelta(hours=lead), "ns")
    stored = xr.open_zarr(cache_path(cfg, "neuralgcm_ens")).load().sel(time=init)
    for k in (0, 2):
        w = sources.forecast_winds(cfg, "neuralgcm_ens", flight, lead, step_h=12, member=k)
        for h in (lead, lead + 12):
            exp = stored["u_component_of_wind"].sel(
                member=k, prediction_timedelta=np.timedelta64(h, "h"), latitude=LAT[2], longitude=LON[1]).item()
            assert _uv(w, init + np.timedelta64(h, "h"))[0] == pytest.approx(exp)


def test_ensemble_without_member_is_error(ens_cfg):
    with pytest.raises(ValueError, match="member"):
        sources.forecast_winds(ens_cfg, "neuralgcm_ens", flights(ens_cfg)[3], 24, step_h=12)


def test_member_on_non_ensemble_is_error(cfg):
    with pytest.raises(ValueError, match="member"):
        sources.forecast_winds(cfg, "hres", flights(cfg)[3], 24, member=0)


def test_neuralgcm_loads_though_not_in_cfg_sources(cfg):
    extra = Dataset("neuralgcm", "", ("u_component_of_wind", "v_component_of_wind"), False, "forecast", ())
    c = dataclasses.replace(cfg, datasets=cfg.datasets + (extra,))
    assert "neuralgcm" not in c.sources
    steps = np.arange(0, 49, 12)
    inits = _inits(c)
    shape = (len(inits), len(steps), len(LAT), len(LON))
    dims = ("time", "prediction_timedelta", "latitude", "longitude")
    xr.Dataset(
        {"u_component_of_wind": (dims, _field(3, shape)), "v_component_of_wind": (dims, _field(4, shape))},
        coords={"time": inits, "prediction_timedelta": steps.astype("timedelta64[h]").astype("timedelta64[ns]"),
                "latitude": LAT, "longitude": LON, "level": 250},
    ).to_zarr(cache_path(c, "neuralgcm"), mode="w")
    w = sources.forecast_winds(c, "neuralgcm", flights(c)[3], 24, step_h=12)
    assert np.isfinite(_uv(w, np.datetime64(flights(c)[3].departure_time, "ns"))[0])


def test_ensemble_not_loaded_whole(ens_cfg, monkeypatch):
    loaded = []
    real = xr.Dataset.load
    monkeypatch.setattr(xr.Dataset, "load", lambda self, *a, **k: loaded.append(dict(self.sizes)) or real(self, *a, **k))
    sources._open.cache_clear()
    sources._member_ds.cache_clear()
    sources.forecast_winds(ens_cfg, "neuralgcm_ens", flights(ens_cfg)[3], 24, step_h=12, member=1)
    assert loaded and all(d.get("member", 1) == 1 for d in loaded)
