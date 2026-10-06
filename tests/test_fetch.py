"""Tests for regret.fetch against tiny zarrs built in tmp_path (no network)."""
from __future__ import annotations

import dataclasses
import logging

import numpy as np
import pytest
import xarray as xr

from regret import fetch as fetch_mod
from regret.config import FIXTURE, cache_path, flights, store_url
from regret.fetch import MissingDataError, fetch, main

LAT = np.arange(90.0, -91.0, -10.0)  # descending, as some stores are
LON = np.arange(0.0, 360.0, 10.0)  # 0..360
LEVELS = np.array([200, 250, 300])
GRAPHCAST_LEVELS = np.array([1, 10, 50, 100, 200, 250, 300, 500, 850, 1000])  # live: 37 levels
WIND = ("u_component_of_wind", "v_component_of_wind")


def _field(shape, seed):
    return np.random.default_rng(seed).normal(size=shape).astype("float32")


def make_truth(path, *, levels=LEVELS, variables=WIND + ("geopotential",)):
    """Like the live ERA5 store: lon before lat."""
    time = np.arange("2019-12-20", "2020-03-05", np.timedelta64(6, "h"), dtype="datetime64[ns]")
    dims = ("time", "level", "longitude", "latitude")
    shape = (len(time), len(levels), len(LON), len(LAT))
    ds = xr.Dataset(
        {v: (dims, _field(shape, i)) for i, v in enumerate(variables)},
        coords=dict(time=time, level=levels, latitude=LAT, longitude=LON),
    )
    ds.to_zarr(path, mode="w")
    return path


def make_forecast(path, *, levels=LEVELS, drop_inits=(), max_step_h=144, min_step_h=0, members=None,
                  variables=WIND + ("geopotential",), int_hours=True, units="hours", lonlat=True):
    """Like the live forecast stores: int64 hour steps with a ``units`` attribute, lon before lat."""
    init = np.arange("2020-01-25", "2020-02-13", np.timedelta64(12, "h"), dtype="datetime64[ns]")
    init = np.array([t for t in init if t not in set(np.array(drop_inits, dtype="datetime64[ns]"))])
    hours = np.arange(min_step_h, max_step_h + 1, 6)
    step = hours.astype("int64") if int_hours else hours.astype("timedelta64[h]").astype("timedelta64[ns]")
    horiz = ["longitude", "latitude"] if lonlat else ["latitude", "longitude"]
    size = dict(latitude=len(LAT), longitude=len(LON))
    dims = ["time", "prediction_timedelta", "level", *horiz]
    shape = [len(init), len(step), len(levels), *(size[d] for d in horiz)]
    coords = dict(time=init, prediction_timedelta=step, level=levels, latitude=LAT, longitude=LON)
    if members:
        dims.insert(1, "member")
        shape.insert(1, members)
        coords["member"] = np.arange(members)
    ds = xr.Dataset({v: (dims, _field(shape, i)) for i, v in enumerate(variables)}, coords=coords)
    if int_hours:
        ds["prediction_timedelta"].attrs.update(units=units, standard_name="forecast_period")
    ds.to_zarr(path, mode="w")
    return path


def make_neuralgcm(path, *, realizations=None, drop_inits=()):
    """Like the live NeuralGCM stores: 12-hourly int-hour steps, inits every 12 h from 2020-01-01,
    ``realization`` (ensemble only), chunk order realization, time, step, level, lon, lat."""
    init = np.arange("2020-01-01", "2020-02-13", np.timedelta64(12, "h"), dtype="datetime64[ns]")
    init = np.array([t for t in init if t not in set(np.array(drop_inits, dtype="datetime64[ns]"))])
    step = np.arange(0, 241, 12).astype("int64")
    dims = ["time", "prediction_timedelta", "level", "longitude", "latitude"]
    shape = [len(init), len(step), len(LEVELS), len(LON), len(LAT)]
    coords = dict(time=init, prediction_timedelta=step, level=LEVELS, latitude=LAT, longitude=LON)
    if realizations:
        dims.insert(0, "realization")
        shape.insert(0, realizations)
        coords["realization"] = np.arange(realizations)
    ds = xr.Dataset({v: (dims, _field(shape, i)) for i, v in enumerate(WIND)}, coords=coords)
    ds["prediction_timedelta"].attrs.update(units="hours", standard_name="forecast_period")
    ds.to_zarr(path, mode="w")
    return path


