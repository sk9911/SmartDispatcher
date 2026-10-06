"""Tests for regret.winds on synthetic grids."""
from __future__ import annotations

import numpy as np

from regret.winds import GridWind

T0 = np.datetime64("2020-02-09T00:00", "ns")
TIMES = T0 + np.arange(3) * np.timedelta64(6, "h")
LAT = np.array([30.0, 40.0, 50.0, 60.0])
LON = np.array([-60.0, -40.0, -20.0, 0.0])


def linear_u(lat, lon, hours):
    return 1.0 + 0.3 * lat - 0.2 * lon + 0.5 * hours


def linear_v(lat, lon, hours):
    return -2.0 - 0.1 * lat + 0.4 * lon + 0.25 * hours


def cube(fn, lat=LAT, lon=LON):
    h = np.arange(3) * 6.0
    return fn(lat[None, :, None], lon[None, None, :], h[:, None, None]) * np.ones(
        (3, len(lat), len(lon))
    )


def test_linear_field_is_interpolated_exactly_in_lat_lon_and_time():
    gw = GridWind(cube(linear_u), cube(linear_v), LAT, LON, TIMES)
    lat = np.array([33.3, 47.1, 59.9])
    lon = np.array([-55.5, -21.0, -0.5])
    hours = np.array([1.7, 6.0, 11.3])
    time = T0 + (hours * 3600e9).astype("timedelta64[ns]")
    u, v = gw.uv(lat, lon, time)
    np.testing.assert_allclose(u, linear_u(lat, lon, hours), atol=1e-9)
    np.testing.assert_allclose(v, linear_v(lat, lon, hours), atol=1e-9)


def test_uniform_eastward_u_returns_plus_ten_toward_the_east():
    shape = (3, len(LAT), len(LON))
    gw = GridWind(np.full(shape, 10.0), np.zeros(shape), LAT, LON, TIMES)
    u, v = gw.uv(45.0, -30.0, T0 + np.timedelta64(3, "h"))
    assert u.shape == () and float(u) == 10.0 and float(v) == 0.0


def test_points_outside_the_grid_raise_value_error():
    import pytest

    gw = GridWind(cube(linear_u), cube(linear_v), LAT, LON, TIMES)
    t = T0 + np.timedelta64(1, "h")
    for lat, lon, time in [
        (29.9, -30.0, t),
        (60.1, -30.0, t),
        (45.0, -60.1, t),
        (45.0, 0.1, t),
        (45.0, -30.0, T0 - np.timedelta64(1, "h")),
        (45.0, -30.0, TIMES[-1] + np.timedelta64(1, "h")),
    ]:
        with pytest.raises(ValueError):
            gw.uv(lat, lon, time)


def make_ds(lat, lon):
    import xarray as xr

    u = cube(linear_u, lat, lon)
    v = cube(linear_v, lat, lon)
    return xr.Dataset(
        {
            "u_component_of_wind": (("time", "latitude", "longitude"), u),
            "v_component_of_wind": (("time", "latitude", "longitude"), v),
        },
        coords={"time": TIMES, "latitude": lat, "longitude": lon},
    )


POINTS = (
    np.array([33.3, 47.1, 59.9]),
    np.array([-55.5, -21.0, -0.5]),
    T0 + np.array([1.7, 6.0, 11.3]) * np.timedelta64(3600, "s"),
)


def test_north_to_south_and_south_to_north_input_give_identical_values():
    from regret.winds import from_dataset

    south_up = from_dataset(make_ds(LAT, LON)).uv(*POINTS)
    north_up = from_dataset(make_ds(LAT[::-1], LON)).uv(*POINTS)
    np.testing.assert_array_equal(south_up[0], north_up[0])
    np.testing.assert_array_equal(south_up[1], north_up[1])
    np.testing.assert_allclose(south_up[0], linear_u(POINTS[0], POINTS[1], np.array([1.7, 6.0, 11.3])), atol=1e-9)


