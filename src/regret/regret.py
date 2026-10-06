"""Regret against the hindsight plan (CONTRACTS §2.9, §3, §4)."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from regret.types import Flight, ReplayResult, SourceName, TRUTH_SOURCE, WindField


def select_hindsight(
    replays: Sequence[ReplayResult], source_order: Sequence[SourceName]
) -> ReplayResult:
    """Lowest replayed fuel; ties: truth-optimised, earlier source, shorter lead."""
    order = {s: i for i, s in enumerate(source_order)}

    def key(r: ReplayResult):
        is_truth = r.source == TRUTH_SOURCE
        return (r.fuel_kg, 0 if is_truth else 1, -1 if is_truth else order[r.source], r.lead_h)

    return min(replays, key=key)


def wind_error(forecast: WindField, truth: WindField, hindsight: ReplayResult) -> float:
    """RMS of the forecast-minus-truth wind vector along the hindsight replay (m/s)."""
    args = (hindsight.lat_deg, hindsight.lon_deg, hindsight.time)
    fu, fv = forecast.uv(*args)
    tu, tv = truth.uv(*args)
    return float(np.sqrt(np.mean((fu - tu) ** 2 + (fv - tv) ** 2)))


COLUMNS = (
    "flight_id", "direction", "departure_time", "source", "lead_h", "is_truth_optimised",
    "is_hindsight", "fuel_kg", "time_min", "co2_kg", "regret_fuel_kg", "regret_fuel_pct",
    "regret_time_min", "regret_co2_kg", "wind_error_ms", "fuel_flow_min_kgh",
    "fuel_flow_max_kgh", "optimiser_gap_fuel_kg",
)


def flight_table(
    flight: Flight,
    replays: Sequence[ReplayResult],
    source_order: Sequence[SourceName],
    wind_errors: Mapping[tuple[SourceName, int], float] | None = None,
) -> pd.DataFrame:
    """One row per replayed plan of one flight, in the §4 column order."""
    wind_errors = wind_errors or {}
    best = select_hindsight(replays, source_order)
    truth = next((r for r in replays if r.source == TRUTH_SOURCE), None)
    # Gap only when a forecast plan is strictly lower than the truth-optimised plan.
    gap = (
        truth.fuel_kg - best.fuel_kg
        if truth is not None and best.source != TRUTH_SOURCE
        else np.nan
    )
    rows = []
    for r in replays:
        is_truth = r.source == TRUTH_SOURCE
        is_best = r is best
        rows.append({
            "flight_id": flight.flight_id,
            "direction": flight.direction,
            "departure_time": np.datetime64(flight.departure_time, "ns"),
            "source": r.source,
            "lead_h": r.lead_h,
            "is_truth_optimised": is_truth,
            "is_hindsight": is_best,
            "fuel_kg": r.fuel_kg,
            "time_min": r.time_min,
            "co2_kg": r.co2_kg,
            "regret_fuel_kg": r.fuel_kg - best.fuel_kg,
            "regret_fuel_pct": 100.0 * (r.fuel_kg - best.fuel_kg) / best.fuel_kg,
            "regret_time_min": r.time_min - best.time_min,
            "regret_co2_kg": r.co2_kg - best.co2_kg,
            "wind_error_ms": 0.0 if is_truth else wind_errors.get((r.source, r.lead_h), np.nan),
            "fuel_flow_min_kgh": r.fuel_flow_min_kgh,
            "fuel_flow_max_kgh": r.fuel_flow_max_kgh,
            "optimiser_gap_fuel_kg": gap if is_best else np.nan,
        })
    df = pd.DataFrame(rows, columns=list(COLUMNS))
    return df.astype({
        "departure_time": "datetime64[ns]", "lead_h": "int64",
        "is_truth_optimised": bool, "is_hindsight": bool,
        **{c: "float64" for c in COLUMNS[7:]},
    })
