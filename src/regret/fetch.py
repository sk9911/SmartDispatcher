"""Fetch WeatherBench 2 winds into the local cache (docs/CONTRACTS.md 2.5).

The only step that touches the network. One zarr per dataset at
``config.cache_path(cfg, name)``: 250 hPa, the box, latitude ascending,
longitude -180..180.
"""
from __future__ import annotations

import argparse
import logging
import shutil
import time as _time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import xarray as xr
from zarr.codecs import BloscCodec, BloscShuffle

from regret.config import cache_path, flights, get_config, first_init, matched_flights, step_h, store_url
from regret.types import Config, Dataset
from regret.winds import normalise

GCS_BUCKET = "gs://weatherbench2"
SHUFFLE = BloscShuffle.shuffle  # byte shuffle
LEVEL_HPA = 250
STEP_H = 6  # core step resolution; config.step_h(name) gives each dataset's own
FLIGHT_WINDOW_H = 12  # prediction steps cover lead ... lead + 12 h

log = logging.getLogger("regret.fetch")


class MissingDataError(Exception):
    """A store lacks the level, init or prediction step the study needs."""


@dataclass(frozen=True)
class FetchReport:
    downloads: int
    elapsed_s: float
    datasets: tuple[str, ...]


def _open_anonymous(url: str) -> xr.Dataset:
    # decode_timedelta=False: keep prediction_timedelta as stored; _decode_steps reads its units
    return xr.open_zarr(url, storage_options={"token": "anon"}, chunks=None, decode_timedelta=False)


_UNIT_NS = {
    "nanoseconds": 1, "nanosecond": 1,
    "microseconds": 1_000, "microsecond": 1_000,
    "milliseconds": 1_000_000, "millisecond": 1_000_000,
    "seconds": 10**9, "second": 10**9,
    "minutes": 60 * 10**9, "minute": 60 * 10**9,
    "hours": 3600 * 10**9, "hour": 3600 * 10**9,
    "days": 86400 * 10**9, "day": 86400 * 10**9,
}
# dimension order of every written cache (CONTRACTS 2.5)
_DIM_ORDER = ("time", "prediction_timedelta", "member", "latitude", "longitude")


def _decode_steps(url: str, ds: xr.Dataset) -> xr.Dataset:
    """Return ds with prediction_timedelta as timedelta64[ns], decoded from its ``units`` attribute."""
    if "prediction_timedelta" not in ds.coords:
        return ds
    coord = ds["prediction_timedelta"]
    if coord.dtype.kind == "m":
        return ds.assign_coords(prediction_timedelta=coord.values.astype("timedelta64[ns]"))
    units = str(coord.attrs.get("units", "")).strip().lower()
    if units not in _UNIT_NS:
        raise MissingDataError(
            f"{url}: cannot decode prediction_timedelta: units {coord.attrs.get('units')!r} "
            f"not one of {sorted(_UNIT_NS)}"
        )
    values = coord.values
    if values.dtype.kind not in "iuf" or not np.all(np.isfinite(values)) or np.any(values != np.round(values)):
        raise MissingDataError(f"{url}: prediction_timedelta values are not whole {units}")
    steps = values.astype("int64") * np.int64(_UNIT_NS[units])
    return ds.assign_coords(
        prediction_timedelta=("prediction_timedelta", steps.astype("timedelta64[ns]"))
    )


def _expected_times(cfg: Config) -> np.ndarray:
    """Truth times: 6-hourly from era5_start to era5_end."""
    return np.arange(
        np.datetime64(cfg.era5_start, "ns"),
        np.datetime64(cfg.era5_end, "ns") + np.timedelta64(1, "ns"),
        np.timedelta64(STEP_H, "h"),
    )


def _expected_inits(cfg: Config, name: str | None = None) -> np.ndarray:
    inits = {
        np.datetime64(f.departure_time, "ns") - np.timedelta64(lead, "h")
        for f in _flights_for(cfg, name)
        for lead in cfg.leads_h
    }
    return np.array(sorted(inits), dtype="datetime64[ns]")


def _flights_for(cfg: Config, name: str | None):
    """Core datasets read every flight; the add-on's NeuralGCM stores only the matched ones."""
    return flights(cfg) if name is None else matched_flights(cfg, name)


def _window_steps(lead: int, name: str | None) -> range:
    return range(lead, lead + FLIGHT_WINDOW_H + 1, STEP_H if name is None else step_h(name))