@pytest.fixture
def world(tmp_path):
    """FIXTURE config whose dataset stores are tiny local zarrs; also an opener that counts reads."""
    src = tmp_path / "src"
    src.mkdir()
    datasets = []
    for d in FIXTURE.datasets:
        datasets.append(dataclasses.replace(d, store=str(src / f"{d.name}.zarr")) if d.store else d)
    cfg = dataclasses.replace(FIXTURE, datasets=tuple(datasets), cache_dir=tmp_path / "cache")
    make_truth(src / "era5.zarr")
    make_forecast(src / "hres.zarr")
    make_forecast(src / "graphcast.zarr", min_step_h=6, levels=GRAPHCAST_LEVELS)
    make_forecast(src / "pangu.zarr", min_step_h=6)
    make_neuralgcm(src / "neuralgcm.zarr")
    make_neuralgcm(src / "neuralgcm_ens.zarr", realizations=3)
    reads = []

    def open_store(url):
        reads.append(url)
        return xr.open_zarr(url, consolidated=False, decode_timedelta=False)

    return cfg, open_store, reads, src


def test_era5_output_only_covers_box_level_and_window(world):
    cfg, open_store, reads, _ = world
    report = fetch(cfg, ["era5"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "era5"))
    assert set(out.data_vars) == set(WIND)
    assert out.time.values[0] == np.datetime64(cfg.era5_start, "ns")
    assert out.time.values[-1] == np.datetime64(cfg.era5_end, "ns")
    assert np.all(np.diff(out.time.values) == np.timedelta64(6, "h"))
    assert out.latitude.min() >= cfg.box.lat_min_deg and out.latitude.max() <= cfg.box.lat_max_deg
    assert out.longitude.min() >= cfg.box.lon_min_deg and out.longitude.max() <= cfg.box.lon_max_deg
    assert np.all(np.diff(out.latitude.values) > 0) and np.all(np.diff(out.longitude.values) > 0)
    assert "level" not in out.dims and float(out.level) == 250
    assert report.datasets == ("era5",)
    assert report.downloads == 1
    assert reads == [store_url(next(d for d in cfg.datasets if d.name == "era5"))]


