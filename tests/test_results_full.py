"""Checks on the full Jan-Feb 2020 results (T17). Skipped until `regret compute` has run."""

import pandas as pd
import pytest

from regret.config import flights, get_config
from regret.regret import COLUMNS

CFG = get_config("full")

pytestmark = pytest.mark.skipif(
    not CFG.results_path.exists(), reason=f"{CFG.results_path} not computed yet"
)


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_parquet(CFG.results_path)


def test_columns_match_schema(df):
    assert list(df.columns) == list(COLUMNS)


def test_forecast_plan_rows(df):
    n_flights = len(flights(CFG))
    assert n_flights == 120
    fc = df[~df["is_truth_optimised"]]
    assert len(fc) == n_flights * len(CFG.leads_h) * len(CFG.sources)


def test_truth_optimised_rows(df):
    assert int(df["is_truth_optimised"].sum()) == 120


def test_regret_is_non_negative(df):
    assert df["regret_fuel_kg"].min() >= 0


def test_one_hindsight_per_flight(df):
    assert (df.groupby("flight_id")["is_hindsight"].sum() == 1).all()
    assert df["flight_id"].nunique() == 120
