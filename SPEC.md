# SPEC: Forecast Regret POC

How much does weather-forecast quality cost a transatlantic flight? This proof-of-concept plans flights on several forecast sources, flies each plan through the truth, and reports the **regret**: the extra fuel, time and CO₂ each forecast costs compared with the hindsight plan.

It is a proof of concept for evaluating how weather-forecast quality affects flight planning, not a production system. Terms in **bold** are defined in [`CONTEXT.md`](./CONTEXT.md); key decisions are in [`docs/adr/`](./docs/adr/).

---

## 1. Scope

### 1.1 In scope

| Item | Value |
|---|---|
| Flights | JFK→LHR departing **00:00 UTC** and LHR→JFK departing **12:00 UTC**, every day |
| Date range | **2020-01-01 → 2020-02-29** (60 days, 120 flights) |
| Showcase flight | JFK→LHR departing 2020-02-09 00:00 UTC (record strong-jet night) |
| Aircraft | **B789** (OpenAP model) |
| Flight profile | Cruise only, fixed **FL350 (250 hPa)**, fixed **Mach 0.85**, initial mass **85% of MTOW**, same for every plan. No climb/descent; endpoints are the airport coordinates |
| Forecast sources (core) | **IFS HRES**, **GraphCast**, **Pangu-Weather**, **Persistence baseline** |
| Forecast sources (optional) | NeuralGCM deterministic, as an opt-in add-on analysis with a reduced method (§1.5); it does not join the core candidate set |
| Truth | ERA5 |
| Lead times | **12, 24, 48, 72, 120 h** (from forecast initialisation to departure) |
| Weather grid | WeatherBench 2 **1.5° (240×121)** stores for every source and the truth ([ADR 0002](./docs/adr/0002-weatherbench2-1p5-degree-grid.md)) |
| Sample size | 120 flights × 5 leads × 4 sources = **2,400 forecast plans** + 120 truth-optimised plans |

### 1.2 Metrics