def _expected_steps(cfg: Config, name: str | None = None) -> np.ndarray:
    steps = {
        np.timedelta64(h, "h").astype("timedelta64[ns]")
        for lead in cfg.leads_h
        for h in _window_steps(lead, name)
    }
    return np.array(sorted(steps), dtype="timedelta64[ns]")


def needed_pairs(cfg: Config, name: str | None = None) -> set[tuple[np.datetime64, np.timedelta64]]:
    """(init, step) pairs some flight x lead reads: init = departure - lead, steps lead ... lead + 12 h.

    The same rule as ``sources.forecast_winds``; every other pair of a forecast cache is masked to NaN.
    With a dataset `name` (the NeuralGCM add-on) only its matched flights count, at its own step
    resolution (12 h: steps lead and lead + 12). ``None`` is the core rule.
    """
    return {
        (
            np.datetime64(f.departure_time, "ns") - np.timedelta64(lead, "h"),
            np.timedelta64(h, "h").astype("timedelta64[ns]"),
        )
        for f in _flights_for(cfg, name)
        for lead in cfg.leads_h
        for h in _window_steps(lead, name)
    }


def _own_rules(store_name: str) -> str | None:
    """The dataset name when it follows its own init/step rules (NeuralGCM add-on); None for core."""
    return store_name if first_init(store_name) is not None or step_h(store_name) != STEP_H else None


def _mask_unneeded(cfg: Config, url: str, ds: xr.Dataset, name: str | None = None) -> xr.Dataset:
    """NaN every (init, step) pair no flight reads; raise if a needed pair is not finite."""
    need = needed_pairs(cfg, name)
    inits, steps = ds["time"].values, ds["prediction_timedelta"].values
    keep = np.array([[(i, s) in need for s in steps] for i in inits])
    mask = xr.DataArray(keep, dims=("time", "prediction_timedelta"),
                        coords={"time": ds["time"], "prediction_timedelta": ds["prediction_timedelta"]})
    masked = ds.where(mask)
    for var in masked.data_vars:
        other = [d for d in masked[var].dims if d not in ("time", "prediction_timedelta")]
        finite = np.isfinite(masked[var]).all(other) if other else np.isfinite(masked[var])
        bad = ~finite.transpose("time", "prediction_timedelta").values & keep
        if bad.any():
            i, j = np.argwhere(bad)[0]
            raise MissingDataError(
                f"{url}: {var} is not finite (NaN) at init {inits[i]}, step {steps[j]}"
                f" ({int(bad.sum())} needed pairs)"
            )
    return masked


def _require(url: str, ds: xr.Dataset, dim: str, needed: np.ndarray, label: str) -> None:
    if dim not in ds.coords:
        raise MissingDataError(f"{url}: no {dim!r} coordinate (needed {label})")
    missing = np.setdiff1d(needed, ds[dim].values)
    if missing.size:
        shown = ", ".join(str(m) for m in missing[:5])
        more = f" (+{missing.size - 5} more)" if missing.size > 5 else ""
        raise MissingDataError(f"{url}: missing {label}: {shown}{more}")


def _subset(
    cfg: Config, kind: str, url: str, ds: xr.Dataset, variables: Sequence[str], name: str | None = None
) -> xr.Dataset:
    if "level" not in ds.coords or LEVEL_HPA not in ds["level"].values:
        raise MissingDataError(f"{url}: level {LEVEL_HPA} hPa not in store")
    absent = [v for v in variables if v not in ds.data_vars]
    if absent:
        raise MissingDataError(f"{url}: missing variables {absent}")
    ds = ds[list(variables)].sel(level=LEVEL_HPA)
    if "realization" in ds.dims:  # NeuralGCM ensemble: the contract calls it member
        ds = ds.rename(realization="member")
    if kind != "truth":
        ds = _decode_steps(url, ds)
    if kind == "truth":
        times = _expected_times(cfg)
        _require(url, ds, "time", times, "times")
        ds = ds.sel(time=times)
    else:
        inits, steps = _expected_inits(cfg, name), _expected_steps(cfg, name)
        _require(url, ds, "time", inits, "inits")
        _require(url, ds, "prediction_timedelta", steps, "prediction steps")
        ds = ds.sel(time=inits, prediction_timedelta=steps)
    ds = normalise(ds)
    box = cfg.box
    ds = ds.sel(
        latitude=slice(box.lat_min_deg, box.lat_max_deg),
        longitude=slice(box.lon_min_deg, box.lon_max_deg),
    )
    ds = ds.transpose(*(d for d in _DIM_ORDER if d in ds.dims))
    for var in ds.variables.values():
        var.encoding = {}
    return ds.load()


