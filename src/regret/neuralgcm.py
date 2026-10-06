"""NeuralGCM add-on (SPEC 1.5): five forecast sources planned 12-hourly on the matched flights."""

from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Sequence

import pandas as pd

from regret import planner, regret, replay, sources
from regret.config import get_config, matched_flights
from regret.types import TRUTH_LEAD_H, TRUTH_SOURCE, Config, Flight

log = logging.getLogger(__name__)

NAME = "neuralgcm"
STEP_H = 12  # planning resolution of every add-on forecast plan
RESULTS_FILE = "neuralgcm_regret.parquet"
SENSITIVITY_FILE = "neuralgcm_sensitivity.parquet"
SENSITIVITY_COLUMNS = (
    "source", "lead_h", "n", "regret_6h_kg", "regret_12h_kg", "regret_12h_core_set_kg",
)


def addon_sources(cfg: Config) -> tuple[str, ...]:
    return (*cfg.sources, NAME)


def addon_flights(cfg: Config) -> tuple[Flight, ...]:
    return matched_flights(cfg, NAME)


def _flight_tables(args: tuple[Config, Flight, tuple[int, ...]]):
    """Per flight: the add-on table (5 sources, 12-hourly) and the core-set tables at 6 h and 12 h.

    Top-level so it pickles under spawn.
    """
    cfg, flight, leads_h = args
    truth = sources.truth_winds(cfg)
    base = planner.plan(truth, flight, source=TRUTH_SOURCE, lead_h=TRUTH_LEAD_H)
    plans, forecasts = [base], {}
    for source in addon_sources(cfg):
        for lead_h in leads_h:
            wind = sources.forecast_winds(cfg, source, flight, lead_h, step_h=STEP_H)
            forecasts[(source, lead_h)] = wind
            plans.append(planner.plan(wind, flight, source=source, lead_h=lead_h))
    replays12 = [replay.replay(p, flight, truth) for p in plans]
    hindsight = regret.select_hindsight(replays12, addon_sources(cfg))
    errors = {k: regret.wind_error(w, truth, hindsight) for k, w in forecasts.items()}
    addon = regret.flight_table(flight, replays12, addon_sources(cfg), errors)

    # like-for-like 12-hourly regret against the core candidate set (truth + 4 core sources)
    core12 = regret.flight_table(
        flight, [r for r in replays12 if r.source in (TRUTH_SOURCE, *cfg.sources)], cfg.sources
    )
    # native (6-hourly) planning with the core candidate set
    plans6 = [base]
    for source in cfg.sources:
        for lead_h in leads_h:
            wind = sources.forecast_winds(cfg, source, flight, lead_h)
            plans6.append(planner.plan(wind, flight, source=source, lead_h=lead_h))
    core6 = regret.flight_table(flight, [replay.replay(p, flight, truth) for p in plans6], cfg.sources)
    return addon, core6, core12


def _sensitivity(core6: pd.DataFrame, core12: pd.DataFrame, addon: pd.DataFrame, order) -> pd.DataFrame:
    """Mean fuel regret (kg) per core source and lead: 6 h planning, 12 h planning (5-source set),
    and 12 h planning against the core candidate set."""

    def mean_regret(df: pd.DataFrame, col: str) -> pd.Series:
        fc = df[~df["is_truth_optimised"] & df["source"].isin(order)]
        return fc.groupby(["source", "lead_h"], sort=False)["regret_fuel_kg"].mean().rename(col)

    fc = addon[~addon["is_truth_optimised"] & addon["source"].isin(order)]
    n = fc.groupby(["source", "lead_h"], sort=False).size().rename("n")
    out = pd.concat(
        [n, mean_regret(core6, "regret_6h_kg"), mean_regret(addon, "regret_12h_kg"),
         mean_regret(core12, "regret_12h_core_set_kg")],
        axis=1,
    ).reset_index()
    rank = {s: i for i, s in enumerate(order)}
    out = out.assign(_s=out["source"].map(rank)).sort_values(["_s", "lead_h"], kind="stable").drop(columns="_s")
    return out[list(SENSITIVITY_COLUMNS)].reset_index(drop=True)


def run(
    cfg: Config,
    *,
    flights: Sequence[Flight] | None = None,
    leads_h: Sequence[int] | None = None,
    workers: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(add-on results, sensitivity table); identical for any worker count."""
    fl = tuple(addon_flights(cfg) if flights is None else flights)
    leads = tuple(cfg.leads_h if leads_h is None else leads_h)
    n = max(1, min(cfg.workers if workers is None else workers, len(fl)))
    jobs = [(cfg, f, leads) for f in fl]
    if n == 1:
        parts = [_flight_tables(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=n) as pool:
            parts = list(pool.map(_flight_tables, jobs))
    addon, core6, core12 = (pd.concat(p, ignore_index=True) for p in zip(*parts))
    order = {s: i for i, s in enumerate((TRUTH_SOURCE, *addon_sources(cfg)))}
    addon = (
        addon.assign(_s=addon["source"].map(order))
        .sort_values(["departure_time", "direction", "_s", "lead_h"], kind="stable")
        .drop(columns="_s")
        .reset_index(drop=True)
    )
    return addon, _sensitivity(core6, core12, addon, cfg.sources)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    cfg = get_config()
    t0 = time.perf_counter()
    df, sens = run(cfg)
    out = cfg.results_path.parent
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / RESULTS_FILE, engine="pyarrow", index=False)
    sens.to_parquet(out / SENSITIVITY_FILE, engine="pyarrow", index=False)
    log.info("wrote %d rows to %s and %d to %s", len(df), out / RESULTS_FILE, len(sens), out / SENSITIVITY_FILE)
    log.info("elapsed_s=%.1f", time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
