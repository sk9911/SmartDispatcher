"""Replay a plan's fixed lateral path through the truth wind (SPEC 4.3, CONTRACTS 2.8)."""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from openap import FuelFlow, prop

from regret.types import Flight, Plan, ReplayResult, WindField
from regret.units import (
    AIRCRAFT,
    CO2_PER_FUEL,
    FLIGHT_LEVEL,
    MACH,
    MASS_FRACTION,
    TAS_MS,
    great_circle_km,
    initial_bearing_deg,
    intermediate_point,
    ms_to_knots,
)

STEP_KM = 10.0
_NS_PER_S = 1e9


@lru_cache(maxsize=1)
def _fuel_model() -> FuelFlow:
    return FuelFlow(AIRCRAFT)


def initial_mass_kg() -> float:
    """MASS_FRACTION of the OpenAP B789 maximum take-off mass."""
    return MASS_FRACTION * float(prop.aircraft(AIRCRAFT)["mtow"])


def _path_points(plan: Plan, step_km: float) -> tuple[np.ndarray, np.ndarray]:
    """Points along the plan: each great-circle segment split into equal steps <= step_km."""
    lat = np.asarray(plan.lat_deg, dtype=float)
    lon = np.asarray(plan.lon_deg, dtype=float)
    out_lat, out_lon = [lat[0]], [lon[0]]
    for i in range(len(lat) - 1):
        length = float(great_circle_km(lat[i], lon[i], lat[i + 1], lon[i + 1]))
        n = max(1, math.ceil(length / step_km))
        f = np.arange(1, n + 1) / n
        la, lo = intermediate_point(lat[i], lon[i], lat[i + 1], lon[i + 1], f)
        out_lat.extend(np.atleast_1d(la))
        out_lon.extend(np.atleast_1d(lo))
    return np.array(out_lat), np.array(out_lon)


def replay(
    plan: Plan, flight: Flight, truth: WindField, *, step_km: float = STEP_KM
) -> ReplayResult:
    """Fly ``plan`` at FL350 / M0.85 through ``truth`` from the flight's departure time.

    Per step: wind sampled at the step midpoint at the step's start time, ground speed
    from the wind triangle, fuel flow from OpenAP cruise at the current mass.
    """
    lat, lon = _path_points(plan, step_km)
    n = len(lat)
    dist_km = great_circle_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
    bearing = np.radians(initial_bearing_deg(lat[:-1], lon[:-1], lat[1:], lon[1:]))
    mid_lat, mid_lon = intermediate_point(lat[:-1], lon[:-1], lat[1:], lon[1:], 0.5)

    model = _fuel_model()
    tas_kt = float(ms_to_knots(TAS_MS))
    alt_ft = FLIGHT_LEVEL * 100.0
    t0 = np.datetime64(flight.departure_time, "ns")

    times = np.empty(n, dtype="datetime64[ns]")
    times[0] = t0
    t_s = 0.0
    mass = initial_mass_kg()
    fuel = 0.0
    flows = np.empty(n - 1)
    for i in range(n - 1):
        u, v = truth.uv(mid_lat[i], mid_lon[i], times[i])
        u, v = float(u), float(v)
        s, c = math.sin(bearing[i]), math.cos(bearing[i])
        w_along = u * s + v * c
        w_cross = u * c - v * s
        gs = math.sqrt(TAS_MS**2 - w_cross**2) + w_along
        dt = dist_km[i] * 1000.0 / gs
        ff_kgs = float(model.enroute(mass=mass, tas=tas_kt, alt=alt_ft))
        flows[i] = ff_kgs * 3600.0
        burn = ff_kgs * dt
        fuel += burn
        mass -= burn
        t_s += dt
        times[i + 1] = t0 + np.timedelta64(int(round(t_s * _NS_PER_S)), "ns")

    return ReplayResult(
        flight_id=flight.flight_id,
        source=plan.source,
        lead_h=plan.lead_h,
        lat_deg=lat,
        lon_deg=lon,
        time=times,
        time_min=float((times[-1] - times[0]) / np.timedelta64(1, "m")),
        fuel_kg=fuel,
        co2_kg=CO2_PER_FUEL * fuel,
        fuel_flow_min_kgh=float(flows.min()),
        fuel_flow_max_kgh=float(flows.max()),
    )
