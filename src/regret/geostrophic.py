"""Geostrophic balance check at 250 hPa (SPEC 1.3 item 2, CONTRACTS 2.1).

Is a forecast's wind near jet level balanced the way the real atmosphere is?
The geostrophic wind from geopotential Phi, with the f-plane evaluated at each grid point::

    u_g = -(1/f) dPhi/dy        v_g = (1/f) dPhi/dx        f = 2 Omega sin(lat)

using centred differences on the sphere (dx = R cos(lat) dlon, dy = R dlat).

The **ageostrophic fraction** is |V - V_g| / |V| over 30-70 N, interior grid points only
(centred differences need both neighbours). To avoid dividing by a tiny |V| at any single
point, it is a **ratio of area means**: mean(|V - V_g|) / mean(|V|), each weighted by
cos(lat). A pointwise ratio would be dominated by calm points; this form is a wind-weighted
average of the pointwise ratio instead.
"""
from __future__ import annotations

import logging
import sys
import time
from collections.abc import Sequence
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from regret.config import cache_path, flights, get_config
from regret.types import Config

log = logging.getLogger(__name__)

EARTH_RADIUS_M = 6_371_000.0
OMEGA = 7.292115e-5  # Earth's rotation rate, rad/s
LAT_MIN, LAT_MAX = 30.0, 70.0
RESULT_NAME = "geostrophic.parquet"
COLUMNS = ["source", "lead_h", "ageostrophic_fraction", "n_fields"]
FORECAST_SOURCES = ("hres", "graphcast", "pangu")  # persistence is ERA5 at init: ERA5's balance
REFERENCE = "era5"


def region_mask(lat: np.ndarray) -> np.ndarray:
    """True for latitudes in 30-70 N."""
    lat = np.asarray(lat, dtype=float)
    return (lat >= LAT_MIN) & (lat <= LAT_MAX)


def geostrophic_wind(phi: np.ndarray, lat: np.ndarray, lon: np.ndarray):
    """(u_g, v_g) in m/s from geopotential phi (m2/s2), shape (lat, lon).

    Centred differences; the outermost rows and columns are NaN (no two-sided stencil).
    """
    phi = np.asarray(phi, dtype=np.float64)
    la = np.deg2rad(np.asarray(lat, dtype=np.float64))
    lo = np.deg2rad(np.asarray(lon, dtype=np.float64))
    dphi_dy = np.full_like(phi, np.nan)
    dphi_dx = np.full_like(phi, np.nan)
    dphi_dy[1:-1, :] = (phi[2:, :] - phi[:-2, :]) / (EARTH_RADIUS_M * (la[2:] - la[:-2]))[:, None]
    dx = EARTH_RADIUS_M * np.cos(la)[:, None] * (lo[2:] - lo[:-2])[None, :]
    dphi_dx[:, 1:-1] = (phi[:, 2:] - phi[:, :-2]) / dx
    f = (2.0 * OMEGA * np.sin(la))[:, None]
    return -dphi_dy / f, dphi_dx / f


def ageostrophic_fraction(u, v, phi, lat, lon) -> float:
    """cos(lat)-weighted mean|V - V_g| / mean|V| over interior points at 30-70 N."""
    ug, vg = geostrophic_wind(phi, lat, lon)
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    ok = region_mask(lat)[:, None] & np.isfinite(ug) & np.isfinite(vg)
    w = np.broadcast_to(np.cos(np.deg2rad(np.asarray(lat, dtype=float)))[:, None], u.shape)[ok]
    diff = np.hypot(u - ug, v - vg)[ok]
    speed = np.hypot(u, v)[ok]
    return float(np.sum(w * diff) / np.sum(w * speed))


@lru_cache(maxsize=None)
def _open(path: Path) -> xr.Dataset:
    return xr.open_zarr(path).load()


def _field(cfg: Config, source: str, valid: np.datetime64, lead_h: int):
    """(u, v, phi, lat, lon) at one valid time; None if that forecast pair is absent/NaN."""
    wind = _open(cache_path(cfg, source))
    pot = _open(cache_path(cfg, f"geopotential_{source}"))
    if source == REFERENCE:
        sel = dict(time=valid)
    else:
        sel = dict(time=valid - np.timedelta64(lead_h, "h"), prediction_timedelta=np.timedelta64(lead_h, "h"))
    try:
        w, p = wind.sel(**sel), pot.sel(**sel)
    except KeyError:
        return None
    u, v, phi = (a.transpose("latitude", "longitude").values for a in (
        w["u_component_of_wind"], w["v_component_of_wind"], p["geopotential"]))
    if not (np.isfinite(u).all() and np.isfinite(phi).all()):
        return None
    lat, lon = w["latitude"].values, w["longitude"].values
    if lat[0] > lat[-1]:
        raise ValueError("latitude must be ascending")
    return u, v, phi, lat, lon


def run(cfg: Config) -> pd.DataFrame:
    """Ageostrophic fraction per source and lead, averaged over the experiment's flights.

    Rows for each forecast source use the fields valid at each flight's departure
    (init = departure - lead, step = lead). The ``era5`` rows are ERA5 at the same valid
    times, once per lead, so that every lead has its own reference.
    """
    deps = [np.datetime64(f.departure_time, "ns") for f in flights(cfg)]
    rows = []
    for source in (REFERENCE, *FORECAST_SOURCES):
        for lead in cfg.leads_h:
            vals = []
            for dep in deps:
                fld = _field(cfg, source, dep, lead)
                if fld is not None:
                    vals.append(ageostrophic_fraction(*fld))
            if vals:
                rows.append((source, int(lead), float(np.mean(vals)), len(vals)))
    return pd.DataFrame(rows, columns=COLUMNS)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    cfg = get_config()
    t0 = time.perf_counter()
    df = run(cfg)
    out = cfg.results_path.parent / RESULT_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, engine="pyarrow", index=False)
    log.info("wrote %d rows to %s", len(df), out)
    log.info("elapsed_s=%.1f", time.perf_counter() - t0)
    return 0
