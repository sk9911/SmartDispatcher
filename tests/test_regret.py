from __future__ import annotations

from datetime import datetime

import numpy as np

from regret.regret import select_hindsight
from regret.types import JFK, LHR, ReplayResult, make_flight

ORDER = ("hres", "graphcast", "pangu", "persistence")
FLIGHT = make_flight(JFK, LHR, datetime(2020, 2, 9))


def rr(source: str, lead_h: int, fuel: float, time_min: float | None = None) -> ReplayResult:
    """Hand-built replay; time follows fuel (as replay guarantees)."""
    if time_min is None:
        time_min = fuel / 100.0
    t0 = np.datetime64(FLIGHT.departure_time, "ns")
    t1 = t0 + np.timedelta64(int(round(time_min * 60e9)), "ns")
    return ReplayResult(
        flight_id=FLIGHT.flight_id, source=source, lead_h=lead_h,
        lat_deg=np.array([40.0, 51.0]), lon_deg=np.array([-73.0, 0.0]),
        time=np.array([t0, t1]), time_min=time_min, fuel_kg=fuel,
        co2_kg=3.16 * fuel, fuel_flow_min_kgh=5000.0, fuel_flow_max_kgh=6000.0,
    )


def test_select_lowest_fuel():
    reps = [rr("truth", 0, 30000.0), rr("hres", 24, 30100.0), rr("pangu", 12, 29900.0)]
    assert select_hindsight(reps, ORDER).source == "pangu"


def test_tie_prefers_truth_optimised():
    reps = [rr("hres", 12, 30000.0), rr("truth", 0, 30000.0), rr("pangu", 12, 30000.0)]
    assert select_hindsight(reps, ORDER).source == "truth"


def test_tie_between_forecasts_source_order_then_lead():
    reps = [rr("truth", 0, 31000.0), rr("pangu", 12, 30000.0), rr("graphcast", 48, 30000.0),
            rr("graphcast", 24, 30000.0)]
    best = select_hindsight(reps, ORDER)
    assert (best.source, best.lead_h) == ("graphcast", 24)


def test_wind_error_constant_offset():
    from regret.regret import wind_error
    from regret.winds import OffsetWind, UniformWind

    truth = UniformWind(10.0, -3.0)
    forecast = OffsetWind(truth, 3.0, 4.0)  # |(3, 4)| = 5
    assert abs(wind_error(forecast, truth, rr("truth", 0, 30000.0)) - 5.0) < 1e-6


def test_wind_error_zero_for_identical_fields():
    from regret.regret import wind_error
    from regret.winds import UniformWind

    w = UniformWind(10.0, -3.0)
    assert wind_error(w, w, rr("truth", 0, 30000.0)) == 0.0


COLUMNS = [
    "flight_id", "direction", "departure_time", "source", "lead_h", "is_truth_optimised",
    "is_hindsight", "fuel_kg", "time_min", "co2_kg", "regret_fuel_kg", "regret_fuel_pct",
    "regret_time_min", "regret_co2_kg", "wind_error_ms", "fuel_flow_min_kgh",
    "fuel_flow_max_kgh", "optimiser_gap_fuel_kg",
]


def table(reps, **kw):
    from regret.regret import flight_table

    return flight_table(FLIGHT, reps, ORDER, **kw)


def row(df, source, lead_h):
    r = df[(df.source == source) & (df.lead_h == lead_h)]
    assert len(r) == 1
    return r.iloc[0]


def base_reps():
    return [rr("truth", 0, 30000.0), rr("hres", 12, 30500.0), rr("hres", 24, 31000.0),
            rr("graphcast", 12, 30200.0), rr("pangu", 12, 30000.0)]  # pangu ties truth


def test_columns_order_and_dtypes():
    df = table(base_reps())
    assert list(df.columns) == COLUMNS
    assert len(df) == 5
    assert str(df.departure_time.dtype) == "datetime64[ns]"
    assert str(df.lead_h.dtype) == "int64"
    for c in ("is_truth_optimised", "is_hindsight"):
        assert df[c].dtype == bool
    for c in COLUMNS[7:]:
        assert str(df[c].dtype) == "float64", c
    assert (df.flight_id == FLIGHT.flight_id).all() and (df.direction == "eastbound").all()


def test_regrets_nonnegative_and_one_hindsight_with_zero_regret():
    df = table(base_reps())
    for c in ("regret_fuel_kg", "regret_time_min", "regret_co2_kg", "regret_fuel_pct"):
        assert (df[c] >= 0).all()
    h = df[df.is_hindsight]
    assert len(h) == 1
    assert h.iloc[0][["regret_fuel_kg", "regret_time_min", "regret_co2_kg"]].eq(0).all()


def test_regret_values():
    df = table(base_reps())
    r = row(df, "hres", 24)
    assert r.regret_fuel_kg == 1000.0
    assert abs(r.regret_fuel_pct - 100 * 1000 / 30000) < 1e-9
    assert abs(r.regret_time_min - 10.0) < 1e-9
    assert abs(r.regret_co2_kg - 3.16 * 1000) < 1e-6


def test_tie_with_truth_optimised_plan():
    df = table(base_reps())
    assert row(df, "truth", 0).is_hindsight
    p = row(df, "pangu", 12)
    assert p.regret_fuel_kg == 0 and not p.is_hindsight
    assert df.optimiser_gap_fuel_kg.isna().all()


def test_rankings_identical_across_fuel_time_co2():
    df = table(base_reps())
    for c in ("time_min", "co2_kg"):
        assert list(df.sort_values("fuel_kg", kind="stable").index) == list(
            df.sort_values(c, kind="stable").index)
        assert list(df.sort_values("fuel_kg", kind="stable")[c].diff().dropna() >= 0) == [True] * 4


def test_optimiser_gap_on_hindsight_row_only():
    reps = [rr("truth", 0, 30000.0), rr("hres", 12, 29800.0), rr("graphcast", 12, 29800.0),
            rr("pangu", 12, 30400.0)]
    df = table(reps)
    h = df[df.is_hindsight]
    assert (h.source.iloc[0], h.lead_h.iloc[0]) == ("hres", 12)
    assert abs(h.optimiser_gap_fuel_kg.iloc[0] - 200.0) < 1e-9
    assert df.optimiser_gap_fuel_kg.notna().sum() == 1
    assert row(df, "truth", 0).regret_fuel_kg == 200.0
    assert row(df, "graphcast", 12).regret_fuel_kg == 0.0 and not row(df, "graphcast", 12).is_hindsight


def test_two_tied_forecasts_resolve_by_source_then_lead():
    reps = [rr("truth", 0, 31000.0), rr("pangu", 12, 30000.0), rr("graphcast", 48, 30000.0),
            rr("graphcast", 24, 30000.0)]
    df = table(reps)
    h = df[df.is_hindsight]
    assert len(h) == 1 and (h.source.iloc[0], h.lead_h.iloc[0]) == ("graphcast", 24)


def test_wind_errors_mapping_missing_nan_truth_zero():
    df = table(base_reps(), wind_errors={("hres", 12): 2.5})
    assert row(df, "hres", 12).wind_error_ms == 2.5
    assert np.isnan(row(df, "hres", 24).wind_error_ms)
    assert row(df, "truth", 0).wind_error_ms == 0.0
    assert row(table(base_reps()), "truth", 0).wind_error_ms == 0.0