def _write(ds: xr.Dataset, path) -> None:
    tmp = path.with_name(path.name + ".partial")
    shutil.rmtree(tmp, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    comp = BloscCodec(cname="zstd", clevel=9, shuffle=SHUFFLE)
    # One chunk per variable (B2); ensembles get one chunk per member so a member read
    # decompresses only that member.
    encoding = {
        v: {"compressors": [comp],
            "chunks": tuple(1 if d == "member" else n for d, n in zip(ds[v].dims, ds[v].shape))}
        for v in ds.data_vars
    }
    ds.to_zarr(tmp, mode="w", encoding=encoding)
    shutil.rmtree(path, ignore_errors=True)
    tmp.rename(path)


def _is_complete(cfg: Config, kind: str, path, variables: Sequence[str], name: str | None = None) -> bool:
    """True when the cached zarr has every variable, time and prediction step it should."""
    if not path.exists():
        return False
    try:
        with xr.open_zarr(path, chunks=None) as ds:
            if not set(variables) <= set(ds.data_vars):
                return False
            if kind == "truth":
                want = {"time": _expected_times(cfg)}
            else:
                want = {"time": _expected_inits(cfg, name), "prediction_timedelta": _expected_steps(cfg, name)}
            for dim, needed in want.items():
                if not np.array_equal(np.sort(ds[dim].values), needed):
                    return False
            return ds.sizes["latitude"] > 0 and ds.sizes["longitude"] > 0
    except Exception:  # unreadable or half-written cache: fetch again
        return False


def _jobs(cfg: Config, names: Sequence[str]) -> list[tuple[str, Dataset, str, Sequence[str]]]:
    """(output name, store dataset, kind, variables) for each requested name."""
    by_name = {d.name: d for d in cfg.datasets}
    jobs = []
    for name in names:
        if name not in by_name:
            raise ValueError(f"unknown dataset {name!r}; expected one of {sorted(by_name)}")
        d = by_name[name]
        if d.derived_from:
            for src in d.derived_from:
                jobs.append((f"{name}_{src}", by_name[src], by_name[src].kind, d.variables))
        else:
            jobs.append((name, d, d.kind, d.variables))
    return jobs


def fetch(
    cfg: Config,
    names: Sequence[str] | None = None,
    *,
    open_store: Callable[[str], xr.Dataset] | None = None,
) -> FetchReport:
    start = _time.perf_counter()
    open_store = open_store or _open_anonymous
    if names is None:
        names = [d.name for d in cfg.datasets if d.fetch_by_default]
    downloads = 0
    done = []
    for out_name, store, kind, variables in _jobs(cfg, names):
        path = cache_path(cfg, out_name)
        done.append(out_name)
        own = _own_rules(store.name)
        if _is_complete(cfg, kind, path, variables, own):
            log.info("%s: cached, skipped", out_name)
            continue
        url = store_url(store)
        ds = _subset(cfg, kind, url, open_store(url), variables, own)
        if kind != "truth":
            ds = _mask_unneeded(cfg, url, ds, own)
        _write(ds, path)
        downloads += 1
    elapsed = _time.perf_counter() - start
    log.info("%d downloads", downloads)
    log.info("elapsed_s=%.3f", elapsed)
    return FetchReport(downloads, elapsed, tuple(done))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="regret fetch",
        description="Fetch WeatherBench 2 250 hPa winds into the local cache (idempotent).",
    )
    p.add_argument("--fixture", action="store_true", help="use the fixture config; write tests/fixtures/")
    p.add_argument(
        "--with", dest="extras", default="", metavar="NAME,...",
        help="extra datasets to fetch besides the defaults (e.g. neuralgcm,neuralgcm_ens,geopotential)",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    cfg = get_config("fixture" if args.fixture else None)
    extras = [n for n in args.extras.split(",") if n]
    known = {d.name for d in cfg.datasets}
    unknown = [n for n in extras if n not in known]
    if unknown:
        parser.error(f"unknown dataset(s) {unknown}; expected some of {sorted(known)}")
    names = [d.name for d in cfg.datasets if d.fetch_by_default]
    names += [n for n in extras if n not in names]
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    fetch(cfg, names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
