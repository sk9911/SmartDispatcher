"""Truth and forecast wind sources read from the local cache (CONTRACTS 2.6)."""
from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import xarray as xr

from regret.config import cache_path
from regret.types import Config, Flight, SourceName, WindField
from regret.winds import FrozenWind, GridWind, from_dataset


FLIGHT_WINDOW_H = 12


class MissingForecastError(Exception):
    """A forecast cache or init is missing; the message names source, init and path."""


@lru_cache(maxsize=None)
def _open(path: Path) -> xr.Dataset:
    """Open a cached zarr once per process (computed ~2,500 times by compute).

    An ensemble store (a ``member`` dimension, ~800 MB) stays lazy; ``forecast_winds``
    loads only the one init and member it needs.
    """
    ds = xr.open_zarr(path)
    return ds if "member" in ds.dims else ds.load()


@lru_cache(maxsize=4)
def _member_ds(path: Path, member: int) -> xr.Dataset:
    """One member of an ensemble cache, loaded (~23 MB). The store is a single zarr chunk,
    so a miss decompresses all members (~1 s, ~1.7 GB transient); callers should iterate
    member-major so each member misses once."""
    return _open(path).sel(member=member, drop=True).load()


@lru_cache(maxsize=4)
def _truth(path: Path) -> GridWind:
    return from_dataset(_open(path))


def truth_winds(cfg: Config) -> WindField:
    """ERA5 over the whole cache window."""
    return _truth(cache_path(cfg, "era5"))


def forecast_winds(
    cfg: Config,
    source: SourceName,
    flight: Flight,
    lead_h: int,
    *,
    step_h: int | None = None,
    member: int | None = None,
) -> WindField:
    """Winds ``source`` forecast for ``flight`` from the init ``lead_h`` hours before departure.

    ``step_h=None`` uses the dataset's native steps from lead to lead + 12 h. ``step_h=12``
    uses only the steps at lead and lead + 12 h (linear in time between them), for any source.
    ``member`` picks one member of an ensemble cache, which is then required.
    """
    if step_h not in (None, FLIGHT_WINDOW_H):
        raise ValueError(f"step_h must be None or {FLIGHT_WINDOW_H}, got {step_h!r}")
    init = np.datetime64(flight.departure_time - timedelta(hours=lead_h), "ns")
    if source == "persistence":
        if member is not None:
            raise ValueError("member applies only to an ensemble source, not persistence")
        return FrozenWind(truth_winds(cfg), at=init)
    path = cache_path(cfg, source)
    if not path.exists():
        raise MissingForecastError(f"source {source!r}: no cache at {path} (init {init})")
    ds = _open(path)
    is_ensemble = "member" in ds.dims
    if is_ensemble and member is None:
        raise ValueError(f"source {source!r} is an ensemble: pass member=")
    if member is not None and not is_ensemble:
        raise ValueError(f"member given but source {source!r} has no member dimension")
    if init not in ds["time"].values:
        raise MissingForecastError(f"source {source!r}: init {init} not in cache {path}")
    one = (_member_ds(path, member) if is_ensemble else ds).sel(time=init, drop=True)
    lead = np.timedelta64(lead_h, "h")
    end = lead + np.timedelta64(FLIGHT_WINDOW_H, "h")
    if step_h is None:
        one = one.sel(prediction_timedelta=slice(lead, end))
    else:
        steps = one["prediction_timedelta"].values
        if not (lead in steps and end in steps):
            raise MissingForecastError(
                f"source {source!r}: steps {lead_h} h and {lead_h + FLIGHT_WINDOW_H} h not both in {path}"
            )
        one = one.sel(prediction_timedelta=[lead, end])
    one = one.load()
    if one.sizes["prediction_timedelta"] == 0:
        raise MissingForecastError(f"source {source!r}: no steps for lead {lead_h} h in {path}")
    valid = init + one["prediction_timedelta"].values
    one = one.rename(prediction_timedelta="time").assign_coords(time=valid)
    return from_dataset(one)
