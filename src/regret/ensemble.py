"""Ensemble robust plan choice (SPEC 1.3 item 1, reduced method 1.5).

Per matched flight and lead, at 12-hourly planning: plan on each of M NeuralGCM members,
cross-replay every member's plan through every member's winds (as if each were the truth),
pick the plan with the lowest mean cost (mean-robust) and the lowest p90 cost (p90-robust),
and replay both through the ERA5 truth. Regret is floored against the add-on hindsight plan.
"""

from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from regret import neuralgcm, planner, replay, sources
from regret.config import get_config
from regret.types import TRUTH_SOURCE, Config, Flight

log = logging.getLogger(__name__)

SOURCE = "neuralgcm_ens"
STEP_H = neuralgcm.STEP_H
MEMBERS = 25  # measured: M = 50 takes ~180 s per flight x lead on one worker (71 ms per cross-replay); M = 20 ran 110 flights x 5 leads in 1,045 s on 12 workers, cost grows as M^2, so M = 25 is ~1,650 s (<= 30 min)
RESULTS_FILE = "ensemble_regret.parquet"
CHOICES = ("mean_robust", "p90_robust")
COLUMNS = (
    "flight_id", "direction", "lead_h", "choice", "members", "fuel_kg", "time_min", "co2_kg",
    "regret_fuel_kg", "beats_hindsight",
)


def choose_robust(cost: np.ndarray) -> tuple[int, int]:
    """(mean-robust, p90-robust) member plan indices; ``cost[j, k]`` is plan j replayed through
    member k. Ties go to the lowest index. With small M the p90 is close to the maximum."""
    cost = np.asarray(cost, dtype=float)
    return int(cost.mean(axis=1).argmin()), int(np.percentile(cost, 90, axis=1).argmin())


def floored_regret(fuel_kg: float, hindsight_kg: float) -> float:
    """``cost - min(hindsight, own cost)``: never negative."""
    return float(fuel_kg - min(hindsight_kg, fuel_kg))


def beats_hindsight(fuel_kg: float, hindsight_kg: float) -> bool:
    return bool(fuel_kg < hindsight_kg)


def _flight_rows(args: tuple[Config, Flight, tuple[int, ...], int, float | None]) -> list[dict]:
    """Rows (two choices per lead) of one flight. Top-level so it pickles under spawn."""
    cfg, flight, leads_h, members, hindsight = args
    truth = sources.truth_winds(cfg)
    rows = []
    for lead_h in leads_h:
        winds = [
            sources.forecast_winds(cfg, SOURCE, flight, lead_h, step_h=STEP_H, member=k)
            for k in range(members)
        ]
        plans = [planner.plan(w, flight, source=SOURCE, lead_h=lead_h) for w in winds]
        cost = np.empty((members, members))
        seen: dict[tuple, int] = {}
        for j, p in enumerate(plans):
            key = (p.lat_deg, p.lon_deg)  # identical paths replay identically
            if key in seen:
                cost[j] = cost[seen[key]]
                continue
            seen[key] = j
            cost[j] = [replay.replay(p, flight, w).fuel_kg for w in winds]
        picks = dict(zip(CHOICES, choose_robust(cost)))
        results = {c: replay.replay(plans[j], flight, truth) for c, j in picks.items()}
        hind = min(r.fuel_kg for r in results.values()) if hindsight is None else hindsight
        for choice in CHOICES:
            r = results[choice]
            rows.append({
                "flight_id": flight.flight_id, "direction": flight.direction, "lead_h": lead_h,
                "choice": choice, "members": members, "fuel_kg": r.fuel_kg,
                "time_min": r.time_min, "co2_kg": r.co2_kg,
                "regret_fuel_kg": floored_regret(r.fuel_kg, hind),
                "beats_hindsight": beats_hindsight(r.fuel_kg, hind),
            })
    return rows


def addon_hindsight(cfg: Config) -> dict[str, float]:
    """Add-on hindsight fuel (kg) per flight, from ``neuralgcm_regret.parquet``."""
    df = pd.read_parquet(cfg.results_path.parent / neuralgcm.RESULTS_FILE)
    return df[df["is_hindsight"]].set_index("flight_id")["fuel_kg"].to_dict()


def run(
    cfg: Config,
    *,
    flights: Sequence[Flight] | None = None,
    leads_h: Sequence[int] | None = None,
    members: int = MEMBERS,
    workers: int | None = None,
    hindsight: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Ensemble results; identical for any worker count.

    ``hindsight`` maps flight_id to the add-on hindsight fuel. Default: read it from the add-on's
    results file when ``flights`` is None; with an explicit ``flights`` and no mapping, the cheaper
    of the two chosen plans stands in, so tests need no add-on file.
    """
    fl = tuple(neuralgcm.addon_flights(cfg) if flights is None else flights)
    leads = tuple(cfg.leads_h if leads_h is None else leads_h)
    if hindsight is None and flights is None:
        hindsight = addon_hindsight(cfg)
    jobs = [(cfg, f, leads, members, None if hindsight is None else hindsight[f.flight_id]) for f in fl]
    n = max(1, min(cfg.workers if workers is None else workers, len(fl)))
    if n == 1:
        parts = [_flight_rows(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=n) as pool:
            parts = list(pool.map(_flight_rows, jobs, chunksize=1))
    df = pd.DataFrame([r for p in parts for r in p], columns=list(COLUMNS))
    return df.astype({"lead_h": "int64", "members": "int64", "beats_hindsight": bool,
                      **{c: "float64" for c in COLUMNS[5:9]}})


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    cfg = get_config()
    t0 = time.perf_counter()
    df = run(cfg)
    out = cfg.results_path.parent
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / RESULTS_FILE, engine="pyarrow", index=False)
    log.info("wrote %d rows to %s (M=%d members)", len(df), out / RESULTS_FILE, MEMBERS)
    log.info("elapsed_s=%.1f", time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
