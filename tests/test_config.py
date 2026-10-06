import dataclasses
import os
from datetime import date, datetime
from pathlib import Path

import pytest

from regret import config
from regret.config import cache_path, flights, get_config, showcase_flight, store_url


def test_full_mode():
    cfg = get_config("full")
    assert cfg.mode == "full"
    assert (cfg.last_departure_date - cfg.first_departure_date).days + 1 == 60
    assert cfg.first_departure_date == date(2020, 1, 1)
    assert cfg.last_departure_date == date(2020, 2, 29)
    fl = flights(cfg)
    assert len(fl) == 120
    assert {f.direction for f in fl} == {"eastbound", "westbound"}
    assert cfg.leads_h == (12, 24, 48, 72, 120)
    assert cfg.sources == ("hres", "graphcast", "pangu", "persistence")
    b = cfg.box
    assert (b.lat_min_deg, b.lat_max_deg, b.lon_min_deg, b.lon_max_deg) == (25, 75, -100, 20)
    assert cfg.era5_start == datetime(2019, 12, 27, 0)
    assert cfg.era5_end == datetime(2020, 3, 1, 12)
    assert cfg.results_path == Path("data/results/regret.parquet")
    assert cfg.report_path == Path("reports/report.html")
    assert cfg.cache_dir == Path("data/cache")
    assert cfg.showcase_departure == datetime(2020, 2, 9, 0)


def test_fixture_mode():
    cfg = get_config("fixture")
    assert cfg.mode == "fixture"
    assert cfg.first_departure_date == date(2020, 2, 8)
    assert cfg.last_departure_date == date(2020, 2, 10)
    assert len(flights(cfg)) == 6
    assert cfg.era5_start == datetime(2020, 2, 3, 0)
    assert cfg.era5_end == datetime(2020, 2, 11, 12)
    assert cfg.results_path == Path("tests/fixture_results/regret.parquet")
    assert cfg.report_path == Path("reports/report-fixture.html")
    assert cfg.cache_dir == Path("tests/fixtures")
    assert cfg.leads_h == (12, 24, 48, 72, 120)


@pytest.mark.parametrize("mode", ["full", "fixture"])
def test_era5_window_and_legs(mode):
    cfg = get_config(mode)
    first = min(f.departure_time for f in flights(cfg))
    assert (first - cfg.era5_start).total_seconds() >= 120 * 3600
    assert [(l.origin.code, l.destination.code, l.departure_hour_utc) for l in cfg.legs] == [
        ("JFK", "LHR", 0),
        ("LHR", "JFK", 12),
    ]


@pytest.mark.parametrize("mode", ["full", "fixture"])
def test_flights_sorted_and_in_box(mode):
    cfg = get_config(mode)
    fl = flights(cfg)
    keys = [(f.departure_time, f.direction) for f in fl]
    assert keys == sorted(keys)
    assert len({f.flight_id for f in fl}) == len(fl)
    b = cfg.box
    for f in fl:
        for a in (f.origin, f.destination):
            assert b.lat_min_deg <= a.lat_deg <= b.lat_max_deg
            assert b.lon_min_deg <= a.lon_deg <= b.lon_max_deg


def test_showcase_flight():
    f = showcase_flight(get_config("fixture"))
    assert f.flight_id == "JFK-LHR-20200209T0000"
    assert f in flights(get_config("fixture"))
    assert f in flights(get_config("full"))