**In:**
- Regret in **fuel (kg and % of trip fuel)**, **time (min)** and **CO₂ (kg)**, per plan.
- Aggregates by source × lead × direction (and pooled over direction): mean, median, p90. Means carry a **bootstrap 90% CI** (resample flights, 2,000 resamples, fixed seed).
- Share of flights where a given forecast plan *is* the hindsight plan, and the **zero-regret share**: flights where its regret is exactly 0, ties with the hindsight plan included.
- Optimiser-gap count and size.
- **Wind error** per plan (RMS vector wind difference at 250 hPa along the hindsight plan's path and times).

**Out:** cost in money / cost index, contrails and other non-CO₂ effects, NOx, ATC, North Atlantic Tracks, airspace and ETOPS constraints, in-flight re-planning, fuel uplift and reserves, climb/descent, step climbs, temperature effects on TAS, turbulence.

### 1.3 Stretch goals (in order)

1. **Ensemble robust plan choice** using the **NeuralGCM ensemble** (50 members, 250 hPa, 2020). Plan on each member, replay each member's plan through every other member, choose the plan with the lowest mean (and lowest p90) cost across members, then replay the chosen plan through the truth and report its regret alongside the deterministic sources. Reduced method (§1.5): the same 110 matched flights and 12-hourly planning as the NeuralGCM add-on, and a member count M ≤ 50 chosen from measured cost. The report states plainly that the IFS ensemble and GenCast are not used because WeatherBench 2 stores them only at 500/700/850 hPa.
2. **Geostrophic-balance check**: the **ageostrophic fraction** |V − V_g| / |V| at 250 hPa over 30–70°N, with V_g from geopotential on an f-plane per grid point, per source vs ERA5, by lead time. One chart.

### 1.4 Explicitly out of scope

Web app, backend, login, database, mobile, native desktop apps, CI, GFS (not in WeatherBench 2), the IFS ensemble (no 250 hPa in WeatherBench 2), 0.25° data, OpenAP-TOP as the planner ([ADR 0001](./docs/adr/0001-own-grid-planner-not-openap-top.md)).


### 1.5 Reduced method for NeuralGCM (user-approved 2026-10-02)

The WeatherBench 2 NeuralGCM stores (deterministic and ensemble) start at 2020-01-01 00 UTC and have 12-hourly prediction steps, so they cannot meet §3.2 and §4.1 as written. They are evaluated in an **opt-in add-on**, separate from the core experiment:

- **Matched flights:** only flights with a NeuralGCM initialisation at every lead (110 of 120; 2020-01-06 onwards).
- **Matched time resolution:** in the add-on, **every** forecast source is planned from the steps at `lead` and `lead + 12` h only, interpolated linearly in time; replay stays through 6-hourly ERA5.
- **Candidates:** within the add-on, the truth-optimised plan plus all five forecast sources; regret is recomputed for every source on that subset (regret ≥ 0 holds).
- **Separate results and figures:** the add-on is labelled "5-source comparison on 110 flights, 12-hourly planning", with a sensitivity line (core sources' mean regret at 6-hourly vs 12-hourly planning on the same flights). The core experiment, its results, the five commands and the README headline are unchanged.
- **Ensemble (stretch 1):** on the same subset and resolution, with M members chosen from measured cost; the robust plans' regret is floored against the add-on hindsight plan, and how often they beat it is reported.

---

## 2. Platform

- **Python 3.12**, pinned in `.python-version`, managed with **uv** (`brew install uv`), dependencies locked in `uv.lock`.
- The analysis runs as a **JupyterLab** notebook (`.ipynb`) in a desktop browser.
- The deliverable is a **single self-contained `report.html`** exported with `nbconvert --no-input`, with Plotly figures and plotly.js embedded inline. It must open from `file://` with **no network access**.
- Supported: **current desktop Chrome**, verified automatically (§6.5). Firefox, mobile and native apps are out of scope.
- No CI; everything runs locally.

---

## 3. Data

### 3.1 Sources (WeatherBench 2, public GCS bucket `gs://weatherbench2`, anonymous access)

All at 1.5° (`240x121_equiangular_with_poles_conservative`):

| Role | Store |
|---|---|
| Truth (ERA5) | `datasets/era5/1959-2022-6h-240x121_equiangular_with_poles_conservative.zarr` |
| IFS HRES | `datasets/hres/2016-2022-0012-240x121_equiangular_with_poles_conservative.zarr` |
| GraphCast | `datasets/graphcast/2020/date_range_2019-11-16_2021-02-01_12_hours-240x121_equiangular_with_poles_conservative.zarr` |
| Pangu-Weather | `datasets/pangu/2018-2022_0012_240x121_equiangular_with_poles_conservative.zarr` |
| NeuralGCM (optional) | `datasets/neuralgcm_deterministic/2020-240x121_equiangular_with_poles_conservative.zarr` |
| NeuralGCM ensemble (stretch) | `datasets/neuralgcm_ens/2020-240x121_equiangular_with_poles_conservative.zarr` |
| Persistence baseline | Derived from ERA5: the truth at the forecast's initialisation time, held constant |

Store paths and level availability were checked against the 0.25° siblings, then confirmed on the 1.5° stores on 2026-10-01 (T8): 250 hPa is present in ERA5, IFS HRES, GraphCast and Pangu-Weather, and every needed initialisation and lead exists. The fetch step **asserts** that 250 hPa, the needed init times and the needed lead times exist in each 1.5° store, and fails loudly if not.

### 3.2 Variables and subsetting

- Variables: `u_component_of_wind`, `v_component_of_wind` at **250 hPa**; `geopotential` at 250 hPa only if the geostrophic stretch goal is in play.
- Box: **25–75°N, 100°W–20°E** (all flights and grid corridors must fit inside; asserted).
- Times: forecast inits at 00 and 12 UTC such that init + lead = departure, for every flight and lead; prediction steps covering **lead … lead + 12 h** (flight ≈ 6–8 h plus margin) at 6-hourly resolution.
- ERA5: 6-hourly from **2019-12-27 00 UTC** to 2020-03-01 12 UTC. The start is the first departure minus the longest lead (120 h), so the persistence baseline exists at every lead.
- Longitudes are normalised to −180…180 and latitudes sorted ascending on load, whatever the source's convention.

### 3.3 Caching

- `uv run regret fetch` is the **only** step that touches the network. It writes one zarr per source to `data/cache/<source>.zarr` (gitignored) and is idempotent (skips what is already cached).
- All other steps read only from the cache.
- Expected cache size: a few hundred MB at most.
- Small test fixtures (< 5 MB total for the core sources, < 10 MB once the optional NeuralGCM source is added; flights 2020-02-08 → 2020-02-10, ERA5 from 2020-02-03 00 UTC to 2020-02-11 12 UTC for the same reason, all core sources, the box above) are committed in `tests/fixtures/` and built by `uv run regret fetch --fixture`.

---

## 4. Method

### 4.1 Winds along the flight

Winds vary in space **and** time along the flight: bilinear in latitude/longitude, linear in time between 6-hourly steps. A forecast source's plan uses one initialisation, stepping through its prediction steps as the flight progresses. Wind sign convention: **u > 0 blows toward the east, v > 0 toward the north**, in m/s.

### 4.2 Planner ([ADR 0001](./docs/adr/0001-own-grid-planner-not-openap-top.md))

- Lateral grid aligned with the great circle between the two airports: **25 columns** along track × **41 cross-track offsets** spaced 60 km (±1,200 km). The first and last columns collapse to the airports.
- Between adjacent columns a plan may shift by at most ±3 offsets (bounds turn angle).
- Edge time: segment length ÷ ground speed, where ground speed comes from the wind triangle at constant TAS (M0.85 at FL350, ISA): GS = √(TAS² − W_cross²) + W_along, with the wind sampled at the segment midpoint at the estimated passing time.
- Dynamic programming column by column, keeping the **earliest arrival** at each node (winds are treated as first-in-first-out, so this is exact on the grid). Objective: **minimum flight time**.
- Because TAS and flight level are fixed and ISA is assumed, fuel burn depends only on flight time (mass evolves by the same equation whatever the path), so the minimum-time plan is also the minimum-fuel and minimum-CO₂ plan. This makes the three regret measures consistent.
- Target: ≤ 1 s per plan.

### 4.3 Replay

Fly a plan's fixed lateral path, at FL350 and M0.85, through the **truth**, from the fixed departure time and initial mass. Integrate in steps of about 10 km: wind from §4.1, ground speed from the wind triangle, fuel flow from OpenAP `FuelFlow("B789")` for cruise at the current mass, mass decreasing as fuel burns. Output: flight time, trip fuel, **CO₂ = 3.16 × fuel**. Replay is deterministic.

### 4.4 Regret

For each flight:

1. Candidates = the **truth-optimised plan** + every forecast plan (all sources × all leads).
2. Replay every candidate through the truth.
3. **Hindsight plan** = the candidate with the lowest replayed cost. A tie goes to the truth-optimised plan, then to the earlier forecast source in the configured order, then to the shorter lead, so there is exactly one per flight.
4. **Regret** of a plan = its replayed cost − the hindsight plan's replayed cost, for fuel, time and CO₂ separately. Zero or positive by definition.
5. If the hindsight plan is a forecast plan rather than the truth-optimised plan (strictly lower cost), record an **optimiser gap** (size = truth-optimised cost − hindsight cost).

### 4.5 Wind error

For each forecast plan: the RMS of |V_forecast − V_truth| at 250 hPa, sampled every ~10 km along the **hindsight plan's** path at the times the hindsight plan's replay passes each point. Same path for every source on a flight, so wind errors are comparable.

---

## 5. Deliverables and layout

```
pyproject.toml, uv.lock, .python-version
src/regret/
    config.py      # full vs fixture config (REGRET_CONFIG=full|fixture)
    fetch.py       # WeatherBench 2 → data/cache
    winds.py       # loading, normalisation, space-time interpolation
    planner.py     # grid + dynamic programming
    replay.py      # truth replay with OpenAP fuel
    regret.py      # candidates, hindsight plan, regret, optimiser gap, wind error
    stats.py       # aggregates and bootstrap CIs
    cli.py         # `regret fetch | compute | report`
notebooks/regret_report.ipynb
data/cache/        # gitignored
data/results/regret.parquet   # one row per plan (gitignored)
reports/report.html           # generated
tests/ + tests/fixtures/
```

### 5.1 Commands

- `uv run regret fetch` – download and cache (only networked step).
- `uv run regret compute` – run the full experiment → `data/results/regret.parquet`. Target **< 30 min** on a laptop, hard limit **45 min**; plans may run in parallel processes, with results identical to a single-process run. Never reduce the planner grid, the replay step, the sample or the bootstrap to meet the time.
- `uv run regret report` – execute the notebook and export `reports/report.html`.

### 5.2 Notebook and report contents (in order)

1. **Headline table**: mean (with 90% CI), median and p90 regret in fuel (kg, % of trip fuel), time (min), CO₂ (kg), by source × lead, directions pooled.
2. **Showcase map**: every source's plan (at a lead chosen from a dropdown in the figure) and the hindsight plan for the showcase flight, over ERA5 250 hPa wind speed, with a slider to show each source's forecast wind field at the chosen lead instead.
3. **Regret vs lead time**: one line per source, split eastbound / westbound.
4. **Wind error vs fuel regret** scatter, coloured by source.
5. **Sanity panel**: eastbound vs westbound replay times, fuel-flow distribution, optimiser-gap frequency.
6. **Method, assumptions and limitations** (§7) as text.

Items 1–4 are the core. The notebook reads all aggregate results from `regret.parquet`; live, it re-plans and replays **only the showcase flight**, at all 5 leads (under a minute), and must run offline from the cache in **< 2 min**.

---

## 6. Testing

All tests run with `uv run pytest`, **offline**, in **< 3 min**, using `tests/fixtures/`.

### 6.1 Units and conventions
- Knots ↔ m/s and Mach ↔ TAS (ISA, FL350) round-trip.
- Wind sign: a synthetic field with u > 0 slows a westbound segment and speeds an eastbound one.
- Latitude order: N→S and S→N inputs give identical interpolated winds.
- Longitude: 0…360 inputs are normalised to −180…180 and give identical winds.

### 6.2 Planner
- **Zero wind**: path lies on the great circle to within one grid cell; time = distance ÷ TAS within 1%.
- **Uniform 50 m/s westerly**: eastbound time < still-air time < westbound time.
- **Determinism**: same inputs → identical plan.

### 6.3 Physics sanity on real data (fixture, 2020-02-09)
- ERA5 truth-optimised eastbound flight is **≥ 45 min faster** than the westbound one.
- B789 fuel flow always within **4,000–8,000 kg/h**; trip fuel within **25–50 t**.
- CO₂ = 3.16 × fuel exactly.

### 6.4 Regret
- Regret ≥ 0 for every plan, in fuel, time and CO₂.
- The hindsight plan has regret exactly 0; exactly one hindsight plan per flight.
- Ordering by fuel, time and CO₂ is identical for every flight (§4.2 property).
- Replay is deterministic (same plan + same winds → same cost).
- Persistence baseline's mean fuel regret at 120 h is ≥ that of HRES (soft check, fixture only, marked as such).

### 6.5 Fetch, end-to-end, browser
- **Fetch** is tested against a small local zarr, never the live network: subsetting, normalisation, the 250 hPa / init / lead assertions.
- **End-to-end**: `pytest --nbmake` runs `notebooks/regret_report.ipynb` with `REGRET_CONFIG=fixture`; it must finish without errors. Then `nbconvert --no-input` regenerates `reports/report.html`.
- **Report in the browser** (pytest-playwright, Chrome via `channel="chrome"`): opening `report.html` from `file://` must give
  - zero console errors,
  - all 5 figures present (`.js-plotly-plot`) each with a rendered plot SVG,
  - zero requests to anything other than `file://`/`data:` (captured via request listener).
- The Playwright MCP is used only for manual checks during development, not in the test suite. It blocks `file://`, so those checks load the report from a local static server.

---

## 7. Assumptions and known limitations (stated in the report)

- Cruise only at fixed FL350 and M0.85; no climb, descent or step climbs.
- No ATC, North Atlantic Tracks, airspace or ETOPS constraints.
- OpenAP fuel models are accurate to roughly ±5–10%; regret is a difference, so most bias cancels.
- Winds at 1.5° under-resolve the jet core; ERA5 is treated as truth but is itself a model.
- Small sample: 2 months, 1 city pair, 1 aircraft. Results show spread, not significance; CIs are given.
- ISA temperature (no temperature effect on TAS); no turbulence.
- Hindsight plan is the best of the candidates, so the planner's grid limits what "best" means.
- The IFS ensemble is unused (no 250 hPa in WeatherBench 2); GFS is not in WeatherBench 2.

---

## 8. Definition of done

1. From a clean clone: `brew install uv && uv sync && uv run regret fetch && uv run regret compute && uv run regret report` succeeds.
2. Full Jan–Feb 2020 experiment computed for HRES, GraphCast, Pangu and persistence at all 5 leads.
3. `reports/report.html` generated, self-contained, with core charts (§5.2 items 1–4) and limitations.
4. Test suite green, including nbmake and Playwright in Chrome.
5. README: 3-line summary, how to run, and the headline number (e.g. "GraphCast at 24 h costs X kg of fuel per crossing vs HRES").
6. `SPEC.md`, `CONTEXT.md` and ADRs committed.

## 9. Cut order (if time runs short, first cut first)

1. Stretch goals (geostrophic first, then ensemble).
2. NeuralGCM deterministic.
3. Wind-field slider on the showcase map (keep a static ERA5 background).
4. Lead times 48 and 120 h (keep 12 / 24 / 72).
5. February (keep January, but keep 2020-02-09 as the showcase day).

**Never cut:** regret ≥ 0 invariant, persistence baseline, physics sanity tests, nbmake end-to-end run, limitations section.

## 10. Change log

- **2026-10-01** (approved by the user during the plan review):
  - Chrome only; Firefox dropped (§2, §6.5, §8, §9).
  - ERA5 window starts 2019-12-27, fixture ERA5 starts 2020-02-03 (§3.2, §3.3).
  - Compute hard limit of 45 min, parallel runs allowed, fidelity never reduced (§5.1).
  - Tie rule and zero-regret share (§1.2, §4.4).
  - Lead dropdown on the showcase map (§5.2).
  - Fixture limit rises to < 10 MB once NeuralGCM is added; core fixtures stay < 5 MB and lossless (§3.3).
- **2026-10-02** (approved by the user: "for the blocked tasks, go ahead with a reduced method"):
  - NeuralGCM deterministic and the ensemble robust plan run as an opt-in add-on with the reduced method in §1.5 (matched 110 flights, 12-hourly planning for all sources, separate results). The core experiment is unchanged.
