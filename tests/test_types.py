from __future__ import annotations

import dataclasses
import re
from datetime import datetime
from pathlib import Path

import pytest

from regret import types as t

CONTRACTS = Path(__file__).resolve().parent.parent / "docs" / "CONTRACTS.md"
TYPE_NAMES = ["Airport", "Leg", "Flight", "Plan", "ReplayResult", "Box", "Dataset", "Config"]


def _split_fields(cell: str) -> list[str]:
    # split on commas outside brackets/parentheses
    parts, depth, cur = [], 0, ""
    for ch in cell:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    names = []
    for p in parts:
        m = re.match(r"\s*`([a-z_0-9]+)", p)
        if m:
            names.append(m.group(1))
    return names


def contract_fields() -> dict[str, list[str]]:
    out = {}
    for line in CONTRACTS.read_text().split("## 2. Module signatures")[0].splitlines():
        m = re.match(r"\| `(\w+)` \| (.*) \|$", line)
        if m and m.group(1) in TYPE_NAMES:
            out[m.group(1)] = _split_fields(m.group(2))
    return out


def test_contract_table_parsed():
    assert set(contract_fields()) == set(TYPE_NAMES)


@pytest.mark.parametrize("name", TYPE_NAMES)
def test_field_names_match_contract(name):
    cls = getattr(t, name)
    assert [f.name for f in dataclasses.fields(cls)] == contract_fields()[name]


def test_box_fields_are_all_four():
    # the Box row lists names before one shared type; guard the parser
    assert contract_fields()["Box"] == ["lat_min_deg", "lat_max_deg", "lon_min_deg", "lon_max_deg"]


@pytest.mark.parametrize("name", TYPE_NAMES)
def test_frozen(name):
    cls = getattr(t, name)
    assert cls.__dataclass_params__.frozen


def test_replay_result_eq_false():
    assert t.ReplayResult.__dataclass_params__.eq is False


def test_frozen_instance_rejects_assignment():
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.JFK.lat_deg = 0.0


def test_constants():
    assert t.TRUTH_SOURCE == "truth"
    assert t.TRUTH_LEAD_H == 0


def test_airports():
    assert t.JFK.code == "JFK" and t.LHR.code == "LHR"
    assert t.JFK.lat_deg == pytest.approx(40.6398, abs=0.01)
    assert t.JFK.lon_deg == pytest.approx(-73.7789, abs=0.01)
    assert t.LHR.lat_deg == pytest.approx(51.4700, abs=0.01)
    assert t.LHR.lon_deg == pytest.approx(-0.4543, abs=0.01)


def test_flight_id_and_direction():
    f = t.make_flight(t.JFK, t.LHR, datetime(2020, 2, 9, 0, 0))
    assert f.flight_id == "JFK-LHR-20200209T0000"
    assert f.direction == "eastbound"
    g = t.make_flight(t.LHR, t.JFK, datetime(2020, 2, 9, 12, 0))
    assert g.flight_id == "LHR-JFK-20200209T1200"
    assert g.direction == "westbound"