def test_forecast_output_has_only_needed_inits_steps_box_and_level(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["hres"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "hres"))
    need_inits = {
        np.datetime64(f.departure_time, "ns") - np.timedelta64(lead, "h")
        for f in flights(cfg)
        for lead in cfg.leads_h
    }
    assert set(out.time.values) == need_inits
    need_steps = {h for lead in cfg.leads_h for h in (lead, lead + 6, lead + 12)}
    assert set(out.prediction_timedelta.values // np.timedelta64(1, "h")) == need_steps
    assert out[WIND[0]].dims == ("time", "prediction_timedelta", "latitude", "longitude")
    assert float(out.level) == 250 and "level" not in out.dims
    assert set(out.data_vars) == set(WIND)
    assert out.latitude.min() >= 25 and out.latitude.max() <= 75
    assert out.longitude.min() >= -100 and out.longitude.max() <= 20
    assert np.all(np.diff(out.longitude.values) > 0) and np.all(np.diff(out.latitude.values) > 0)


def test_values_survive_the_subset(world):
    cfg, open_store, _, src = world
    fetch(cfg, ["era5"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "era5"))
    raw = xr.open_zarr(src / "era5.zarr", consolidated=False)
    # raw lon 350 is -10 after normalisation; lat 50
    want = raw[WIND[0]].sel(level=250, latitude=50.0, longitude=350.0, time=out.time[3])
    got = out[WIND[0]].sel(latitude=50.0, longitude=-10.0).isel(time=3)
    assert float(got) == float(want)


def test_store_without_250_hpa_raises_naming_store_and_level(world):
    cfg, open_store, _, src = world
    make_forecast(src / "hres.zarr", levels=np.array([200, 300, 500]))
    url = store_url(next(d for d in cfg.datasets if d.name == "hres"))
    with pytest.raises(MissingDataError) as e:
        fetch(cfg, ["hres"], open_store=open_store)
    assert url in str(e.value) and "250" in str(e.value)
    assert not cache_path(cfg, "hres").exists()


def test_missing_init_raises_naming_store_and_init(world):
    cfg, open_store, _, src = world
    make_forecast(src / "pangu.zarr", drop_inits=["2020-02-08T12:00"])
    url = store_url(next(d for d in cfg.datasets if d.name == "pangu"))
    with pytest.raises(MissingDataError) as e:
        fetch(cfg, ["pangu"], open_store=open_store)
    assert url in str(e.value) and "2020-02-08T12" in str(e.value)


def test_missing_prediction_steps_raise(world):
    cfg, open_store, _, src = world
    make_forecast(src / "graphcast.zarr", max_step_h=120)  # lead 120 needs step 132
    url = store_url(next(d for d in cfg.datasets if d.name == "graphcast"))
    with pytest.raises(MissingDataError) as e:
        fetch(cfg, ["graphcast"], open_store=open_store)
    assert url in str(e.value) and "prediction step" in str(e.value)


def test_missing_era5_times_raise(world):
    cfg, open_store, _, src = world
    cfg = dataclasses.replace(cfg, era5_start=cfg.era5_start.replace(year=2018))
    with pytest.raises(MissingDataError):
        fetch(cfg, ["era5"], open_store=open_store)


def test_second_run_makes_zero_store_reads(world, caplog):
    cfg, open_store, reads, _ = world
    with caplog.at_level(logging.INFO, logger="regret.fetch"):
        first = fetch(cfg, open_store=open_store)
        assert first.downloads == 4 and len(reads) == 4
        assert first.datasets == ("era5", "hres", "graphcast", "pangu")
        reads.clear()
        caplog.clear()
        second = fetch(cfg, open_store=open_store)
    assert reads == []
    assert second.downloads == 0
    assert "0 downloads" in caplog.text and "elapsed_s=" in caplog.text


def test_incomplete_cache_is_refetched(world):
    cfg, open_store, reads, _ = world
    fetch(cfg, ["hres"], open_store=open_store)
    import shutil
    shutil.rmtree(cache_path(cfg, "hres") / "time")  # corrupt
    reads.clear()
    assert fetch(cfg, ["hres"], open_store=open_store).downloads == 1
    assert len(reads) == 1


def test_with_extras_fetches_exactly_those_and_keeps_member_and_geopotential(world, monkeypatch):
    cfg, open_store, reads, _ = world
    monkeypatch.setattr(fetch_mod, "get_config", lambda mode=None: cfg)
    monkeypatch.setattr(fetch_mod, "_open_anonymous", open_store)
    assert main(["--with", "neuralgcm_ens,geopotential"]) == 0
    cached = sorted(p.name for p in cfg.cache_dir.iterdir())
    assert cached == sorted(
        f"{n}.zarr" for n in
        ("era5", "hres", "graphcast", "pangu", "neuralgcm_ens",
         "geopotential_era5", "geopotential_hres", "geopotential_graphcast", "geopotential_pangu")
    )
    ens = xr.open_zarr(cache_path(cfg, "neuralgcm_ens"))
    assert ens.sizes["member"] == 3
    assert ens[WIND[0]].dims == ("time", "member", "prediction_timedelta", "latitude", "longitude") or \
        set(ens[WIND[0]].dims) == {"time", "member", "prediction_timedelta", "latitude", "longitude"}
    for src, dim in (("era5", None), ("hres", "prediction_timedelta")):
        g = xr.open_zarr(cache_path(cfg, f"geopotential_{src}"))
        assert set(g.data_vars) == {"geopotential"}
        assert (dim in g.dims) == (dim is not None)


def test_with_extras_only_adds_the_named_ones(world):
    cfg, open_store, _, _ = world
    report = fetch(cfg, ["neuralgcm"], open_store=open_store)
    assert report.datasets == ("neuralgcm",)
    assert sorted(p.name for p in cfg.cache_dir.iterdir()) == ["neuralgcm.zarr"]


def test_main_rejects_unknown_dataset(world, monkeypatch):
    cfg, open_store, _, _ = world
    monkeypatch.setattr(fetch_mod, "get_config", lambda mode=None: cfg)
    with pytest.raises(SystemExit):
        main(["--with", "nonsense"])


def test_main_fixture_flag_uses_fixture_config(monkeypatch):
    seen = {}
    monkeypatch.setattr(fetch_mod, "get_config", lambda mode=None: seen.setdefault("mode", mode) and FIXTURE)
    monkeypatch.setattr(fetch_mod, "fetch", lambda cfg, names=None, **kw: seen.update(names=names, cfg=cfg)
                        or fetch_mod.FetchReport(0, 0.0, ()))
    assert main(["--fixture", "--with", "neuralgcm"]) == 0
    assert seen["mode"] == "fixture" and seen["cfg"] is FIXTURE
    assert seen["names"] == ["era5", "hres", "graphcast", "pangu", "neuralgcm"]


def test_int_hour_steps_are_stored_as_timedelta_ns(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["hres"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "hres"))
    assert out.prediction_timedelta.dtype == np.dtype("timedelta64[ns]")


def test_step_units_come_from_the_attribute(world):
    cfg, open_store, _, src = world
    # 21600 s == 6 h: the same steps expressed in seconds must work
    make_forecast(src / "hres.zarr", units="seconds")
    ds = xr.open_zarr(src / "hres.zarr", consolidated=False, decode_timedelta=False).load()
    ds = ds.assign_coords(prediction_timedelta=ds.prediction_timedelta * 3600)
    ds.prediction_timedelta.attrs["units"] = "seconds"
    import shutil
    shutil.rmtree(src / "hres.zarr")
    ds.drop_encoding().to_zarr(src / "hres.zarr", mode="w")
    fetch(cfg, ["hres"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "hres"))
    assert set(out.prediction_timedelta.values // np.timedelta64(1, "h")) == {
        h for lead in cfg.leads_h for h in (lead, lead + 6, lead + 12)}


def test_unknown_step_units_raise(world):
    cfg, open_store, _, src = world
    make_forecast(src / "hres.zarr", units="fortnights")
    with pytest.raises(MissingDataError) as e:
        fetch(cfg, ["hres"], open_store=open_store)
    assert "fortnights" in str(e.value)
    assert not cache_path(cfg, "hres").exists()


def test_int_steps_without_units_raise(world):
    cfg, open_store, _, src = world
    make_forecast(src / "hres.zarr")
    ds = xr.open_zarr(src / "hres.zarr", consolidated=False, decode_timedelta=False).load()
    ds.prediction_timedelta.attrs.pop("units")
    import shutil
    shutil.rmtree(src / "hres.zarr")
    ds.drop_encoding().to_zarr(src / "hres.zarr", mode="w")
    with pytest.raises(MissingDataError):
        fetch(cfg, ["hres"], open_store=open_store)


def test_decode_steps_passes_real_timedeltas_through():
    steps = np.arange(0, 25, 6).astype("timedelta64[h]").astype("timedelta64[ns]")
    ds = xr.Dataset(coords=dict(prediction_timedelta=steps))
    out = fetch_mod._decode_steps("mem", ds)
    assert out.prediction_timedelta.dtype == np.dtype("timedelta64[ns]")
    assert (out.prediction_timedelta.values == steps).all()


def test_timedelta_typed_store_still_works(world):
    cfg, open_store, _, src = world
    make_forecast(src / "hres.zarr", int_hours=False)
    fetch(cfg, ["hres"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "hres"))
    assert set(out.prediction_timedelta.values // np.timedelta64(1, "h")) == {
        h for lead in cfg.leads_h for h in (lead, lead + 6, lead + 12)}


def test_every_written_cache_has_contract_dim_order(world):
    cfg, open_store, _, src = world
    fetch(cfg, ["era5", "hres", "graphcast", "pangu", "neuralgcm", "neuralgcm_ens"], open_store=open_store)
    horizontal = ("latitude", "longitude")
    for name in ("era5", "hres", "graphcast", "pangu", "neuralgcm", "neuralgcm_ens"):
        out = xr.open_zarr(cache_path(cfg, name))
        lead = ("time",) if name == "era5" else ("time", "prediction_timedelta")
        if name == "neuralgcm_ens":
            lead = ("time", "prediction_timedelta", "member")
        for v in WIND:
            assert out[v].dims == (*lead, *horizontal), (name, out[v].dims)
    # and a lat-before-lon forecast store is reordered too
    make_forecast(src / "hres.zarr", lonlat=False)
    import shutil
    shutil.rmtree(cache_path(cfg, "hres"))
    fetch(cfg, ["hres"], open_store=open_store)
    assert xr.open_zarr(cache_path(cfg, "hres"))[WIND[0]].dims == (
        "time", "prediction_timedelta", "latitude", "longitude")


def test_geopotential_caches_also_have_contract_dim_order(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["geopotential"], open_store=open_store)
    assert xr.open_zarr(cache_path(cfg, "geopotential_era5"))["geopotential"].dims == (
        "time", "latitude", "longitude")
    assert xr.open_zarr(cache_path(cfg, "geopotential_hres"))["geopotential"].dims == (
        "time", "prediction_timedelta", "latitude", "longitude")


def test_round_trip_through_sources(world):
    from regret import sources
    cfg, open_store, _, src = world
    sources._open.cache_clear()
    sources._truth.cache_clear()
    fetch(cfg, ["era5", "hres"], open_store=open_store)
    flight = flights(cfg)[0]
    lead = cfg.leads_h[0]
    init = np.datetime64(flight.departure_time, "ns") - np.timedelta64(lead, "h")
    raw = xr.open_zarr(src / "hres.zarr", consolidated=False, decode_timedelta=False)
    want = float(raw[WIND[0]].sel(time=init, prediction_timedelta=lead, level=250,
                                  latitude=50.0, longitude=350.0))
    wind = sources.forecast_winds(cfg, "hres", flight, lead)
    u, _ = wind.uv(50.0, -10.0, init + np.timedelta64(lead, "h"))
    assert float(u) == pytest.approx(want)
    # the step 6 h later is a different stored value, so a shifted step would be caught
    other = float(raw[WIND[0]].sel(time=init, prediction_timedelta=lead + 6, level=250,
                                   latitude=50.0, longitude=350.0))
    u6, _ = wind.uv(50.0, -10.0, init + np.timedelta64(lead + 6, "h"))
    assert float(u6) == pytest.approx(other) and other != want
    t = np.datetime64(cfg.era5_start, "ns")
    raw_t = xr.open_zarr(src / "era5.zarr", consolidated=False)
    want_t = float(raw_t[WIND[0]].sel(time=t, level=250, latitude=50.0, longitude=350.0))
    ut, _ = sources.truth_winds(cfg).uv(50.0, -10.0, t)
    assert float(ut) == pytest.approx(want_t)


# --- B2: compact cache writes ---------------------------------------------------------------

def _needed_pairs(cfg):
    """(init, step hours) pairs some flight x lead reads: written out longhand, independent of fetch."""
    return {
        (np.datetime64(f.departure_time, "ns") - np.timedelta64(lead, "h"), h)
        for f in flights(cfg)
        for lead in cfg.leads_h
        for h in (lead, lead + 6, lead + 12)
    }


def test_forecast_cache_is_finite_exactly_at_needed_pairs(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["hres"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "hres")).load()
    need = _needed_pairs(cfg)
    hours = out.prediction_timedelta.values // np.timedelta64(1, "h")
    for var in WIND:
        finite = np.isfinite(out[var].values).all(axis=(2, 3))
        got = {(out.time.values[i], int(hours[j])) for i, j in zip(*np.nonzero(finite))}
        assert got == need
        assert np.isnan(out[var].values[~finite]).all()
    assert len(need) < out.sizes["time"] * out.sizes["prediction_timedelta"]  # the mask removes something


def test_truth_cache_is_not_masked(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["era5"], open_store=open_store)
    assert np.isfinite(xr.open_zarr(cache_path(cfg, "era5"))[WIND[0]].values).all()


def test_written_variables_are_one_blosc_zstd_chunk(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["era5", "hres"], open_store=open_store)
    for name in ("era5", "hres"):
        out = xr.open_zarr(cache_path(cfg, name))
        for var in WIND:
            enc = out[var].encoding
            assert tuple(enc["chunks"]) == out[var].shape
            (comp,) = enc["compressors"]
            assert type(comp).__name__ == "BloscCodec" and "zstd" in str(comp.cname).lower()


def test_needed_pair_that_is_nan_in_the_store_raises(world):
    cfg, open_store, _, src = world
    flight, lead = flights(cfg)[0], cfg.leads_h[0]
    init = np.datetime64(flight.departure_time, "ns") - np.timedelta64(lead, "h")
    raw = xr.open_zarr(src / "hres.zarr", consolidated=False, decode_timedelta=False).load()
    raw[WIND[0]].loc[dict(time=init, prediction_timedelta=lead)] = np.nan

    def bad_store(url):
        return raw

    with pytest.raises(MissingDataError, match="finite|NaN|nan"):
        fetch(cfg, ["hres"], open_store=bad_store)
    assert not cache_path(cfg, "hres").exists()


def test_every_flight_lead_source_reads_finite_winds_over_the_window(world):
    from regret import sources
    cfg, open_store, _, _ = world
    sources._open.cache_clear()
    sources._truth.cache_clear()
    names = ["era5", "hres", "graphcast", "pangu"]
    fetch(cfg, names, open_store=open_store)
    for source in ("hres", "graphcast", "pangu"):
        for flight in flights(cfg):
            for lead in cfg.leads_h:
                wind = sources.forecast_winds(cfg, source, flight, lead)
                for h in (0, 6, 12):
                    t = np.datetime64(flight.departure_time, "ns") + np.timedelta64(h, "h")
                    u, v = wind.uv(50.0, -10.0, t)
                    assert np.isfinite(u) and np.isfinite(v), (source, flight, lead, h)


def test_cache_written_before_b2_still_counts_as_complete(world, caplog):
    cfg, open_store, reads, _ = world
    # a B1-style cache: full rectangle, default encoding, no masking
    url = store_url(next(d for d in cfg.datasets if d.name == "hres"))
    ds = fetch_mod._subset(cfg, "forecast", url, open_store(url), WIND)
    fetch_mod._write(ds, cache_path(cfg, "hres"))
    reads.clear()
    with caplog.at_level(logging.INFO, logger="regret.fetch"):
        report = fetch(cfg, ["hres"], open_store=open_store)
    assert report.downloads == 0 and reads == []


def test_core_needed_pairs_and_strict_errors_unchanged(world):
    cfg, open_store, _, src = world
    want = {
        (np.datetime64(f.departure_time, "ns") - np.timedelta64(lead, "h"),
         np.timedelta64(h, "h").astype("timedelta64[ns]"))
        for f in flights(cfg) for lead in cfg.leads_h for h in (lead, lead + 6, lead + 12)
    }
    assert fetch_mod.needed_pairs(cfg) == want
    for name in ("hres", "graphcast", "pangu", "geopotential"):
        assert fetch_mod.needed_pairs(cfg, None) == want and fetch_mod._own_rules(name) is None
    # a core store missing an init still raises (strict), naming the store and the init
    make_forecast(src / "hres.zarr", drop_inits=["2020-02-04T00"])
    with pytest.raises(MissingDataError, match="2020-02-04T00"):
        fetch(cfg, ["hres"], open_store=open_store)


def test_neuralgcm_fetches_only_matched_pairs_at_12h(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["neuralgcm"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "neuralgcm"))
    need = fetch_mod.needed_pairs(cfg, "neuralgcm")
    assert {h for lead in cfg.leads_h for h in (lead, lead + 12)} == set(
        out.prediction_timedelta.values // np.timedelta64(1, "h"))
    assert all(pair[1] // np.timedelta64(1, "h") % 12 == 0 for pair in need)
    inits, steps = out.time.values, out.prediction_timedelta.values
    finite = np.isfinite(out[WIND[0]]).all(("latitude", "longitude")).values
    for i, t in enumerate(inits):
        for j, s in enumerate(steps):
            assert finite[i, j] == ((t, s) in need)


def test_neuralgcm_matched_flights_only(world):
    """Full-config shape: flights without an init at every lead are ignored, not an error."""
    cfg, open_store, _, src = world
    cfg = dataclasses.replace(
        cfg, first_departure_date=cfg.first_departure_date.replace(year=2020, month=1, day=3),
        last_departure_date=cfg.first_departure_date.replace(year=2020, month=1, day=8),
    )
    from regret.config import matched_flights
    assert 0 < len(matched_flights(cfg, "neuralgcm")) < len(flights(cfg))
    inits = fetch_mod._expected_inits(cfg, "neuralgcm")
    assert inits.min() >= np.datetime64("2020-01-01", "ns")
    assert fetch_mod._expected_inits(cfg).min() < np.datetime64("2020-01-01", "ns")  # core would need them


def test_ensemble_realization_is_renamed_to_member(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["neuralgcm_ens"], open_store=open_store)
    out = xr.open_zarr(cache_path(cfg, "neuralgcm_ens"))
    assert "realization" not in out.dims and out.sizes["member"] == 3
    assert out[WIND[0]].dims == ("time", "prediction_timedelta", "member", "latitude", "longitude")
    assert out.latitude.min() >= 25 and out.longitude.max() <= 20


def test_neuralgcm_missing_matched_init_is_strict(world):
    cfg, open_store, _, src = world
    make_neuralgcm(src / "neuralgcm.zarr", drop_inits=["2020-02-05T12"])
    with pytest.raises(MissingDataError, match="2020-02-05T12"):
        fetch(cfg, ["neuralgcm"], open_store=open_store)


def test_neuralgcm_second_run_is_cached(world):
    cfg, open_store, reads, _ = world
    fetch(cfg, ["neuralgcm"], open_store=open_store)
    fetch(cfg, ["neuralgcm"], open_store=open_store)
    assert len(reads) == 1


def test_neuralgcm_registry_stays_opt_in():
    assert not any(d.fetch_by_default for d in FIXTURE.datasets if d.name.startswith("neuralgcm"))


def test_ensemble_cache_is_one_chunk_per_member_and_core_stays_one_chunk(world):
    cfg, open_store, _, _ = world
    fetch(cfg, ["neuralgcm_ens", "hres"], open_store=open_store)
    ens = xr.open_zarr(cache_path(cfg, "neuralgcm_ens"))
    for var in WIND:
        enc = ens[var].encoding
        want = tuple(1 if d == "member" else n for d, n in zip(ens[var].dims, ens[var].shape))
        assert tuple(enc["chunks"]) == want
        (comp,) = enc["compressors"]
        assert type(comp).__name__ == "BloscCodec" and "zstd" in str(comp.cname).lower()
    core = xr.open_zarr(cache_path(cfg, "hres"))
    assert all(tuple(core[v].encoding["chunks"]) == core[v].shape for v in WIND)


def test_completeness_check_recognises_member_chunked_and_single_chunk_caches(world):
    cfg, open_store, reads, _ = world
    fetch(cfg, ["neuralgcm_ens", "hres"], open_store=open_store)
    reads.clear()
    assert fetch(cfg, ["neuralgcm_ens", "hres"], open_store=open_store).downloads == 0
    assert reads == []
