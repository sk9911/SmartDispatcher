from __future__ import annotations

import numpy as np
import pytest

from regret import units

JFK = (40.6413, -73.7781)
LHR = (51.4700, -0.4543)


def test_knots_ms_round_trip():
    for kt in (0.0, 1.0, 250.0, -40.0):
        assert units.ms_to_knots(units.knots_to_ms(kt)) == pytest.approx(kt, abs=1e-9)
    assert units.knots_to_ms(1.0) == pytest.approx(1852 / 3600, abs=1e-12)
    arr = np.array([10.0, 100.0])
    assert np.allclose(units.ms_to_knots(units.knots_to_ms(arr)), arr, atol=1e-9)


def test_mach_tas_round_trip():
    for m in (0.5, 0.78, 0.85, 0.9):
        assert units.tas_to_mach(units.mach_to_tas(m)) == pytest.approx(m, abs=1e-9)
    assert units.tas_to_mach(units.mach_to_tas(0.8, 300), 300) == pytest.approx(0.8, abs=1e-9)


def test_tas_at_m085_fl350():
    assert units.mach_to_tas(0.85, 350) == pytest.approx(252.0, abs=1.0)
    assert units.TAS_MS == units.mach_to_tas(units.MACH)


def test_constants():
    assert (units.FLIGHT_LEVEL, units.PRESSURE_HPA, units.MACH) == (350, 250, 0.85)
    assert units.MASS_FRACTION == 0.85 and units.CO2_PER_FUEL == 3.16
    assert units.AIRCRAFT == "B789" and units.EARTH_RADIUS_KM == 6371.0088


def test_isa_temperature():
    assert units.isa_temperature_k(0.0) == pytest.approx(288.15)
    assert units.isa_temperature_k(11000.0) == pytest.approx(216.65)
    assert units.isa_temperature_k(15000.0) == pytest.approx(216.65)  # isothermal
    assert units.speed_of_sound_ms(216.65) == pytest.approx(295.04, abs=0.05)


def test_fl_to_altitude():
    assert units.flight_level_to_m(350) == pytest.approx(10668.0)


def test_great_circle_jfk_lhr():
    d = units.great_circle_km(*JFK, *LHR)
    assert d == pytest.approx(5540.0, rel=0.005)
    assert units.great_circle_km(*JFK, *JFK) == pytest.approx(0.0, abs=1e-9)
    assert units.great_circle_km(*LHR, *JFK) == pytest.approx(d)


def test_great_circle_known_quarter():
    assert units.great_circle_km(0, 0, 0, 90) == pytest.approx(units.EARTH_RADIUS_KM * np.pi / 2)
    assert units.great_circle_km(0, 179, 0, -179) == pytest.approx(
        units.EARTH_RADIUS_KM * np.radians(2)
    )


def test_great_circle_vectorised():
    d = units.great_circle_km(np.array([0.0, 0.0]), 0.0, 0.0, np.array([90.0, 180.0]))
    assert d.shape == (2,)
    assert d[1] == pytest.approx(np.pi * units.EARTH_RADIUS_KM)
    assert isinstance(units.great_circle_km(*JFK, *LHR), float)


def test_bearing_cardinals():
    assert units.initial_bearing_deg(0, 0, 10, 0) == pytest.approx(0.0, abs=1e-9)
    assert units.initial_bearing_deg(0, 0, 0, 10) == pytest.approx(90.0)
    assert units.initial_bearing_deg(0, 0, -10, 0) == pytest.approx(180.0)
    assert units.initial_bearing_deg(0, 0, 0, -10) == pytest.approx(270.0)


def test_bearing_jfk_lhr():
    b = units.initial_bearing_deg(*JFK, *LHR)
    assert b == pytest.approx(51.2, abs=0.5)  # known: ~51 deg
    assert 0 <= b < 360


def test_destination_round_trip():
    b = units.initial_bearing_deg(*JFK, *LHR)
    d = units.great_circle_km(*JFK, *LHR)
    lat, lon = units.destination_point(*JFK, b, d)
    assert lat == pytest.approx(LHR[0], abs=1e-6)
    assert lon == pytest.approx(LHR[1], abs=1e-6)
    lat0, lon0 = units.destination_point(10.0, 20.0, 33.0, 0.0)
    assert (lat0, lon0) == (pytest.approx(10.0), pytest.approx(20.0))


def test_destination_wraps_longitude():
    lat, lon = units.destination_point(0.0, 179.0, 90.0, 2 * 111.195)
    assert -180 <= lon <= 180
    assert lon == pytest.approx(-179.0, abs=0.01)


def test_destination_vectorised():
    lat, lon = units.destination_point(0.0, 0.0, np.array([0.0, 90.0]), 111.195)
    assert lat.shape == lon.shape == (2,)
    assert lat[0] == pytest.approx(1.0, abs=1e-3) and lon[1] == pytest.approx(1.0, abs=1e-3)


def test_intermediate_points_on_great_circle():
    total = units.great_circle_km(*JFK, *LHR)
    for f in (0.0, 0.25, 0.5, 0.9, 1.0):
        lat, lon = units.intermediate_point(*JFK, *LHR, f)
        assert units.great_circle_km(*JFK, lat, lon) == pytest.approx(f * total, abs=1e-6)
        assert units.great_circle_km(lat, lon, *LHR) == pytest.approx((1 - f) * total, abs=1e-6)
    # fraction arrays
    lat, lon = units.intermediate_point(*JFK, *LHR, np.linspace(0, 1, 25))
    assert lat.shape == (25,)
    assert lat[0] == pytest.approx(JFK[0]) and lon[-1] == pytest.approx(LHR[1])


def test_intermediate_matches_destination_point():
    b = units.initial_bearing_deg(*JFK, *LHR)
    total = units.great_circle_km(*JFK, *LHR)
    la, lo = units.intermediate_point(*JFK, *LHR, 0.4)
    la2, lo2 = units.destination_point(*JFK, b, 0.4 * total)
    assert (la, lo) == (pytest.approx(la2, abs=1e-6), pytest.approx(lo2, abs=1e-6))


def test_intermediate_coincident_points():
    lat, lon = units.intermediate_point(10.0, 20.0, 10.0, 20.0, 0.5)
    assert (lat, lon) == (pytest.approx(10.0), pytest.approx(20.0))
