"""Compute pipeline: one flight per worker, per CONTRACTS §2.11."""

from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Sequence

import pandas as pd

from regret import planner, regret, replay, sources
from regret.config import get_config
from regret.config import flights as config_flights
from regret.types import TRUTH_LEAD_H, TRUTH_SOURCE, Config, Flight

log = logging.getLogger(__name__)


class SoftCheckWarning(UserWarning):
    """A plausibility check on the results failed (SPEC §6.4); not an error."""


def _flight_rows(args: tuple[Config, Flight, tuple[int, ...]]) -> pd.DataFrame:
    """Per-flight procedure (§2.11), top-level so it pickles under spawn."""
    cfg, flight, leads_h = args
    truth = sources.truth_winds(cfg)
    plans = [planner.plan(truth, flight, source=TRUTH_SOURCE, lead_h=TRUTH_LEAD_H)]
    forecasts = {}
    for source in cfg.sources:
        for lead_h in leads_h:
            wind = sources.forecast_winds(cfg, source, flight, lead_h)
            forecasts[(source, lead_h)] = wind
            plans.append(planner.plan(wind, flight, source=source, lead_h=lead_h))
    replays = [replay.replay(p, flight, truth) for p in plans]
    hindsight = regret.select_hindsight(replays, cfg.sources)
    errors = {k: regret.wind_error(w, truth, hindsight) for k, w in forecasts.items()}
    return regret.flight_table(flight, replays, cfg.sources, errors)


def run(
    cfg: Config,
    *,
    flights: Sequence[Flight] | None = None,
    leads_h: Sequence[int] | None = None,
    workers: int | None = None,
) -> pd.DataFrame:
    fl = tuple(config_flights(cfg) if flights is None else flights)
    leads = tuple(cfg.leads_h if leads_h is None else leads_h)
    n = max(1, min(cfg.workers if workers is None else workers, len(fl)))
    jobs = [(cfg, f, leads) for f in fl]
    if n == 1:
        parts = [_flight_rows(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=n) as pool:
            parts = list(pool.map(_flight_rows, jobs))
    df = pd.concat(parts, ignore_index=True)
    order = {s: i for i, s in enumerate((TRUTH_SOURCE, *cfg.sources))}
    df = (
        df.assign(_s=df["source"].map(order))
        .sort_values(["departure_time", "direction", "_s", "lead_h"], kind="stable")
        .drop(columns="_s")
        .reset_index(drop=True)
    )
    return df


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    cfg = get_config()
    t0 = time.perf_counter()
    df = run(cfg)
    cfg.results_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cfg.results_path, engine="pyarrow", index=False)
    log.info("wrote %d rows to %s", len(df), cfg.results_path)
    log.info("elapsed_s=%.1f", time.perf_counter() - t0)
    return 0
