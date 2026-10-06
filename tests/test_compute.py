from __future__ import annotations

import warnings

import pandas as pd
import pytest

from regret import compute
from regret.compute import SoftCheckWarning, run
from regret.config import flights, get_config
from regret.regret import COLUMNS

CFG = get_config("fixture")


@pytest.fixture(scope="module")
def slice_df() -> pd.DataFrame:
    return run(CFG, flights=flights(CFG)[:1], leads_h=(24, 120), workers=1)


def test_slice_shape_and_invariants(slice_df):
    df = slice_df
    assert list(df.columns) == list(COLUMNS)
    assert len(df) == 2 * len(CFG.sources) + 1
    assert df["is_truth_optimised"].iloc[0]
    assert df["is_hindsight"].sum() == 1
    assert df["regret_fuel_kg"].min() >= 0


def test_workers_identical(slice_df):
    four = run(CFG, flights=flights(CFG)[:1], leads_h=(24, 120), workers=4)
    pd.testing.assert_frame_equal(slice_df, four)


def test_rows_sorted_per_contract(slice_df):
    order = {s: i for i, s in enumerate(("truth", *CFG.sources))}
    keys = list(zip(slice_df["source"].map(order), slice_df["lead_h"]))
    assert keys == sorted(keys)


def _fixture_df() -> pd.DataFrame:
    return pd.read_parquet(CFG.results_path)


def test_fixture_results_schema_and_counts():
    df = _fixture_df()
    fl = flights(CFG)
    assert list(df.columns) == list(COLUMNS)
    fc = df[~df["is_truth_optimised"]]
    assert len(fc) == len(fl) * len(CFG.leads_h) * len(CFG.sources)
    assert df["is_truth_optimised"].sum() == len(fl)
    assert df["regret_fuel_kg"].min() >= 0
    assert (df.groupby("flight_id")["is_hindsight"].sum() == 1).all()
    assert df["flight_id"].nunique() == len(fl)


def test_main_writes_parquet(tmp_path, monkeypatch):
    import dataclasses

    cfg = dataclasses.replace(CFG, results_path=tmp_path / "sub" / "r.parquet")
    monkeypatch.setattr(compute, "get_config", lambda *a, **k: cfg)
    real_run = compute.run
    monkeypatch.setattr(
        compute, "run", lambda c: real_run(c, flights=flights(CFG)[:1], leads_h=(24,), workers=1)
    )
    assert compute.main([]) == 0
    out = pd.read_parquet(cfg.results_path)
    assert list(out.columns) == list(COLUMNS)


def test_soft_check_persistence_vs_hres():
    df = _fixture_df()
    m = df[(df["lead_h"] == 120) & ~df["is_truth_optimised"]].groupby("source")["regret_fuel_kg"].mean()
    if m["persistence"] < m["hres"]:
        warnings.warn(
            f"persistence ({m['persistence']:.1f} kg) beats HRES ({m['hres']:.1f} kg) at 120 h",
            SoftCheckWarning,
        )
