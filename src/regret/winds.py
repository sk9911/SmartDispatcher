"""Wind fields: gridded interpolation and simple wrappers (CONTRACTS 2.4).

Wind sign: u > 0 blows toward the east, v > 0 toward the north (m/s).
"""
from __future__ import annotations

import numpy as np
import xarray as xr
from numpy.typing import ArrayLike


def _axis_weights(axis: np.ndarray, x: np.ndarray, name: str):
    """Lower index and fractional weight of x within a strictly ascending axis."""
    if x.size and (np.nanmin(x) < axis[0] or np.nanmax(x) > axis[-1] or np.isnan(x).any()):
        raise ValueError(f"{name} outside the grid's coverage [{axis[0]}, {axis[-1]}]")
    if len(axis) == 1:
        return np.zeros(x.shape, dtype=np.intp), np.zeros(x.shape)
    i = np.clip(np.searchsorted(axis, x, side="right") - 1, 0, len(axis) - 2)
    frac = (x - axis[i]) / (axis[i + 1] - axis[i])
    return i, frac


class GridWind:
    """Wind on a regular (time, lat, lon) grid: bilinear in space, linear in time."""

    def __init__(self, u, v, lat, lon, time):
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        time = np.asarray(time).astype("datetime64[ns]")
        u = np.asarray(u, dtype=np.float64)
        v = np.asarray(v, dtype=np.float64)
        if u.shape != v.shape or u.shape != (len(time), len(lat), len(lon)):
            raise ValueError("u and v must both have shape (time, lat, lon)")
        lon = np.where(lon > 180.0, lon - 360.0, lon)
        lat_order = np.argsort(lat, kind="stable")
        lon_order = np.argsort(lon, kind="stable")
        time_order = np.argsort(time, kind="stable")
        self._lat = lat[lat_order]
        self._lon = lon[lon_order]
        self._time = time[time_order]
        self._t_h = (self._time - self._time[0]) / np.timedelta64(1, "h")
        self._u = u[np.ix_(time_order, lat_order, lon_order)]
        self._v = v[np.ix_(time_order, lat_order, lon_order)]

    def uv(self, lat: ArrayLike, lon: ArrayLike, time: ArrayLike):
        lat, lon, time = _broadcast(lat, lon, time)
        shape = lat.shape
        lat, lon = lat.ravel(), lon.ravel()
        hours = ((time.ravel() - self._time[0]) / np.timedelta64(1, "h")).astype(np.float64)
        i, fy = _axis_weights(self._lat, lat, "latitude")
        j, fx = _axis_weights(self._lon, lon, "longitude")
        k, ft = _axis_weights(self._t_h, hours, "time")
        i1 = np.minimum(i + 1, len(self._lat) - 1)
        j1 = np.minimum(j + 1, len(self._lon) - 1)
        k1 = np.minimum(k + 1, len(self._t_h) - 1)

        def sample(a):
            def plane(kk):
                return (
                    a[kk, i, j] * (1 - fy) * (1 - fx)
                    + a[kk, i, j1] * (1 - fy) * fx
                    + a[kk, i1, j] * fy * (1 - fx)
                    + a[kk, i1, j1] * fy * fx
                )

            return (plane(k) * (1 - ft) + plane(k1) * ft).reshape(shape)

        return sample(self._u), sample(self._v)


def _broadcast(lat, lon, time):
    return np.broadcast_arrays(
        np.asarray(lat, dtype=np.float64),
        np.asarray(lon, dtype=np.float64),
        np.asarray(time).astype("datetime64[ns]"),
    )


class UniformWind:
    """Constant wind everywhere and always (for tests)."""

    def __init__(self, u_ms: float, v_ms: float):
        self._u = float(u_ms)
        self._v = float(v_ms)

    def uv(self, lat: ArrayLike, lon: ArrayLike, time: ArrayLike):
        lat, _, _ = _broadcast(lat, lon, time)
        return np.full(lat.shape, self._u), np.full(lat.shape, self._v)


class OffsetWind:
    """A base wind plus a constant (du, dv) offset."""

    def __init__(self, base, du_ms: float, dv_ms: float):
        self._base = base
        self._du = float(du_ms)
        self._dv = float(dv_ms)

    def uv(self, lat: ArrayLike, lon: ArrayLike, time: ArrayLike):
        u, v = self._base.uv(lat, lon, time)
        return np.asarray(u, dtype=np.float64) + self._du, np.asarray(v, dtype=np.float64) + self._dv


class FrozenWind:
    """A base wind sampled at the fixed time ``at`` for every query time."""

    def __init__(self, base, at):
        self._base = base
        self._at = np.datetime64(at, "ns")

    def uv(self, lat: ArrayLike, lon: ArrayLike, time: ArrayLike):
        lat, lon, time = _broadcast(lat, lon, time)
        return self._base.uv(lat, lon, np.full(lat.shape, self._at))


def normalise(ds: xr.Dataset) -> xr.Dataset:
    """Latitude ascending, longitude wrapped to -180..180 and sorted."""
    lon = ds["longitude"].values
    ds = ds.assign_coords(longitude=np.where(lon > 180.0, lon - 360.0, lon))
    return ds.sortby(["latitude", "longitude"])


def from_dataset(ds: xr.Dataset, *, time: xr.DataArray | None = None) -> GridWind:
    """GridWind from a dataset with u/v_component_of_wind (time, latitude, longitude).

    ``time`` overrides the time axis (forecast valid time = init + lead).
    """
    ds = normalise(ds)
    times = ds["time"].values if time is None else np.asarray(time.values)
    dims = ("time", "latitude", "longitude")
    return GridWind(
        ds["u_component_of_wind"].transpose(*dims).values,
        ds["v_component_of_wind"].transpose(*dims).values,
        ds["latitude"].values,
        ds["longitude"].values,
        times,
    )
