"""Shared types (docs/CONTRACTS.md section 1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import ArrayLike

TRUTH_SOURCE = "truth"
TRUTH_LEAD_H = 0

SourceName = str


class WindField(Protocol):
    def uv(
        self, lat: ArrayLike, lon: ArrayLike, time: ArrayLike
    ) -> tuple[np.ndarray, np.ndarray]: ...


@dataclass(frozen=True)
class Airport:
    code: str
    lat_deg: float
    lon_deg: float


@dataclass(frozen=True)
class Leg:
    origin: Airport
    destination: Airport
    departure_hour_utc: int


@dataclass(frozen=True)
class Flight:
    flight_id: str
    origin: Airport
    destination: Airport
    departure_time: datetime
    direction: str


@dataclass(frozen=True)
class Plan:
    flight_id: str
    source: SourceName
    lead_h: int
    lat_deg: tuple[float, ...]
    lon_deg: tuple[float, ...]
    planned_time_min: float


@dataclass(frozen=True, eq=False)
class ReplayResult:
    flight_id: str
    source: SourceName
    lead_h: int
    lat_deg: np.ndarray
    lon_deg: np.ndarray
    time: np.ndarray
    time_min: float
    fuel_kg: float
    co2_kg: float
    fuel_flow_min_kgh: float
    fuel_flow_max_kgh: float


@dataclass(frozen=True)
class Box:
    lat_min_deg: float
    lat_max_deg: float
    lon_min_deg: float
    lon_max_deg: float


@dataclass(frozen=True)
class Dataset:
    name: str
    store: str
    variables: tuple[str, ...]
    fetch_by_default: bool
    kind: str
    derived_from: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    mode: str
    datasets: tuple[Dataset, ...]
    sources: tuple[SourceName, ...]
    leads_h: tuple[int, ...]
    box: Box
    legs: tuple[Leg, ...]
    first_departure_date: date
    last_departure_date: date
    showcase_departure: datetime
    era5_start: datetime
    era5_end: datetime
    cache_dir: Path
    results_path: Path
    report_path: Path
    workers: int


JFK = Airport("JFK", 40.6398, -73.7789)
LHR = Airport("LHR", 51.4700, -0.4543)


def make_flight(origin: Airport, destination: Airport, departure_time: datetime) -> Flight:
    """Build a Flight with the contract's flight_id and direction rules."""
    return Flight(
        flight_id=f"{origin.code}-{destination.code}-{departure_time:%Y%m%dT%H%M}",
        origin=origin,
        destination=destination,
        departure_time=departure_time,
        direction="eastbound" if destination.lon_deg > origin.lon_deg else "westbound",
    )
