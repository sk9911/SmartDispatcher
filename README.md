# Forecast Regret POC

**Forecast regret** is the extra fuel, time and CO₂ a flight burns because its plan was made on a forecast instead of the truth. It is measured against the hindsight plan, the best plan for the weather that actually happened.
This POC plans 120 transatlantic crossings (JFK↔LHR, Jan–Feb 2020, B789) on IFS HRES, GraphCast, Pangu-Weather and a persistence baseline at 12–120 h lead time, flies each plan through ERA5 truth, and reports the regret.
Everything is reproducible from the commands below and ends in one self-contained HTML report.

## Headline

At 120 h lead time, GraphCast costs **160 kg** of fuel per crossing (90% CI 124–202 kg) and Pangu-Weather 172 kg (139–208 kg), against **294 kg** (229–367 kg) for IFS HRES. At 12–72 h the three forecast sources are statistically tied (their CIs overlap). The persistence baseline is far worse, about 100× at short lead times (526 kg at 12 h vs 6 kg for HRES).

Means over 120 flights, directions pooled, bootstrap 90% CI.

## How to run

```
brew install uv
uv sync
uv run regret fetch      # WeatherBench 2 stores (network)
uv run regret compute    # plans and regret -> data/results/regret.parquet
uv run regret report     # -> reports/report.html
```

Optional stretch, not part of the five commands above: the geostrophic balance figure (section 6 of the report).

```
uv run regret fetch --with geopotential   # optional: adds 250 hPa geopotential (network)
uv run regret geostrophic                 # optional: -> data/results/geostrophic.parquet
```

Optional NeuralGCM add-on (sections 7 and 8), a reduced method: the flights with a NeuralGCM initialisation at every lead, and 12-hourly planning for all five sources. It does not change the core results. Run these in order:

```
uv run regret fetch --with neuralgcm,neuralgcm_ens   # optional: NeuralGCM deterministic and ensemble (network, large)
uv run regret neuralgcm                              # optional: -> data/results/neuralgcm_regret.parquet
uv run regret ensemble                               # optional, after the add-on: -> data/results/ensemble_regret.parquet
```

Run `uv run regret report` again afterwards. Without a result file the report shows a short note in its place.

`uv run pytest` runs the test suite. The report lands in `reports/report.html` (not committed) and opens from `file://` with no network.

## What's in the report

1. **Headline table**: mean (90% CI), median and p90 regret per forecast source and lead time.
2. **Showcase flight**: JFK→LHR on 2020-02-09 on a map, with the jet, each forecast source's plan and the hindsight plan.
3. **Regret vs lead time**: how regret grows with lead time, per forecast source.
4. **Wind error vs fuel regret**: per-plan wind error against regret.
5. **Sanity panel**: checks that the truth-optimised plans are physically plausible.
6. **Geostrophic balance at 250 hPa** (optional stretch): the ageostrophic fraction of each forecast source against ERA5, shown only when the optional commands above have been run.
7. **NeuralGCM add-on: 5-source comparison** (optional): mean fuel regret by lead for five sources on the matched flights with 12-hourly planning, with a note on how much 12-hourly planning alone adds. Shown only when `regret neuralgcm` has been run.
8. **Ensemble robust plan** (optional): the mean- and p90-robust plans chosen across NeuralGCM ensemble members, against the deterministic sources. Shown only when `regret ensemble` has been run.

The "Assumptions and limitations" section lists the eight modelling assumptions (fixed FL350 and Mach 0.85, cruise only, 1.5° grid, and so on). Read it before quoting any number.

One fact the full run revealed: 11 of the 60 westbound hindsight plans burn slightly over 50 t (max 51.3 t). The 25–50 t sanity range applies only to the fixture day.

## Pointers

- [SPEC.md](./SPEC.md): scope and definition of done
- [CONTEXT.md](./CONTEXT.md): the project's terms (plan, truth, hindsight plan, regret, forecast source, lead time)
- [docs/adr/](./docs/adr/): recorded decisions
