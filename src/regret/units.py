"""Units, ISA atmosphere and great-circle helpers shared by planner and replay.

Conventions (CONTRACTS): degrees for latitude/longitude, m/s for speeds, km for
distances. Geodesy uses a spherical Earth of radius ``EARTH_RADIUS_KM``.
Every function accepts floats or numpy arrays (numpy broadcasting) and returns
the same kind: ``float`` for all-scalar input, ``numpy.ndarray`` otherwise.
"""
from __future__ import annotations

import numpy as np

FLIGHT_LEVEL = 350
PRESSURE_HPA = 250
MACH = 0.85
MASS_FRACTION = 0.85
CO2_PER_FUEL = 3.16
AIRCRAFT = "B789"
EARTH_RADIUS_KM = 6371.0088

_KT_MS = 1852.0 / 3600.0
_FT_M = 0.3048
_T0_K = 288.15
_LAPSE_K_PER_M = 0.0065
_TROPOPAUSE_M = 11000.0
_GAMMA = 1.4
_R_AIR = 287.05287


def _out(x):
    """float for 0-d results, ndarray otherwise."""
    x = np.asarray(x, dtype=np.float64)
    return float(x) if x.ndim == 0 else x


def knots_to_ms(kt):
    """Knots to m/s (1 kt = 1852/3600 m/s)."""
    return _out(np.asarray(kt, dtype=np.float64) * _KT_MS)


def ms_to_knots(ms):
    """m/s to knots."""
    return _out(np.asarray(ms, dtype=np.float64) / _KT_MS)


def flight_level_to_m(flight_level):
    """Geometric altitude in metres of a flight level (FL350 = 35,000 ft)."""
    return _out(np.asarray(flight_level, dtype=np.float64) * 100.0 * _FT_M)


def isa_temperature_k(altitude_m):
    """ISA temperature in K at altitude in m (troposphere lapse, isothermal above 11 km)."""
    h = np.asarray(altitude_m, dtype=np.float64)
    return _out(np.maximum(_T0_K - _LAPSE_K_PER_M * h, _T0_K - _LAPSE_K_PER_M * _TROPOPAUSE_M))


def speed_of_sound_ms(temperature_k):
    """Speed of sound in m/s for air at temperature in K."""
    return _out(np.sqrt(_GAMMA * _R_AIR * np.asarray(temperature_k, dtype=np.float64)))


def _sound_speed_at_fl(flight_level):
    return speed_of_sound_ms(isa_temperature_k(flight_level_to_m(flight_level)))


def mach_to_tas(mach: float, flight_level: int = FLIGHT_LEVEL) -> float:
    """True airspeed in m/s for a Mach number at a flight level (ISA)."""
    return _out(np.asarray(mach, dtype=np.float64) * _sound_speed_at_fl(flight_level))


def tas_to_mach(tas_ms: float, flight_level: int = FLIGHT_LEVEL) -> float:
    """Mach number for a true airspeed in m/s at a flight level (ISA)."""
    return _out(np.asarray(tas_ms, dtype=np.float64) / _sound_speed_at_fl(flight_level))


TAS_MS: float = mach_to_tas(MACH)


def great_circle_km(lat1, lon1, lat2, lon2):
    """Great-circle (haversine) distance in km between points given in degrees.

    Broadcasts over all four arguments; symmetric; 0 for identical points.
    """
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return _out(EARTH_RADIUS_KM * c)


def initial_bearing_deg(lat1, lon1, lat2, lon2):
    """Initial true bearing in degrees [0, 360) from point 1 toward point 2.

    0 = north, 90 = east. Broadcasts over all four arguments.
    """
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlmb = np.radians(lon2) - np.radians(lon1)
    y = np.sin(dlmb) * np.cos(p2)
    x = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dlmb)
    return _out(np.degrees(np.arctan2(y, x)) % 360.0)


def _norm_lon(lon_deg):
    return (np.asarray(lon_deg, dtype=np.float64) + 180.0) % 360.0 - 180.0


def destination_point(lat, lon, bearing_deg, distance_km):
    """Point reached from (lat, lon) travelling distance_km along a great circle.

    Starts on initial bearing ``bearing_deg`` (degrees, 0 = north). Returns
    ``(lat_deg, lon_deg)`` with longitude normalised to [-180, 180). Broadcasts.
    """
    p1, l1 = np.radians(lat), np.radians(lon)
    th = np.radians(bearing_deg)
    delta = np.asarray(distance_km, dtype=np.float64) / EARTH_RADIUS_KM
    sin_p2 = np.sin(p1) * np.cos(delta) + np.cos(p1) * np.sin(delta) * np.cos(th)
    p2 = np.arcsin(np.clip(sin_p2, -1.0, 1.0))
    l2 = l1 + np.arctan2(
        np.sin(th) * np.sin(delta) * np.cos(p1), np.cos(delta) - np.sin(p1) * sin_p2
    )
    return _out(np.degrees(p2)), _out(_norm_lon(np.degrees(l2)))


def intermediate_point(lat1, lon1, lat2, lon2, fraction):
    """Point a ``fraction`` (0 = point 1, 1 = point 2) of the way along the great circle.

    Returns ``(lat_deg, lon_deg)``, longitude in [-180, 180). Broadcasts over all
    arguments. Coincident points return point 1. Antipodal points are undefined.
    """
    p1, l1 = np.radians(lat1), np.radians(lon1)
    p2, l2 = np.radians(lat2), np.radians(lon2)
    delta = great_circle_km(lat1, lon1, lat2, lon2) / EARTH_RADIUS_KM
    sd = np.sin(delta)
    safe = np.where(sd == 0, 1.0, sd)
    f = np.asarray(fraction, dtype=np.float64)
    a = np.where(sd == 0, 1.0 - f, np.sin((1 - f) * delta) / safe)
    b = np.where(sd == 0, f, np.sin(f * delta) / safe)
    x = a * np.cos(p1) * np.cos(l1) + b * np.cos(p2) * np.cos(l2)
    y = a * np.cos(p1) * np.sin(l1) + b * np.cos(p2) * np.sin(l2)
    z = a * np.sin(p1) + b * np.sin(p2)
    lat = np.degrees(np.arctan2(z, np.hypot(x, y)))
    lon = np.degrees(np.arctan2(y, x))
    return _out(lat), _out(_norm_lon(lon))
