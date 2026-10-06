"""Minimum-time grid planner (CONTRACTS 2.7, SPEC 4.2, ADR 0001).

Lateral grid aligned with the great circle: ``N_COLUMNS`` columns along track,
``N_OFFSETS`` cross-track offsets spaced ``OFFSET_SPACING_KM`` apart. Offset
index ``N_OFFSETS // 2`` lies on the great circle; positive offsets are to the
right of the direction of travel. The first and last columns collapse to the
airports. Dynamic programming keeps the earliest arrival at every node.
"""
from __future__ import annotations

import numpy as np

from .types import Flight, Plan, SourceName, WindField
from .units import (
    TAS_MS,
    destination_point,
    great_circle_km,
    initial_bearing_deg,
    intermediate_point,
)

N_COLUMNS = 25
N_OFFSETS = 41
OFFSET_SPACING_KM = 60.0
MAX_SHIFT = 3

_CENTRE = N_OFFSETS // 2
_SHIFTS = np.arange(-MAX_SHIFT, MAX_SHIFT + 1)


def great_circle_path(flight: Flight, n: int = N_COLUMNS) -> tuple[np.ndarray, np.ndarray]:
    """``n`` points evenly spaced along the great circle, origin to destination."""
    f = np.linspace(0.0, 1.0, n)
    lat, lon = intermediate_point(
        flight.origin.lat_deg, flight.origin.lon_deg,
        flight.destination.lat_deg, flight.destination.lon_deg, f,
    )
    lat, lon = np.array(lat), np.array(lon)
    lat[0], lon[0] = flight.origin.lat_deg, flight.origin.lon_deg
    return lat, lon


def build_grid(flight: Flight) -> tuple[np.ndarray, np.ndarray]:
    """Node latitudes and longitudes, each ``(N_COLUMNS, N_OFFSETS)``."""
    clat, clon = great_circle_path(flight)
    # track bearing at each column; the last column looks back from the destination
    brg = np.empty(N_COLUMNS)
    brg[:-1] = initial_bearing_deg(clat[:-1], clon[:-1], clat[1:], clon[1:])
    brg[-1] = (initial_bearing_deg(clat[-1], clon[-1], clat[-2], clon[-2]) + 180.0) % 360.0
    off_km = (np.arange(N_OFFSETS) - _CENTRE) * OFFSET_SPACING_KM
    lat, lon = destination_point(
        clat[:, None], clon[:, None], (brg[:, None] + 90.0) % 360.0, off_km[None, :]
    )
    lat, lon = np.array(lat), np.array(lon)
    lat[0], lon[0] = flight.origin.lat_deg, flight.origin.lon_deg
    lat[-1], lon[-1] = flight.destination.lat_deg, flight.destination.lon_deg
    return lat, lon


def _edge_times_s(wind, lat0, lon0, lat1, lon1, t0_s, t_ref):
    """Edge times (s) for from/to node arrays of one shape.

    Ground speed from the wind triangle at the segment midpoint, sampled at the
    estimated passing time (two passes: still-air estimate, then refined).
    """
    dist_m = great_circle_km(lat0, lon0, lat1, lon1) * 1000.0
    mlat, mlon = intermediate_point(lat0, lon0, lat1, lon1, 0.5)
    brg = np.radians(initial_bearing_deg(mlat, mlon, lat1, lon1))
    sb, cb = np.sin(brg), np.cos(brg)
    dt = dist_m / TAS_MS
    for _ in range(2):
        t_mid = t_ref + ((t0_s + 0.5 * dt) * 1e9).astype("timedelta64[ns]")
        u, v = wind.uv(mlat, mlon, t_mid)
        along = u * sb + v * cb
        cross = u * cb - v * sb
        gs = np.sqrt(np.maximum(TAS_MS**2 - cross**2, 1.0)) + along
        dt = dist_m / np.maximum(gs, 1.0)
    return dt


def plan(wind: WindField, flight: Flight, *, source: SourceName, lead_h: int) -> Plan:
    lat, lon = build_grid(flight)
    t_ref = np.datetime64(flight.departure_time, "ns")
    ncol = N_COLUMNS
    abs_off = np.abs(np.arange(N_OFFSETS) - _CENTRE)

    arr = np.full(N_OFFSETS, np.inf)           # earliest arrival (s since departure)
    arr[_CENTRE] = 0.0
    back = np.zeros((ncol, N_OFFSETS), dtype=np.intp)

    to_idx = np.arange(N_OFFSETS)[:, None]
    from_idx = to_idx + _SHIFTS[None, :]       # (to, shift) -> from offset
    valid = (from_idx >= 0) & (from_idx < N_OFFSETS)
    from_c = np.clip(from_idx, 0, N_OFFSETS - 1)

    for c in range(ncol - 1):
        t_from = arr[from_c]
        reachable = valid & np.isfinite(t_from)
        t0 = np.where(reachable, t_from, 0.0)
        dt = _edge_times_s(
            wind,
            lat[c][from_c], lon[c][from_c],
            np.broadcast_to(lat[c + 1][:, None], from_c.shape),
            np.broadcast_to(lon[c + 1][:, None], from_c.shape),
            t0, t_ref,
        )
        cand = np.where(reachable, t0 + dt, np.inf)
        best = cand.min(axis=1)
        # tie rule: among equal arrivals take the from-node with smallest |offset|
        tie_cost = np.where(cand == best[:, None], abs_off[from_c], N_OFFSETS)
        pick = tie_cost.argmin(axis=1)
        back[c + 1] = from_c[np.arange(N_OFFSETS), pick]
        arr = best

    # last column is a single point: take the smallest |offset| node among ties
    best = arr.min()
    node = int(np.where(arr == best, abs_off, N_OFFSETS).argmin())
    path = np.empty(ncol, dtype=np.intp)
    for c in range(ncol - 1, -1, -1):
        path[c] = node
        node = back[c, node]
    cols = np.arange(ncol)
    return Plan(
        flight_id=flight.flight_id,
        source=source,
        lead_h=lead_h,
        lat_deg=tuple(float(x) for x in lat[cols, path]),
        lon_deg=tuple(float(x) for x in lon[cols, path]),
        planned_time_min=float(best) / 60.0,
    )
