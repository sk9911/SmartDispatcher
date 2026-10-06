"""Physics sanity on the real ERA5 fixture (SPEC 6.3): 2020-02-09, the strong-jet night."""
from __future__ import annotations

from datetime import datetime

import pytest

from regret import config, planner, replay, sources
from regret.types import TRUTH_SOURCE


@pytest.fixture(scope="module")
def results():
    cfg = config.get_config("fixture")
    truth = sources.truth_winds(cfg)
    out = {}
    for f in config.flights(cfg):
        if f.departure_time.date() != datetime(2020, 2, 9).date():
            continue
        p = planner.plan(truth, f, source=TRUTH_SOURCE, lead_h=0)
        out[f.direction] = replay.replay(p, f, truth)
    assert set(out) == {"eastbound", "westbound"}
    return out


def test_eastbound_truth_plan_is_at_least_45_min_faster_than_westbound(results):
    east, west = results["eastbound"], results["westbound"]
    print(f"east {east.time_min:.1f} min, west {west.time_min:.1f} min")
    assert west.time_min - east.time_min >= 45


def test_trip_fuel_is_25_to_50_tonnes_both_directions(results):
    for r in results.values():
        assert 25_000 <= r.fuel_kg <= 50_000


def test_every_step_fuel_flow_is_4000_to_8000_kgh(results):
    for r in results.values():
        assert 4000 <= r.fuel_flow_min_kgh <= r.fuel_flow_max_kgh <= 8000


def test_co2_is_exactly_3_16_times_fuel(results):
    for r in results.values():
        assert r.co2_kg == 3.16 * r.fuel_kg
