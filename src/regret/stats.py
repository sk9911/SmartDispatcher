"""Statistics over the results table (CONTRACTS section 2.10): bootstrap CIs, aggregates, hindsight shares."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20200209
CI_LEVEL = 0.90

_METRICS = ("fuel_kg", "fuel_pct", "time_min", "co2_kg")


def bootstrap_mean_ci(
    values: np.ndarray,
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    level: float = CI_LEVEL,
) -> tuple[float, float]:
    """Percentile interval of the mean, resampling flights (one value per flight) with replacement."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, v.size, size=(resamples, v.size))].mean(axis=1)
    alpha = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [alpha, 1.0 - alpha])
    return (float(lo), float(hi))


def _sorted_keys(keys: pd.DataFrame, source_order: list, by: Sequence[str]) -> pd.DataFrame:
    keys = keys.copy()
    if "source" in by:
        keys["_s"] = keys["source"].map({s: i for i, s in enumerate(source_order)})
        keys = keys.sort_values(["_s", *[c for c in by if c != "source"]], kind="stable").drop(columns="_s")
    else:
        keys = keys.sort_values(list(by), kind="stable")
    return keys


def hindsight_shares(df: pd.DataFrame, by: Sequence[str] = ("source", "lead_h")) -> pd.DataFrame:
    """Share of flights whose hindsight plan falls in each group; all rows, including the truth-optimised plan."""
    by = list(by)
    n_flights = df["flight_id"].nunique()
    hind = df[df["is_hindsight"]]
    counts = hind.groupby(by, sort=False).size()
    groups = df[by].drop_duplicates()
    out = groups.merge(counts.rename("_c").reset_index(), on=by, how="left")
    out["hindsight_share"] = out.pop("_c").fillna(0).astype(float) / n_flights
    order = list(dict.fromkeys(df["source"])) if "source" in by else []
    return _sorted_keys(out, order, by).reset_index(drop=True)


def aggregate(df: pd.DataFrame, by: Sequence[str] = ("source", "lead_h")) -> pd.DataFrame:
    """Per-group regret statistics over forecast-plan rows."""
    by = list(by)
    source_order = list(dict.fromkeys(df["source"]))
    shares = hindsight_shares(df, by).set_index(by)["hindsight_share"]
    fc = df[~df["is_truth_optimised"]]
    rows = []
    for key, g in fc.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        r = dict(zip(by, key))
        r["n"] = len(g)
        for m in _METRICS:
            v = g[f"regret_{m}"].to_numpy(dtype=float)
            lo, hi = bootstrap_mean_ci(v)
            r[f"{m}_mean"] = float(v.mean())
            r[f"{m}_ci_lo"] = lo
            r[f"{m}_ci_hi"] = hi
            r[f"{m}_median"] = float(np.median(v))
            r[f"{m}_p90"] = float(np.percentile(v, 90))
        r["zero_regret_share"] = float((g["regret_fuel_kg"] == 0).mean())
        r["hindsight_share"] = float(shares.get(key if len(key) > 1 else key[0], 0.0))
        gaps = g["optimiser_gap_fuel_kg"].dropna()
        r["optimiser_gap_count"] = int(len(gaps))
        r["optimiser_gap_mean_kg"] = float(gaps.mean()) if len(gaps) else float("nan")
        rows.append(r)
    out = pd.DataFrame(rows)
    out = _sorted_keys(out, source_order, by) if len(out) else out
    return out.reset_index(drop=True)
