"""Tests for regret.replay (CONTRACTS 2.8, SPEC 4.3) on synthetic winds."""
from __future__ import annotations

from datetime import datetime

import numpy as np

from regret.replay import STEP_KM, replay
from regret.types import JFK, LHR, Plan, make_flight
from regret.units import great_circle_km, intermediate_point
from regret.winds import UniformWind

DEP = datetime(2020, 2, 9, 0, 0)
FLIGHT = make_flight(JFK, LHR, DEP)
ZERO = UniformWind(0.0, 0.0)


def gc_plan(scale: float = 1.0, source: str = "truth", lead_h: int = 0) -> Plan:
    """25-waypoint great circle; scale > 1 pushes the middle off the great circle (longer)."""
    f = np.linspace(0.0, 1.0, 25)
    lat, lon = intermediate_point(JFK.lat_deg, JFK.lon_deg, LHR.lat_deg, LHR.lon_deg, f)
    lat = np.asarray(lat) + (scale - 1.0) * 60.0 * np.sin(np.pi * f)
    return Plan(FLIGHT.flight_id, source, lead_h, tuple(lat), tuple(np.asarray(lon)), 0.0)


def test_zero_wind_great_circle_fuel_flow_is_realistic_for_a_b789():
    r = replay(gc_plan(), FLIGHT, ZERO)
    assert 4000 <= r.fuel_flow_min_kgh <= r.fuel_flow_max_kgh <= 8000
    assert 25_000 < r.fuel_kg < 50_000


def test_co2_is_exactly_3_16_times_fuel_and_result_carries_plan_identity():
    r = replay(gc_plan(source="hres", lead_h=48), FLIGHT, ZERO)
    assert r.co2_kg == 3.16 * r.fuel_kg
    assert (r.flight_id, r.source, r.lead_h) == (FLIGHT.flight_id, "hres", 48)


def test_two_runs_are_identical():
    a = replay(gc_plan(), FLIGHT, UniformWind(15.0, -5.0))
    b = replay(gc_plan(), FLIGHT, UniformWind(15.0, -5.0))
    assert (a.fuel_kg, a.time_min) == (b.fuel_kg, b.time_min)
    np.testing.assert_array_equal(a.time, b.time)
    np.testing.assert_array_equal(a.lat_deg, b.lat_deg)


def test_a_longer_path_burns_more_fuel_and_takes_longer():
    base = replay(gc_plan(), FLIGHT, ZERO)
    longer = replay(gc_plan(scale=2.0), FLIGHT, ZERO)
    assert longer.fuel_kg > base.fuel_kg
    assert longer.time_min > base.time_min


def test_points_are_at_most_one_step_apart_and_time_starts_at_departure():
    r = replay(gc_plan(), FLIGHT, ZERO)
    gaps = great_circle_km(r.lat_deg[:-1], r.lon_deg[:-1], r.lat_deg[1:], r.lon_deg[1:])
    assert gaps.max() <= STEP_KM + 1e-6
    assert len(r.lat_deg) == len(r.lon_deg) == len(r.time) > 500
    assert r.time[0] == np.datetime64(DEP, "ns")
    assert (r.lat_deg[0], r.lon_deg[0]) == (JFK.lat_deg, JFK.lon_deg)
    assert np.all(np.diff(r.time.astype("int64")) > 0)
    assert r.time_min == (r.time[-1] - r.time[0]) / np.timedelta64(1, "m")


def test_tailwind_is_faster_and_cheaper_headwind_the_opposite():
    # JFK->LHR is eastbound: +u is a tailwind.
    calm = replay(gc_plan(), FLIGHT, ZERO)
    tail = replay(gc_plan(), FLIGHT, UniformWind(25.0, 0.0))
    head = replay(gc_plan(), FLIGHT, UniformWind(-25.0, 0.0))
    assert tail.time_min < calm.time_min < head.time_min
    assert tail.fuel_kg < calm.fuel_kg < head.fuel_kg


def test_zero_wind_time_matches_distance_over_true_airspeed():
    r = replay(gc_plan(), FLIGHT, ZERO)
    gc = float(great_circle_km(JFK.lat_deg, JFK.lon_deg, LHR.lat_deg, LHR.lon_deg))
    tas_ms = 0.85 * 296.5  # speed of sound at FL350 ISA (~296.5 m/s), independent literal
    assert abs(r.time_min - gc * 1000 / tas_ms / 60) < 3.0
