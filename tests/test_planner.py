"""Grid planner (CONTRACTS 2.7, SPEC 4.2, 6.2)."""
from __future__ import annotations

import time
from datetime import datetime

import numpy as np

from regret import planner
from regret.planner import N_COLUMNS, N_OFFSETS, OFFSET_SPACING_KM, MAX_SHIFT
from regret.types import JFK, LHR, TRUTH_LEAD_H, TRUTH_SOURCE, make_flight
from regret.units import TAS_MS, great_circle_km
from regret.winds import GridWind, UniformWind

DEP = datetime(2020, 2, 9, 0, 0)
EAST = make_flight(JFK, LHR, DEP)
WEST = make_flight(LHR, JFK, DEP)
CENTRE = N_OFFSETS // 2


def _xtrack_km(lat, lon, flight):
    """Distance of points from the great circle through the airports (km)."""
    from regret.units import EARTH_RADIUS_KM, initial_bearing_deg

    d13 = great_circle_km(flight.origin.lat_deg, flight.origin.lon_deg, lat, lon) / EARTH_RADIUS_KM
    t13 = np.radians(initial_bearing_deg(flight.origin.lat_deg, flight.origin.lon_deg, lat, lon))
    t12 = np.radians(
        initial_bearing_deg(flight.origin.lat_deg, flight.origin.lon_deg,
                            flight.destination.lat_deg, flight.destination.lon_deg)
    )
    return np.abs(np.arcsin(np.sin(d13) * np.sin(t13 - t12))) * EARTH_RADIUS_KM


def _gc_km(flight):
    return float(great_circle_km(flight.origin.lat_deg, flight.origin.lon_deg,
                                 flight.destination.lat_deg, flight.destination.lon_deg))


def test_great_circle_path_endpoints():
    lat, lon = planner.great_circle_path(EAST)
    assert lat.shape == lon.shape == (N_COLUMNS,)
    assert (lat[0], lon[0]) == (JFK.lat_deg, JFK.lon_deg)
    assert np.allclose((lat[-1], lon[-1]), (LHR.lat_deg, LHR.lon_deg))


def test_zero_wind_follows_great_circle():
    for flight in (EAST, WEST):
        p = planner.plan(UniformWind(0, 0), flight, source="hres", lead_h=24)
        assert (p.source, p.lead_h, p.flight_id) == ("hres", 24, flight.flight_id)
        assert len(p.lat_deg) == len(p.lon_deg) == N_COLUMNS
        xt = _xtrack_km(np.array(p.lat_deg), np.array(p.lon_deg), flight)
        assert xt.max() <= OFFSET_SPACING_KM
        expected = _gc_km(flight) * 1000 / TAS_MS / 60
        assert abs(p.planned_time_min - expected) / expected < 0.01


def test_truth_source_label():
    p = planner.plan(UniformWind(0, 0), EAST, source=TRUTH_SOURCE, lead_h=TRUTH_LEAD_H)
    assert (p.source, p.lead_h) == ("truth", 0)


def test_uniform_westerly_ordering():
    still = planner.plan(UniformWind(0, 0), EAST, source="s", lead_h=0).planned_time_min
    east = planner.plan(UniformWind(50, 0), EAST, source="s", lead_h=0).planned_time_min
    west = planner.plan(UniformWind(50, 0), WEST, source="s", lead_h=0).planned_time_min
    assert east < still < west


def test_deterministic():
    wind = _synthetic_grid_wind()
    a = planner.plan(wind, EAST, source="s", lead_h=0)
    b = planner.plan(wind, EAST, source="s", lead_h=0)
    assert a == b


def test_grid_shape_spacing_and_shifts():
    lat, lon = planner.build_grid(EAST)
    assert lat.shape == lon.shape == (N_COLUMNS, N_OFFSETS) == (25, 41)
    assert (OFFSET_SPACING_KM, MAX_SHIFT) == (60.0, 3)
    # first and last columns collapse to the airports
    assert np.all(lat[0] == JFK.lat_deg) and np.all(lon[0] == JFK.lon_deg)
    assert np.allclose(lat[-1], LHR.lat_deg) and np.allclose(lon[-1], LHR.lon_deg)
    # interior columns: 60 km between neighbouring offsets, centred on the great circle
    gcl, gcn = planner.great_circle_path(EAST)
    for c in range(1, N_COLUMNS - 1):
        step = great_circle_km(lat[c, :-1], lon[c, :-1], lat[c, 1:], lon[c, 1:])
        assert np.allclose(step, OFFSET_SPACING_KM, rtol=1e-3)
        assert np.allclose((lat[c, CENTRE], lon[c, CENTRE]), (gcl[c], gcn[c]), atol=1e-6)
    # a plan only ever moves <= 3 offsets between columns, onto grid nodes
    wind = UniformWind(40, 25)
    for flight in (EAST, WEST):
        lat, lon = planner.build_grid(flight)
        p = planner.plan(wind, flight, source="s", lead_h=0)
        idx = []
        for c in range(N_COLUMNS):
            d = great_circle_km(p.lat_deg[c], p.lon_deg[c], lat[c], lon[c])
            idx.append(CENTRE if c in (0, N_COLUMNS - 1) else int(np.argmin(d)))
            assert d.min() < 1e-3
        assert np.abs(np.diff(idx)).max() <= MAX_SHIFT


def _synthetic_grid_wind(jet=None):
    lat = np.arange(25.0, 75.01, 1.5)
    lon = np.arange(-100.0, 20.01, 1.5)
    times = np.datetime64("2020-02-09T00:00") + np.arange(5) * np.timedelta64(6, "h")
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    if jet is None:
        u = 20 + 15 * np.sin(np.radians(la * 6)) * np.cos(np.radians(lo * 4))
        v = 8 * np.cos(np.radians(la * 5 + lo * 3))
    else:
        u = jet * np.exp(-(((la - 58.0) / 4.0) ** 2))
        v = np.zeros_like(la)
    u = np.broadcast_to(u, (5, *la.shape)).copy()
    v = np.broadcast_to(v, (5, *la.shape)).copy()
    return GridWind(u, v, lat, lon, times)


def test_jet_attracts_eastbound_and_repels_westbound():
    wind = _synthetic_grid_wind(jet=60.0)
    gcl, _ = planner.great_circle_path(EAST)
    east = planner.plan(wind, EAST, source="s", lead_h=0)
    west = planner.plan(wind, WEST, source="s", lead_h=0)
    assert np.mean(east.lat_deg) - gcl.mean() > 1.0       # bends north toward the jet
    assert np.mean(west.lat_deg) - gcl.mean() < 0.2       # does not climb into the jet
    assert np.max(west.lat_deg) < np.max(east.lat_deg)
    still = planner.plan(UniformWind(0, 0), EAST, source="s", lead_h=0).planned_time_min
    assert east.planned_time_min < still


def test_plan_time_under_one_second():
    wind = _synthetic_grid_wind()
    planner.plan(wind, EAST, source="s", lead_h=0)  # warm-up (imports, caches)
    t0 = time.perf_counter()
    n = 3
    for _ in range(n):
        planner.plan(wind, EAST, source="s", lead_h=0)
    per_plan = (time.perf_counter() - t0) / n
    print(f"seconds per plan: {per_plan:.3f}")
    assert per_plan <= 1.0