def test_dataset_registry():
    cfg = get_config("full")
    ds = {d.name: d for d in cfg.datasets}
    assert set(ds) == {"era5", "hres", "graphcast", "pangu", "neuralgcm", "neuralgcm_ens", "geopotential"}
    assert ds["era5"].store == "datasets/era5/1959-2022-6h-240x121_equiangular_with_poles_conservative.zarr"
    assert ds["hres"].store == "datasets/hres/2016-2022-0012-240x121_equiangular_with_poles_conservative.zarr"
    assert ds["graphcast"].store == (
        "datasets/graphcast/2020/date_range_2019-11-16_2021-02-01_12_hours-240x121_equiangular_with_poles_conservative.zarr"
    )
    assert ds["pangu"].store == "datasets/pangu/2018-2022_0012_240x121_equiangular_with_poles_conservative.zarr"
    assert ds["neuralgcm"].store == "datasets/neuralgcm_deterministic/2020-240x121_equiangular_with_poles_conservative.zarr"
    assert ds["neuralgcm_ens"].store == "datasets/neuralgcm_ens/2020-240x121_equiangular_with_poles_conservative.zarr"
    assert ds["geopotential"].store == ""
    assert ds["geopotential"].derived_from == ("era5", "hres", "graphcast", "pangu")
    assert ds["geopotential"].variables == ("geopotential",)
    for n in ("era5", "hres", "graphcast", "pangu"):
        assert ds[n].fetch_by_default
        assert ds[n].variables == ("u_component_of_wind", "v_component_of_wind")
    for n in ("neuralgcm", "neuralgcm_ens", "geopotential"):
        assert not ds[n].fetch_by_default
    assert ds["era5"].kind == "truth"
    assert ds["neuralgcm_ens"].kind == "ensemble"
    assert ds["geopotential"].kind == "extra"
    assert {d.name for d in cfg.datasets if d.fetch_by_default} == {"era5", "hres", "graphcast", "pangu"}
    # every source except persistence is a dataset
    assert set(cfg.sources) - {"persistence"} <= set(ds)
    assert get_config("fixture").datasets == cfg.datasets


def test_store_url_and_cache_path(tmp_path):
    cfg = get_config("full")
    era5 = next(d for d in cfg.datasets if d.name == "era5")
    assert store_url(era5) == "gs://weatherbench2/" + era5.store
    local = dataclasses.replace(era5, store="/tmp/x.zarr")
    assert store_url(local) == "/tmp/x.zarr"
    remote = dataclasses.replace(era5, store="file:///tmp/x.zarr")
    assert store_url(remote) == "file:///tmp/x.zarr"
    assert cache_path(cfg, "era5") == Path("data/cache/era5.zarr")
    assert cache_path(dataclasses.replace(cfg, cache_dir=tmp_path), "hres") == tmp_path / "hres.zarr"


def test_env_selects_mode(monkeypatch):
    monkeypatch.setenv("REGRET_CONFIG", "full")
    assert get_config().mode == "full"
    monkeypatch.setenv("REGRET_CONFIG", "fixture")
    assert get_config().mode == "fixture"
    monkeypatch.delenv("REGRET_CONFIG")
    assert get_config().mode == "full"
    with pytest.raises(ValueError):
        get_config("bogus")


def test_env_workers(monkeypatch):
    monkeypatch.delenv("REGRET_WORKERS", raising=False)
    assert get_config("full").workers == (os.cpu_count() or 1)
    monkeypatch.setenv("REGRET_WORKERS", "3")
    assert get_config("full").workers == 3
    assert get_config("fixture").workers == 3
    assert config.FULL.mode == "full" and config.FIXTURE.mode == "fixture"


def test_step_resolution_and_first_init_registry():
    from datetime import datetime

    from regret.config import first_init, step_h

    for n in ("era5", "hres", "graphcast", "pangu", "geopotential"):
        assert step_h(n) == 6 and first_init(n) is None
    for n in ("neuralgcm", "neuralgcm_ens"):
        assert step_h(n) == 12 and first_init(n) == datetime(2020, 1, 1, 0)


def test_matched_flights_counts():
    from regret.config import matched_flights

    full, fixture = get_config("full"), get_config("fixture")
    assert len(flights(full)) == 120
    for n in ("neuralgcm", "neuralgcm_ens"):
        m = matched_flights(full, n)
        assert len(m) == 110
        assert min(f.departure_time for f in m).date().isoformat() == "2020-01-06"
        assert all(f in flights(full) for f in m)
        assert matched_flights(fixture, n) == flights(fixture) and len(flights(fixture)) == 6
    assert matched_flights(full, "hres") == flights(full)
