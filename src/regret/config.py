"""Configuration: full and fixture modes, dataset registry (docs/CONTRACTS.md 1.1, 1.2, 2.2)."""

from __future__ import annotations

import dataclasses
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from regret.types import (
    JFK,
    LHR,
    Box,
    Config,
    Dataset,
    Flight,
    Leg,
    make_flight,
)

GCS_PREFIX = "gs://weatherbench2/"
_WIND = ("u_component_of_wind", "v_component_of_wind")
_GRID = "240x121_equiangular_with_poles_conservative.zarr"

DATASETS: tuple[Dataset, ...] = (
    Dataset("era5", f"datasets/era5/1959-2022-6h-{_GRID}", _WIND, True, "truth", ()),
    Dataset("hres", f"datasets/hres/2016-2022-0012-{_GRID}", _WIND, True, "forecast", ()),
    Dataset(
        "graphcast",
        f"datasets/graphcast/2020/date_range_2019-11-16_2021-02-01_12_hours-{_GRID}",
        _WIND,
        True,
        "forecast",
        (),
    ),
    Dataset("pangu", f"datasets/pangu/2018-2022_0012_{_GRID}", _WIND, True, "forecast", ()),
    Dataset(
        "neuralgcm", f"datasets/neuralgcm_deterministic/2020-{_GRID}", _WIND, False, "forecast", ()
    ),
    Dataset("neuralgcm_ens", f"datasets/neuralgcm_ens/2020-{_GRID}", _WIND, False, "ensemble", ()),
    Dataset(
        "geopotential",
        "",
        ("geopotential",),
        False,
        "extra",
        ("era5", "hres", "graphcast", "pangu"),
    ),
)

# Per-dataset forecast resolution (the add-on, SPEC 1.5). Datasets not listed are core:
# 6-hourly steps and no first init. ``Dataset`` lives in types.py, so these are kept here.
CORE_STEP_H = 6
NEURALGCM_FIRST_INIT = datetime(2020, 1, 1, 0)
_STEP_H = {"neuralgcm": 12, "neuralgcm_ens": 12}
_FIRST_INIT = {"neuralgcm": NEURALGCM_FIRST_INIT, "neuralgcm_ens": NEURALGCM_FIRST_INIT}

_COMMON = dict(
    datasets=DATASETS,
    sources=("hres", "graphcast", "pangu", "persistence"),
    leads_h=(12, 24, 48, 72, 120),
    box=Box(25.0, 75.0, -100.0, 20.0),
    legs=(Leg(JFK, LHR, 0), Leg(LHR, JFK, 12)),
    showcase_departure=datetime(2020, 2, 9, 0),
    workers=os.cpu_count() or 1,
)

FULL = Config(
    mode="full",
    first_departure_date=date(2020, 1, 1),
    last_departure_date=date(2020, 2, 29),
    era5_start=datetime(2019, 12, 27, 0),
    era5_end=datetime(2020, 3, 1, 12),
    cache_dir=Path("data/cache"),
    results_path=Path("data/results/regret.parquet"),
    report_path=Path("reports/report.html"),
    **_COMMON,
)

FIXTURE = Config(
    mode="fixture",
    first_departure_date=date(2020, 2, 8),
    last_departure_date=date(2020, 2, 10),
    era5_start=datetime(2020, 2, 3, 0),
    era5_end=datetime(2020, 2, 11, 12),
    cache_dir=Path("tests/fixtures"),
    results_path=Path("tests/fixture_results/regret.parquet"),
    report_path=Path("reports/report-fixture.html"),
    **_COMMON,
)

_MODES = {"full": FULL, "fixture": FIXTURE}


def get_config(mode: str | None = None) -> Config:
    """Config for `mode`; None reads REGRET_CONFIG (default "full").

    REGRET_WORKERS, when set, overrides `workers`.
    """
    if mode is None:
        mode = os.environ.get("REGRET_CONFIG") or "full"
    if mode not in _MODES:
        raise ValueError(f"unknown config mode {mode!r}; expected one of {sorted(_MODES)}")
    cfg = _MODES[mode]
    workers = os.environ.get("REGRET_WORKERS")
    if workers:
        cfg = dataclasses.replace(cfg, workers=int(workers))
    return cfg


def store_url(dataset: Dataset) -> str:
    if "://" in dataset.store or dataset.store.startswith("/"):
        return dataset.store
    return GCS_PREFIX + dataset.store


def cache_path(cfg: Config, name: str) -> Path:
    return cfg.cache_dir / f"{name}.zarr"


def flights(cfg: Config) -> tuple[Flight, ...]:
    out = []
    day = cfg.first_departure_date
    while day <= cfg.last_departure_date:
        for leg in cfg.legs:
            dep = datetime(day.year, day.month, day.day, leg.departure_hour_utc)
            out.append(make_flight(leg.origin, leg.destination, dep))
        day += timedelta(days=1)
    return tuple(sorted(out, key=lambda f: (f.departure_time, f.direction)))


def showcase_flight(cfg: Config) -> Flight:
    return make_flight(JFK, LHR, cfg.showcase_departure)


def step_h(name: str) -> int:
    """Prediction-step resolution in hours of dataset `name` (6 for the core datasets)."""
    return _STEP_H.get(name, CORE_STEP_H)


def first_init(name: str) -> datetime | None:
    """Earliest initialisation in dataset `name`; None when the store covers every needed init."""
    return _FIRST_INIT.get(name)


def matched_flights(cfg: Config, name: str) -> tuple[Flight, ...]:
    """Flights with an init available at every lead: departure - lead >= first_init.

    All flights for a dataset without a first init.
    """
    start = first_init(name)
    if start is None:
        return flights(cfg)
    earliest = max(cfg.leads_h)
    return tuple(f for f in flights(cfg) if f.departure_time - timedelta(hours=earliest) >= start)