def test_zero_to_360_and_minus_180_to_180_input_give_identical_values():
    from regret.winds import from_dataset

    # Same physical longitudes; field values depend on the -180..180 value.
    lon360 = np.where(LON < 0, LON + 360.0, LON)
    ds360 = make_ds(LAT, LON).assign_coords(longitude=lon360)  # 300, 320, 340, 0
    a = from_dataset(make_ds(LAT, LON)).uv(*POINTS)
    b = from_dataset(ds360).uv(*POINTS)
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])


def test_normalise_sorts_latitude_ascending_and_wraps_longitude():
    from regret.winds import normalise

    lon360 = np.array([300.0, 320.0, 340.0, 0.0])
    out = normalise(make_ds(LAT[::-1], LON).assign_coords(longitude=lon360))
    np.testing.assert_array_equal(out["latitude"].values, LAT)
    np.testing.assert_array_equal(out["longitude"].values, LON)
    np.testing.assert_allclose(
        out["u_component_of_wind"].values, cube(linear_u), atol=1e-12
    )


def test_from_dataset_time_override_sets_the_valid_time_axis():
    import xarray as xr
    from regret.winds import from_dataset

    shifted = xr.DataArray(TIMES + np.timedelta64(12, "h"), dims="time")
    gw = from_dataset(make_ds(LAT, LON), time=shifted)
    u, _ = gw.uv(45.0, -30.0, TIMES[0] + np.timedelta64(12, "h"))
    np.testing.assert_allclose(u, linear_u(45.0, -30.0, 0.0), atol=1e-9)


def uniform(u_ms, v_ms):
    shape = (3, len(LAT), len(LON))
    return GridWind(np.full(shape, u_ms), np.full(shape, v_ms), LAT, LON, TIMES)


def test_uniform_wind_returns_constant_everywhere_in_the_broadcast_shape():
    from regret.winds import UniformWind

    u, v = UniformWind(3.0, -4.0).uv(np.array([[1.0], [2.0]]), np.array([5.0, 6.0, 7.0]), T0)
    assert u.shape == v.shape == (2, 3)
    assert (u == 3.0).all() and (v == -4.0).all()


def test_offset_wind_adds_the_offset_to_the_base():
    from regret.winds import OffsetWind

    w = OffsetWind(uniform(10.0, 2.0), du_ms=1.5, dv_ms=-0.5)
    u, v = w.uv(np.array([40.0, 50.0]), np.array([-30.0, -20.0]), T0 + np.timedelta64(2, "h"))
    np.testing.assert_allclose(u, [11.5, 11.5])
    np.testing.assert_allclose(v, [1.5, 1.5])
    assert u.dtype == np.float64


def test_frozen_wind_samples_base_at_the_fixed_time_for_every_time():
    from regret.winds import FrozenWind

    gw = GridWind(cube(linear_u), cube(linear_v), LAT, LON, TIMES)
    at = T0 + np.timedelta64(6, "h")
    fw = FrozenWind(gw, at)
    # a query time far outside the base's range is fine: base is only sampled at `at`
    times = T0 + np.array([0, 100, 1000]) * np.timedelta64(1, "h")
    u, v = fw.uv(np.array([40.0] * 3), np.array([-30.0] * 3), times)
    ue, ve = gw.uv(40.0, -30.0, at)
    np.testing.assert_allclose(u, [float(ue)] * 3)
    np.testing.assert_allclose(v, [float(ve)] * 3)


def test_ten_thousand_points_are_interpolated_well_under_a_tenth_of_a_second():
    import time as clock

    gw = GridWind(cube(linear_u), cube(linear_v), LAT, LON, TIMES)
    rng = np.random.default_rng(0)
    lat = rng.uniform(30, 60, 10_000)
    lon = rng.uniform(-60, 0, 10_000)
    t = T0 + (rng.uniform(0, 12, 10_000) * 3600e9).astype("timedelta64[ns]")
    gw.uv(lat, lon, t)
    start = clock.perf_counter()
    gw.uv(lat, lon, t)
    assert clock.perf_counter() - start < 0.1
