"""Statistics on a small synthetic table shaped like the CONTRACTS section 4 schema."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from regret import stats

# fuel_kg per flight for (source, lead_h); "truth" is the truth-optimised plan.
PLANS = [("truth", 0), ("hres", 6), ("hres", 12), ("persistence", 6), ("persistence", 12)]
FUEL = {
    "F1": [100, 100, 105, 110, 120],  # hindsight truth; hres 6 ties it (regret 0)
    "F2": [200, 190, 210, 200, 205],  # hindsight hres 6; optimiser gap 10
    "F3": [300, 310, 300, 320, 300],  # hindsight truth; hres 12 and persistence 12 tie
    "F4": [400, 395, 395, 410, 420],  # hindsight hres 6 (earlier lead beats hres 12); gap 5
}
DIRECTION = {"F1": "eastbound", "F2": "eastbound", "F3": "westbound", "F4": "westbound"}


def make_table() -> pd.DataFrame:
    rows = []
    for fid, fuels in FUEL.items():
        best = min(fuels)
        winner = fuels.index(best)  # first minimum: truth first, then source order, then lead
        for i, ((src, lead), fuel) in enumerate(zip(PLANS, fuels)):
            truth = src == "truth"
            hind = i == winner
            rows.append(
                dict(
                    flight_id=fid, direction=DIRECTION[fid],
                    departure_time=pd.Timestamp("2020-02-09"),
                    source=src, lead_h=lead,
                    is_truth_optimised=truth, is_hindsight=hind,
                    fuel_kg=float(fuel), time_min=fuel / 10, co2_kg=3.16 * fuel,
                    regret_fuel_kg=float(fuel - best),
                    regret_fuel_pct=100.0 * (fuel - best) / best,
                    regret_time_min=(fuel - best) / 10,
                    regret_co2_kg=3.16 * (fuel - best),
                    wind_error_ms=0.0, fuel_flow_min_kgh=1.0, fuel_flow_max_kgh=2.0,
                    optimiser_gap_fuel_kg=(fuels[0] - best) if hind and not truth and fuels[0] > best else np.nan,
                )
            )
    df = pd.DataFrame(rows)
    df["lead_h"] = df["lead_h"].astype("int64")
    return df


@pytest.fixture
def df() -> pd.DataFrame:
    return make_table()


def row(agg: pd.DataFrame, source: str, lead: int) -> pd.Series:
    return agg[(agg.source == source) & (agg.lead_h == lead)].iloc[0]


def test_constants():
    assert stats.BOOTSTRAP_RESAMPLES == 2000
    assert stats.BOOTSTRAP_SEED == 20200209
    assert stats.CI_LEVEL == 0.90


def test_aggregate_layout(df):
    agg = stats.aggregate(df)
    expected = ["source", "lead_h", "n"]
    for m in ("fuel_kg", "fuel_pct", "time_min", "co2_kg"):
        expected += [f"{m}_mean", f"{m}_ci_lo", f"{m}_ci_hi", f"{m}_median", f"{m}_p90"]
    expected += ["zero_regret_share", "hindsight_share", "optimiser_gap_count", "optimiser_gap_mean_kg"]
    assert list(agg.columns) == expected
    assert len(agg) == 4  # forecast plans only: no truth row
    assert "truth" not in set(agg.source)
    assert list(zip(agg.source, agg.lead_h)) == [("hres", 6), ("hres", 12), ("persistence", 6), ("persistence", 12)]
    assert (agg.n == 4).all()


def test_aggregate_mean_median_p90(df):
    agg = stats.aggregate(df)
    r = row(agg, "hres", 6)  # regrets 0, 0, 10, 0 -> hand: mean 2.5, median 0, p90 = 7 (linear: 0.9*3=2.7 -> 0+0.7*10)
    assert r.fuel_kg_mean == pytest.approx(2.5)
    assert r.fuel_kg_median == pytest.approx(0.0)
    assert r.fuel_kg_p90 == pytest.approx(7.0)
    r = row(agg, "persistence", 6)  # regrets 10, 10, 20, 15 -> mean 13.75, median 12.5, p90 = 18.5
    assert r.fuel_kg_mean == pytest.approx(13.75)
    assert r.fuel_kg_median == pytest.approx(12.5)
    assert r.fuel_kg_p90 == pytest.approx(18.5)
    assert r.co2_kg_mean == pytest.approx(3.16 * 13.75)
    assert r.time_min_mean == pytest.approx(1.375)


def test_fuel_pct_is_regret_over_hindsight_fuel(df):
    # regret_fuel_pct is a stored column (CONTRACTS section 4); aggregate passes it through.
    r = row(stats.aggregate(df), "persistence", 6)
    hindsight = [100, 190, 300, 395]
    pct = [100 * x / h for x, h in zip([10, 10, 20, 15], hindsight)]
    assert r.fuel_pct_mean == pytest.approx(np.mean(pct))
    assert r.fuel_pct_median == pytest.approx(np.median(pct))
    assert r.fuel_pct_p90 == pytest.approx(np.percentile(pct, 90))


def test_bootstrap_same_seed_identical():
    v = np.array([0.0, 0.0, 10.0, 0.0, 3.0])
    assert stats.bootstrap_mean_ci(v) == stats.bootstrap_mean_ci(v)
    assert stats.bootstrap_mean_ci(v, seed=1) == stats.bootstrap_mean_ci(v, seed=1)


def test_bootstrap_matches_manual_resampling():
    v = np.array([1.0, 2.0, 4.0, 8.0])
    rng = np.random.default_rng(stats.BOOTSTRAP_SEED)
    means = v[rng.integers(0, len(v), size=(2000, len(v)))].mean(axis=1)
    lo, hi = stats.bootstrap_mean_ci(v)
    assert lo == pytest.approx(np.percentile(means, 5))
    assert hi == pytest.approx(np.percentile(means, 95))


def test_ci_contains_mean(df):
    agg = stats.aggregate(df)
    for m in ("fuel_kg", "fuel_pct", "time_min", "co2_kg"):
        assert (agg[f"{m}_ci_lo"] <= agg[f"{m}_mean"] + 1e-12).all()
        assert (agg[f"{m}_mean"] <= agg[f"{m}_ci_hi"] + 1e-12).all()


def test_aggregate_deterministic(df):
    pd.testing.assert_frame_equal(stats.aggregate(df), stats.aggregate(df))


def test_zero_regret_share_counts_ties(df):
    agg = stats.aggregate(df)
    assert row(agg, "hres", 6).zero_regret_share == pytest.approx(3 / 4)  # F1 tie with truth, F2, F4
    assert row(agg, "hres", 12).zero_regret_share == pytest.approx(2 / 4)  # F3 and F4 ties
    assert row(agg, "persistence", 6).zero_regret_share == 0.0
    assert row(agg, "persistence", 12).zero_regret_share == pytest.approx(1 / 4)


def test_hindsight_shares_sum_to_one_per_flight(df):
    assert df.groupby("flight_id").is_hindsight.sum().eq(1).all()
    sh = stats.hindsight_shares(df)
    assert list(sh.columns) == ["source", "lead_h", "hindsight_share"]
    assert sh.hindsight_share.sum() == pytest.approx(1.0)
    got = {(r.source, r.lead_h): r.hindsight_share for r in sh.itertuples()}
    assert got[("truth", 0)] == pytest.approx(2 / 4)
    assert got[("hres", 6)] == pytest.approx(2 / 4)
    assert got[("hres", 12)] == 0.0
    assert ("truth", 0) in got


def test_aggregate_hindsight_share(df):
    agg = stats.aggregate(df)
    assert row(agg, "hres", 6).hindsight_share == pytest.approx(2 / 4)
    assert row(agg, "persistence", 12).hindsight_share == 0.0


def test_optimiser_gap(df):
    agg = stats.aggregate(df)
    r = row(agg, "hres", 6)
    assert r.optimiser_gap_count == 2
    assert r.optimiser_gap_mean_kg == pytest.approx(7.5)  # gaps 10 and 5
    for src, lead in [("hres", 12), ("persistence", 6), ("persistence", 12)]:
        r = row(agg, src, lead)
        assert r.optimiser_gap_count == 0
        assert np.isnan(r.optimiser_gap_mean_kg)


def test_by_direction(df):
    agg = stats.aggregate(df, by=("source", "lead_h", "direction"))
    assert list(agg.columns[:4]) == ["source", "lead_h", "direction", "n"]
    assert len(agg) == 8
    r = agg[(agg.source == "hres") & (agg.lead_h == 6) & (agg.direction == "eastbound")].iloc[0]
    assert r.n == 2
    assert r.fuel_kg_mean == pytest.approx(0.0)
    assert r.optimiser_gap_count == 1
    sh = stats.hindsight_shares(df, by=("source", "lead_h", "direction"))
    assert sh.hindsight_share.sum() == pytest.approx(1.0)
