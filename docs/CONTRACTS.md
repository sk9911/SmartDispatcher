# CONTRACTS: shared interfaces

Every builder implements against this file. Vocabulary follows [`CONTEXT.md`](../CONTEXT.md); scope follows [`SPEC.md`](../SPEC.md); task order follows [`PLAN.md`](../PLAN.md). Changing a contract here means messaging the affected builder first (CLAUDE.md).

Conventions used everywhere:

- Python 3.12, `from __future__ import annotations`, package `regret` under `src/regret/`.
- **Units:** latitude/longitude in degrees (`_deg`), speeds in m/s (`_ms`), distances in km (`_km`), time in minutes (`_min`) or hours (`_h`), mass in kg, fuel flow in kg/h (`_kgh`). A unit suffix is part of every field and column name.
- **Time:** timezone-naive UTC. Scalars are `datetime.datetime`; arrays and parquet columns are `numpy.datetime64[ns]`.
- **Wind sign:** `u > 0` blows toward the east, `v > 0` toward the north.
- **Coordinates:** latitude ascending, longitude in −180…180 ascending (SPEC §3.2).
- **Dataclasses:** all `@dataclass(frozen=True)`, defined in `src/regret/types.py` unless stated. Collections are tuples; per-point arrays (`ReplayResult`) are `numpy.ndarray` and the dataclass sets `eq=False`.
- **Logging:** `logging` at INFO to stderr. Timed commands log `elapsed_s=<float>`; `fetch` also logs `<n> downloads`.

---

## 1. Types (`regret/types.py`, T3)

Constants: `TRUTH_SOURCE = "truth"`, `TRUTH_LEAD_H = 0`. `SourceName = str`: a forecast source's name; equal to its dataset name in `Config.datasets`, or `"persistence"`; `"truth"` is reserved for the truth-optimised plan.

| Type | Fields (name: type), in this order |
|---|---|
| `Airport` | `code: str` (IATA), `lat_deg: float`, `lon_deg: float` |
| `Leg` | `origin: Airport`, `destination: Airport`, `departure_hour_utc: int` |
| `Flight` | `flight_id: str`, `origin: Airport`, `destination: Airport`, `departure_time: datetime`, `direction: str` (`"eastbound"` or `"westbound"`) |
| `Plan` | `flight_id: str`, `source: SourceName`, `lead_h: int`, `lat_deg: tuple[float, ...]`, `lon_deg: tuple[float, ...]`, `planned_time_min: float` |
| `ReplayResult` | `flight_id: str`, `source: SourceName`, `lead_h: int`, `lat_deg: ndarray[float64] (n,)`, `lon_deg: ndarray[float64] (n,)`, `time: ndarray[datetime64[ns]] (n,)`, `time_min: float`, `fuel_kg: float`, `co2_kg: float`, `fuel_flow_min_kgh: float`, `fuel_flow_max_kgh: float` |
| `Box` | `lat_min_deg`, `lat_max_deg`, `lon_min_deg`, `lon_max_deg`: all `float` |
| `Dataset` | `name: str`, `store: str`, `variables: tuple[str, ...]`, `fetch_by_default: bool`, `kind: str` (`"truth"`, `"forecast"`, `"ensemble"` or `"extra"`), `derived_from: tuple[str, ...]` |
| `Config` | `mode: str` (`"full"` or `"fixture"`), `datasets: tuple[Dataset, ...]`, `sources: tuple[SourceName, ...]`, `leads_h: tuple[int, ...]`, `box: Box`, `legs: tuple[Leg, ...]`, `first_departure_date: date`, `last_departure_date: date`, `showcase_departure: datetime`, `era5_start: datetime`, `era5_end: datetime`, `cache_dir: Path`, `results_path: Path`, `report_path: Path`, `workers: int` |

Rules:

- `Flight.flight_id` = `f"{origin.code}-{destination.code}-{departure_time:%Y%m%dT%H%M}"` (e.g. `JFK-LHR-20200209T0000`). `direction` is `"eastbound"` when the destination's longitude is east of the origin's.
- `make_flight(origin: Airport, destination: Airport, departure_time: datetime) -> Flight` (in `types.py`) applies the `flight_id` and `direction` rules above. Every `Flight` must be built with it: `config.flights`, `config.showcase_flight` and tests never construct `Flight` directly.
- `Airport` values (constants `JFK`, `LHR` in `types.py`): JFK 40.6398 °N, −73.7789 °E; LHR 51.4700 °N, −0.4543 °E.
- `Plan.lat_deg`/`lon_deg` are the **25 waypoints** of the planner's grid columns, from the origin airport (first) to the destination airport (last). Consecutive waypoints are joined by great-circle segments. The truth-optimised plan has `source == TRUTH_SOURCE` and `lead_h == TRUTH_LEAD_H`. `planned_time_min` is the flight time the planner predicted with its own winds.
- `ReplayResult` holds one point per integration step (≤ ~10 km apart), the first at departure and the last at arrival; `time[0] == flight.departure_time`; `time_min == (time[-1] - time[0])` in minutes. `co2_kg == 3.16 * fuel_kg` exactly. A `ReplayResult` carries the `source` and `lead_h` of the plan it replays.
- `Config.legs` for both modes: JFK→LHR at hour 0 and LHR→JFK at hour 12. `Config.sources` order is the tie-break order (§3). `Config.workers` is `REGRET_WORKERS` or the CPU count.
- `Dataset.store` is a path relative to `gs://weatherbench2/` (full URL via `config.store_url(dataset)`; a value containing `://` or starting with `/` is used as given, so tests can point at local zarrs). `Dataset.derived_from` is non-empty only for `geopotential` (`("era5", "hres", "graphcast", "pangu")`); it has no store of its own.

### 1.1 Dataset registry (`config.py`, T4)

| `name` | `kind` | `store` | `variables` | `fetch_by_default` |
|---|---|---|---|---|
| `era5` | truth | `datasets/era5/1959-2022-6h-240x121_equiangular_with_poles_conservative.zarr` | `u_component_of_wind`, `v_component_of_wind` | yes |
| `hres` | forecast | `datasets/hres/2016-2022-0012-240x121_equiangular_with_poles_conservative.zarr` | same | yes |
| `graphcast` | forecast | `datasets/graphcast/2020/date_range_2019-11-16_2021-02-01_12_hours-240x121_equiangular_with_poles_conservative.zarr` | same | yes |
| `pangu` | forecast | `datasets/pangu/2018-2022_0012_240x121_equiangular_with_poles_conservative.zarr` | same | yes |
| `neuralgcm` | forecast | `datasets/neuralgcm_deterministic/2020-240x121_equiangular_with_poles_conservative.zarr` | same | **no** |
| `neuralgcm_ens` | ensemble | `datasets/neuralgcm_ens/2020-240x121_equiangular_with_poles_conservative.zarr` | same; `member` dimension kept | **no** |
| `geopotential` | extra | `""` (uses the four stores above) | `geopotential` | **no** |

`persistence` is not a dataset: it is derived from `era5`. `Config.sources` lists forecast sources only: `("hres", "graphcast", "pangu", "persistence")`.

**NeuralGCM add-on (done, SPEC §1.5).** Both NeuralGCM stores start at 2020-01-01 00 UTC and hold only 12-hourly `prediction_timedelta`, so they cannot meet the core rules (SPEC §3.2, §4.1). They are evaluated in an **opt-in add-on** with a reduced method (§2.14). `neuralgcm` and `neuralgcm_ens` stay in the registry (`fetch_by_default` false); **neither is in `Config.sources`**, so the core results, the five core commands and the core candidate set are unchanged. `neuralgcm` has a colour and symbol in `style` (§6.1).

The per-dataset **step resolution** and **first initialisation** are not `Dataset` fields (`Dataset` is a §1 type); they live in two mappings in `config.py`, read through the functions in §2.2:

| `name` | `step_h` (h) | `first_init` |
|---|---|---|
| `neuralgcm`, `neuralgcm_ens` | 12 | 2020-01-01 00:00 (`NEURALGCM_FIRST_INIT`) |
| every other dataset | 6 (`CORE_STEP_H`) | `None`: the store covers every needed init |

The **matched flights** of a dataset with a first init are the flights whose init exists at every lead, `departure_time − max(leads_h) ≥ first_init` (110 of 120 in the full config, from 2020-01-06; 6 in the fixture config).

### 1.2 Config modes (`config.py`)

| Field | full | fixture |
|---|---|---|
| `first_departure_date` / `last_departure_date` | 2020-01-01 / 2020-02-29 | 2020-02-08 / 2020-02-10 |
| `era5_start` / `era5_end` | 2019-12-27 00:00 / 2020-03-01 12:00 | 2020-02-03 00:00 / 2020-02-11 12:00 |
| `leads_h` | `(12, 24, 48, 72, 120)` | same |
| `box` | 25–75 °N, −100…20 °E | same |
| `showcase_departure` | 2020-02-09 00:00 | same |
| `cache_dir` | `data/cache` | `tests/fixtures` |
| `results_path` | `data/results/regret.parquet` | `tests/fixture_results/regret.parquet` |
| `report_path` | `reports/report.html` | `reports/report-fixture.html` |

---

## 2. Module signatures

Every module below lives in `src/regret/<name>.py`. A module that implements a CLI command exposes `main(argv: Sequence[str] | None = None) -> int` (exit code; `None` means `sys.argv[1:]`).

### 2.1 CLI convention

`regret <cmd> [args]` (T1's `cli.py`) imports `regret.<cmd>` with `importlib`, calls `main(args)` and exits with its return value. **The module name is the command.** Reserved commands, as `cli.COMMANDS`: `fetch`, `compute`, `report`, `ensemble`, `geostrophic`, `neuralgcm` (the last three are opt-in). If the module is missing, `cli.py` exits 2 with a message naming it. Modules never edit `cli.py`.

Environment: `REGRET_CONFIG` = `full` (default) or `fixture`; `REGRET_WORKERS` = worker count; `REGRET_BLOCK_NETWORK=1` installs the offline guard.

### 2.2 `config` (T4)

```python
FULL: Config; FIXTURE: Config
def get_config(mode: str | None = None) -> Config        # mode None -> REGRET_CONFIG, default "full"
def store_url(dataset: Dataset) -> str
def cache_path(cfg: Config, name: str) -> Path           # cfg.cache_dir / f"{name}.zarr"
def flights(cfg: Config) -> tuple[Flight, ...]           # sorted by departure_time, then direction
def showcase_flight(cfg: Config) -> Flight               # JFK->LHR at cfg.showcase_departure
def step_h(name: str) -> int                             # prediction-step resolution, h: 12 for NeuralGCM, else 6
def first_init(name: str) -> datetime | None             # earliest init in the store; None = covers every needed init
def matched_flights(cfg: Config, name: str) -> tuple[Flight, ...]
    # flights with an init at every lead (§1.1); all of flights(cfg) when first_init(name) is None
    # NeuralGCM: 110 in full, 6 in fixture; same sort order as flights()
```

Tests make variants with `dataclasses.replace(cfg, cache_dir=tmp_path)`.

### 2.3 `units` (T5)

```python
FLIGHT_LEVEL = 350; PRESSURE_HPA = 250; MACH = 0.85; MASS_FRACTION = 0.85
CO2_PER_FUEL = 3.16; AIRCRAFT = "B789"; EARTH_RADIUS_KM = 6371.0088
def knots_to_ms(kt): ...        def ms_to_knots(ms): ...
def mach_to_tas(mach: float, flight_level: int = FLIGHT_LEVEL) -> float   # m/s, ISA
def tas_to_mach(tas_ms: float, flight_level: int = FLIGHT_LEVEL) -> float
TAS_MS: float                                              # mach_to_tas(MACH)
def great_circle_km(lat1, lon1, lat2, lon2) -> ndarray     # vectorised, degrees in
def initial_bearing_deg(lat1, lon1, lat2, lon2) -> ndarray
def destination_point(lat, lon, bearing_deg, distance_km) -> tuple[ndarray, ndarray]
```

Functions accept floats or numpy arrays and return the same kind. The great-circle helpers live here so `planner` and `replay` share them.

### 2.4 `winds` (T6)

`WindField` (in `types.py`) is a `typing.Protocol`:

```python
class WindField(Protocol):
    def uv(self, lat: ArrayLike, lon: ArrayLike, time: ArrayLike) -> tuple[np.ndarray, np.ndarray]: ...
```

`lat`, `lon` in degrees (lon −180…180), `time` as `datetime64[ns]`; any mix of scalars and arrays that numpy broadcasts. **Vectorised:** returns `(u, v)` as float64 arrays of the broadcast shape, in m/s. A point outside the field's box or time range raises `ValueError`. Bilinear in latitude/longitude, linear in time.

```python
class GridWind:                                            # implements WindField
    def __init__(self, u: ndarray, v: ndarray, lat: ndarray, lon: ndarray, time: ndarray): ...
        # u, v: float (time, lat, lon) in m/s; any lat order and 0..360 or -180..180 lon are normalised
def from_dataset(ds: xr.Dataset, *, time: xr.DataArray | None = None) -> GridWind
    # ds has u_component_of_wind, v_component_of_wind with dims (time, latitude, longitude);
    # `time` overrides the time axis (used for forecasts: valid time = init + prediction_timedelta)
def normalise(ds: xr.Dataset) -> xr.Dataset                # lat ascending, lon -180..180 sorted
class UniformWind:  def __init__(self, u_ms: float, v_ms: float)       # for tests
class OffsetWind:   def __init__(self, base: WindField, du_ms: float, dv_ms: float)
class FrozenWind:   def __init__(self, base: WindField, at: datetime64)  # base sampled at `at` for every time
```

### 2.5 `fetch` (T7)

```python
class MissingDataError(Exception): ...                     # message names the store and the level/init/step
class FetchReport: downloads: int; elapsed_s: float; datasets: tuple[str, ...]   # frozen dataclass
GCS_BUCKET = "gs://weatherbench2"
def fetch(cfg: Config, names: Sequence[str] | None = None, *,
          open_store: Callable[[str], xr.Dataset] | None = None) -> FetchReport
def main(argv=None) -> int
```

- `names=None` fetches every dataset with `fetch_by_default`. `main` accepts `--with a,b` (extra dataset names, added to the defaults) and `--fixture` (use `get_config("fixture")`, writing to `tests/fixtures/`).
- `open_store` receives `config.store_url(dataset)`; default opens the zarr anonymously. Tests inject a fake and count its reads.
- Output per dataset is `cache_path(cfg, name)`, normalised (§1 conventions), 250 hPa selected (`level` dropped to a scalar coord), subset to `cfg.box`. Variables `u_component_of_wind`, `v_component_of_wind` (and `geopotential` for `geopotential_<source>`).
  - `era5`: dims `(time, latitude, longitude)`, `cfg.era5_start … cfg.era5_end`.
  - forecasts: dims `(time, prediction_timedelta, latitude, longitude)`; `time` is the initialisation. Only the inits that satisfy init + lead = departure for every flight × lead, and `prediction_timedelta` covering lead … lead + 12 h.
  - `neuralgcm_ens`: same plus `member`.
  - `geopotential`: one store per derived dataset, `geopotential_<source>.zarr`, same shape as that source.
- **Add-on datasets.** `needed_pairs(cfg, name=None)` is `{(init, step)}` for the pairs some flight × lead reads. With `name=None` it is the core rule above, unchanged. With the name of a dataset that has its own `first_init` or `step_h` (`neuralgcm`, `neuralgcm_ens`), only `config.matched_flights(cfg, name)` count, and the steps are `lead … lead + 12 h` at `step_h(name)` (12 h: steps `lead` and `lead + 12`). Every other pair is masked to NaN, as for the core.
- **`realization` → `member`.** A store whose ensemble dimension is `realization` (the live NeuralGCM ensemble) is renamed to `member` on write; the cache and every reader see `member`.
- Idempotent: an existing complete cache is skipped (0 downloads). Missing 250 hPa, init or prediction step raises `MissingDataError`; so does a needed (init, step) pair that is not finite.

**Cache storage format** (B1, B2; the on-disk shape every reader relies on):

- `prediction_timedelta` is decoded from its `units` attribute (the live stores hold int64 hours, `units='hours'`) and stored as `timedelta64[ns]`. The store is opened with `decode_timedelta=False` and `_decode_steps` does the conversion; a missing or unsupported `units`, or values that are not whole units, raise `MissingDataError`.
- Dimension order is the contract order: `time, prediction_timedelta, member, latitude, longitude`, keeping only the dims a dataset has (`era5`: `time, latitude, longitude`).
- Forecast caches mask every (init, step) pair that no flight × lead needs to NaN, using the same rule as `sources.forecast_winds` (`fetch.needed_pairs(cfg)`: init = departure − lead, step = lead … lead + 12 h at 6 h). Readers never read a masked pair.
- **Chunks.** A dataset without a `member` dimension writes each variable as one chunk (`chunks = shape`). A dataset with `member` writes one chunk per member (`member` chunk size 1, every other dim whole), so reading one member decompresses only that member. Both use Blosc zstd (`clevel=9`, byte shuffle). The core fixtures total < 5 MB (SPEC §3.3) and stay lossless for every value the experiment reads.
- Completeness (`_is_complete`) checks variables, the expected times, inits and steps; it does not depend on chunking or compression, so a cache written with any encoding counts.

### 2.6 `sources` (T10)

```python
def forecast_winds(cfg: Config, source: SourceName, flight: Flight, lead_h: int, *,
                   step_h: int | None = None, member: int | None = None) -> WindField
def truth_winds(cfg: Config) -> WindField
class MissingForecastError(Exception): ...                 # cache, init or step missing; names source, init, path
```

- `truth_winds`: `GridWind` over the whole `era5` cache.
- `forecast_winds`: init = `flight.departure_time - lead_h`; reads `cache_path(cfg, source)`, selects that init, valid time = init + `prediction_timedelta`; covers departure … departure + 12 h. Any name in `cfg.sources` with a cache works with no code change.
- `"persistence"`: `FrozenWind(truth_winds(cfg), at=init)`: ERA5 at init, constant in time, including at lead 120 h for the first flight.
- **`step_h`:** `None` (default) uses the dataset's native steps, `lead … lead + 12 h`: the core behaviour, unchanged. `step_h=12` uses only the steps at `lead` and `lead + 12` h, linear in time between them, for **any** source (the add-on plans every source this way; replay stays through 6-hourly ERA5). Any other value raises `ValueError`. Persistence ignores `step_h` (it is constant in time).
- **`member`:** picks one member of an ensemble cache (a `member` dimension). Errors, all `ValueError` unless noted: an ensemble source without `member`; `member` given for a source with no `member` dimension; `member` given for `"persistence"`. A missing cache, an init not in the cache, or (with `step_h=12`) a missing `lead` or `lead + 12` step raises `MissingForecastError`.

### 2.7 `planner` (T11)

```python
N_COLUMNS = 25; N_OFFSETS = 41; OFFSET_SPACING_KM = 60.0; MAX_SHIFT = 3
def plan(wind: WindField, flight: Flight, *, source: SourceName, lead_h: int) -> Plan
def great_circle_path(flight: Flight, n: int = N_COLUMNS) -> tuple[np.ndarray, np.ndarray]   # lat, lon
```

Minimum flight time by dynamic programming (SPEC §4.2): fixed FL350, M0.85, ISA, wind from `wind.uv`, start at `flight.departure_time`. Deterministic. Truth-optimised plan: `source=TRUTH_SOURCE, lead_h=TRUTH_LEAD_H`.

### 2.8 `replay` (T12)

```python
STEP_KM = 10.0
def initial_mass_kg() -> float                              # MASS_FRACTION * OpenAP B789 MTOW
def replay(plan: Plan, flight: Flight, truth: WindField, *, step_km: float = STEP_KM) -> ReplayResult
```

Flies the plan's great-circle segments at FL350/M0.85 through `truth` from `flight.departure_time` (SPEC §4.3). Deterministic; result carries `plan.source` and `plan.lead_h`.

### 2.9 `regret` (T13)

```python
def select_hindsight(replays: Sequence[ReplayResult], source_order: Sequence[SourceName]) -> ReplayResult
def wind_error(forecast: WindField, truth: WindField, hindsight: ReplayResult) -> float   # m/s
def flight_table(flight: Flight, replays: Sequence[ReplayResult], source_order: Sequence[SourceName],
                 wind_errors: Mapping[tuple[SourceName, int], float] | None = None) -> pd.DataFrame
```

- `replays` holds the truth-optimised replay (`source == "truth"`) and every forecast replay of one flight. Selection follows the tie rule (§3).
- `wind_error`: `sqrt(mean(du² + dv²))` of `forecast.uv − truth.uv` at every point and time of `hindsight` (m/s).
- `flight_table` returns the rows of one flight with the §4 columns, in the §4 order. `wind_errors` is keyed by `(source, lead_h)`; missing keys give `NaN`; truth rows get `0.0`.

### 2.10 `stats` (T16)

```python
BOOTSTRAP_RESAMPLES = 2000; BOOTSTRAP_SEED = 20200209; CI_LEVEL = 0.90
def bootstrap_mean_ci(values: np.ndarray, *, resamples: int = BOOTSTRAP_RESAMPLES,
                      seed: int = BOOTSTRAP_SEED, level: float = CI_LEVEL) -> tuple[float, float]
def aggregate(df: pd.DataFrame, by: Sequence[str] = ("source", "lead_h")) -> pd.DataFrame
def hindsight_shares(df: pd.DataFrame, by: Sequence[str] = ("source", "lead_h")) -> pd.DataFrame
```

- `bootstrap_mean_ci`: one value per flight, flights resampled with `numpy.random.default_rng(seed)`; percentile interval (5th and 95th).
- `aggregate`: forecast-plan rows only (`is_truth_optimised == False`), grouped by `by` (`"direction"` may be added). Returns the `by` columns, `n`, and for each `m` in `fuel_kg`, `fuel_pct`, `time_min`, `co2_kg` (from `regret_<m>`): `<m>_mean`, `<m>_ci_lo`, `<m>_ci_hi`, `<m>_median`, `<m>_p90`; then `zero_regret_share`, `hindsight_share`, `optimiser_gap_count`, `optimiser_gap_mean_kg`. Sorted by source order of first appearance in `df`, then the other `by` columns.
- `hindsight_shares`: all rows including `"truth"`; columns `by` + `hindsight_share`; with `by=("source","lead_h")` the shares sum to 1 over all groups.
- Sources appear in the order of first appearance in `df` (`compute` writes them in `Config.sources` order).

### 2.11 `compute` (T15)

```python
def run(cfg: Config, *, flights: Sequence[Flight] | None = None,
        leads_h: Sequence[int] | None = None, workers: int | None = None) -> pd.DataFrame
def main(argv=None) -> int          # run(get_config()); writes cfg.results_path; logs elapsed_s
```

The unit of parallel work is one flight (`concurrent.futures.ProcessPoolExecutor`, `workers` defaults to `cfg.workers`). The result is identical for any worker count. Rows are sorted by `departure_time`, `direction`, truth-optimised row first, then source order in `cfg.sources`, then `lead_h`. Parquet via pyarrow, column order and dtypes as §4.

**Per-flight procedure** (normative; `compute` and `build_showcase_map` both follow it):

1. `truth = sources.truth_winds(cfg)`; truth-optimised plan = `planner.plan(truth, flight, source="truth", lead_h=0)`.
2. For every `source` in `cfg.sources` and `lead_h` in `cfg.leads_h`: `planner.plan(sources.forecast_winds(cfg, source, flight, lead_h), flight, source=source, lead_h=lead_h)`.
3. `replay.replay(plan, flight, truth)` for every plan.
4. `hindsight = regret.select_hindsight(replays, cfg.sources)`.
5. `wind_errors[(source, lead_h)] = regret.wind_error(forecast_winds, truth, hindsight)` for every forecast plan.
6. `regret.flight_table(flight, replays, cfg.sources, wind_errors)`.

### 2.12 `offline` (T1a)

```python
ENV_VAR = "REGRET_BLOCK_NETWORK"
class NetworkBlockedError(OSError): ...
def install() -> None                 # idempotent
def uninstall() -> None               # idempotent; restores the real socket functions
def is_installed() -> bool
def install_if_requested() -> None    # installs only when REGRET_BLOCK_NETWORK == "1"
```

After `install()`, a TCP connect to a non-loopback address raises `NetworkBlockedError`, and DNS lookups of non-local hosts are blocked. `127.0.0.1` and `AF_UNIX` sockets still work. `tests/conftest.py` sets `REGRET_CONFIG=fixture` unless already set, and installs the guard whenever `REGRET_BLOCK_NETWORK=1`.

### 2.13 `report` (T28a)

```python
DEFAULT_NOTEBOOK = Path("notebooks/regret_report.ipynb")
def export(cfg: Config, out_path: Path, *, notebook: Path | None = None) -> Path
def main(argv=None) -> int            # export(get_config(), get_config().report_path)
```

`export` executes the notebook (default `DEFAULT_NOTEBOOK`) with `REGRET_CONFIG=cfg.mode` set for the kernel (and `REGRET_BLOCK_NETWORK` passed through when set) and writes self-contained HTML without input cells. The page `<title>` is `report.REPORT_TITLE` = `"Forecast Regret"`. It contains no CDN scripts (`require_js_url=""`, `mathjax_url=""`), no `<script src=http…>` or `<link href=http…>`, and plotly.js appears once; the showcase map's basemap is inlined (§6.2).

### 2.14 Opt-in commands (N1c, S1, S2)

None of these is part of the five core commands, and none changes `regret.parquet`. Each writes next to `cfg.results_path` (`data/results/` in full mode; the fixture config writes the committed copies in `tests/fixture_results/`), so the fixture config cannot overwrite the full files.

**`regret neuralgcm` (N1c)** is the NeuralGCM add-on (SPEC §1.5): `regret fetch --with neuralgcm,neuralgcm_ens`, then `regret neuralgcm`.

```python
NAME = "neuralgcm"; STEP_H = 12
RESULTS_FILE = "neuralgcm_regret.parquet"; SENSITIVITY_FILE = "neuralgcm_sensitivity.parquet"
SENSITIVITY_COLUMNS = ("source", "lead_h", "n", "regret_6h_kg", "regret_12h_kg", "regret_12h_core_set_kg")
def addon_sources(cfg: Config) -> tuple[str, ...]            # (*cfg.sources, "neuralgcm")
def addon_flights(cfg: Config) -> tuple[Flight, ...]         # matched_flights(cfg, "neuralgcm")
def run(cfg: Config, *, flights=None, leads_h=None, workers=None) -> tuple[pd.DataFrame, pd.DataFrame]
    # (add-on results, sensitivity table); identical for any worker count
def main(argv=None) -> int     # run(get_config()); writes both files; logs elapsed_s
```

- **Reduced method.** Only the matched flights (110 full, 6 fixture). Every forecast source, core and NeuralGCM, is planned with `forecast_winds(..., step_h=12)`, so differences between sources measure forecast quality, not time resolution; replay stays through 6-hourly ERA5.
- **Candidate set.** The truth-optimised plan plus the five forecast sources (`hres`, `graphcast`, `pangu`, `persistence`, `neuralgcm`) at every lead, all at `step_h=12`. The hindsight plan, regret and tie rule (§3) are recomputed on that set, so `regret_fuel_kg ≥ 0` holds and a plan identical to the truth-optimised plan has regret 0.
- **`neuralgcm_regret.parquet`** has the §4 columns, dtypes and row order (truth row first, then sources in `addon_sources` order, then lead), one truth row plus 5 × 5 forecast rows per flight.
- **`neuralgcm_sensitivity.parquet`** has one row per core source (not `neuralgcm`) and lead, in `cfg.sources` order then lead, with `source` (str), `lead_h` (int64), `n` (flights), and three mean fuel regrets in kg: `regret_6h_kg` (native 6-hourly planning, core candidate set), `regret_12h_kg` (12-hourly planning, the five-source add-on set) and `regret_12h_core_set_kg` (12-hourly planning against the core candidate set: truth plus the four core sources). The last column isolates the time-resolution effect from the effect of adding NeuralGCM to the candidates.

**`regret ensemble` (S1)** is the robust plan choice (SPEC §1.3 item 1) on the add-on's flights and 12-hourly planning. Run it after `regret neuralgcm`.

```python
SOURCE = "neuralgcm_ens"; STEP_H = 12; MEMBERS = 25
RESULTS_FILE = "ensemble_regret.parquet"; CHOICES = ("mean_robust", "p90_robust")
COLUMNS = ("flight_id", "direction", "lead_h", "choice", "members", "fuel_kg", "time_min", "co2_kg",
           "regret_fuel_kg", "beats_hindsight")
def choose_robust(cost: ndarray) -> tuple[int, int]            # (mean-robust, p90-robust) plan indices
def floored_regret(fuel_kg: float, hindsight_kg: float) -> float
def beats_hindsight(fuel_kg: float, hindsight_kg: float) -> bool
def addon_hindsight(cfg: Config) -> dict[str, float]           # flight_id -> hindsight fuel_kg
def run(cfg, *, flights=None, leads_h=None, members=MEMBERS, workers=None, hindsight=None) -> pd.DataFrame
def main(argv=None) -> int     # run(get_config()); writes cfg.results_path.parent / RESULTS_FILE; logs elapsed_s
```

- **Method.** Per matched flight and lead: plan on each of M members (`forecast_winds(cfg, "neuralgcm_ens", flight, lead_h, step_h=12, member=k)`); cross-replay every member's plan through every member's winds, as if each were the truth (cost matrix `cost[j, k]` = fuel of plan j in member k); the **mean-robust** plan has the lowest mean cost across members and the **p90-robust** plan the lowest 90th-percentile cost (ties go to the lowest member index); replay both chosen plans through ERA5 truth.
- **M = 25 (`MEMBERS`)**, chosen from measured cost: M = 50 takes ~180 s per flight × lead on one worker, and the cost grows as M², so M = 25 puts the full run at ~1,650 s (≤ 30 min). The download is the same for any M (the store chunks all 50 members together), so `fetch` always keeps every member.
- **Floor.** Regret is `fuel_kg − min(hindsight, fuel_kg)` (never negative), against the add-on hindsight fuel of the flight from `neuralgcm_regret.parquet` (`addon_hindsight`). `beats_hindsight` is true when a chosen plan's fuel is strictly below that hindsight fuel (the hindsight plan is chosen with truth knowledge from deterministic candidates only, so an ensemble plan can beat it; its regret is then 0).
- **Test-only fallback.** When `run()` is given explicit `flights` and no `hindsight` mapping, it compares against the cheaper of the two chosen plans instead, so tests need no add-on file. That fallback is for tests only and makes about half the rows zero-regret by construction; real runs go through `main()` (`flights=None`), which always reads `neuralgcm_regret.parquet` and raises if it is missing.
- **`ensemble_regret.parquet`** columns, in order: `flight_id` (str), `direction` (str), `lead_h` (int64, h), `choice` (str, `mean_robust` or `p90_robust`), `members` (int64, M used), `fuel_kg`, `time_min`, `co2_kg`, `regret_fuel_kg` (float64) and `beats_hindsight` (bool). Two rows per flight × lead. Row order is flight, lead, then `CHOICES`; the result is identical for any worker count.

**`geostrophic` (S2)**: `regret fetch --with geopotential`, then `regret geostrophic`.

```python
RESULT_NAME = "geostrophic.parquet"; REFERENCE = "era5"; FORECAST_SOURCES = ("hres", "graphcast", "pangu")
COLUMNS = ["source", "lead_h", "ageostrophic_fraction", "n_fields"]
def run(cfg: Config) -> pd.DataFrame
def main(argv=None) -> int     # run(get_config()); writes cfg.results_path.parent / RESULT_NAME; logs elapsed_s
```

- The results file sits next to `cfg.results_path` (`data/results/geostrophic.parquet`; the fixture config writes `tests/fixture_results/geostrophic.parquet`, which is committed).
- Columns: `source` (str: `era5` is the reference, then `hres`, `graphcast`, `pangu`; persistence is ERA5 at initialisation, so it has no rows), `lead_h` (int64, h), `ageostrophic_fraction` (float64, share of the 30–70 °N wind not in geostrophic balance at 250 hPa), `n_fields` (int, flights averaged). The `era5` rows are ERA5 at the same valid times, once per lead.
- Geopotential is read from `geopotential_<source>.zarr` (§2.5). Only `figures.geostrophic` reads the results file.

---

## 3. Tie rule

- **Hindsight plan:** the candidate with the lowest replayed fuel; a tie goes to the truth-optimised plan, then to the earlier source in `Config.sources`, then to the shorter lead. (SPEC §4.4: candidates are the truth-optimised plan and every forecast plan, all sources and leads; time and CO₂ rank identically.) Fuel is compared with exact equality of `fuel_kg`.
- **Optimiser gap:** recorded only when a forecast plan is strictly lower. Its size is the truth-optimised fuel minus the hindsight fuel, stored in `optimiser_gap_fuel_kg` on the hindsight row only.
- **Zero-regret share:** counts every plan with regret exactly 0, ties included.

Consequences: exactly one `is_hindsight` row per flight, with regret exactly 0; a forecast plan identical to the truth-optimised plan has regret 0, is not `is_hindsight`, and records no gap.

---

## 4. Results schema (`regret.parquet`)

One row per plan: per flight, one truth-optimised row plus one row per `(source, lead_h)`. Rows: flights × `len(sources)` × `len(leads_h)` forecast rows + one truth row per flight. Columns in this order:

| Column | dtype | Unit / meaning |
|---|---|---|
| `flight_id` | str | `Flight.flight_id` |
| `direction` | str | `eastbound` or `westbound` |
| `departure_time` | datetime64[ns] | UTC |
| `source` | str | forecast source; `"truth"` on the truth-optimised row |
| `lead_h` | int64 | hours; `0` on the truth-optimised row |
| `is_truth_optimised` | bool | true on the truth-optimised row |
| `is_hindsight` | bool | exactly one true per flight |
| `fuel_kg` | float64 | replayed fuel, kg |
| `time_min` | float64 | replayed flight time, min |
| `co2_kg` | float64 | `3.16 * fuel_kg`, kg |
| `regret_fuel_kg` | float64 | `fuel_kg` − hindsight `fuel_kg`, kg, ≥ 0 |
| `regret_fuel_pct` | float64 | `100 * regret_fuel_kg / hindsight fuel_kg`, % |
| `regret_time_min` | float64 | `time_min` − hindsight `time_min`, min, ≥ 0 |
| `regret_co2_kg` | float64 | `co2_kg` − hindsight `co2_kg`, kg, ≥ 0 |
| `wind_error_ms` | float64 | wind error, m/s (RMS along the hindsight plan's path); **`0.0` on the truth-optimised row**; `NaN` only if not computed |
| `fuel_flow_min_kgh` | float64 | minimum fuel flow over the replay, kg/h |
| `fuel_flow_max_kgh` | float64 | maximum fuel flow over the replay, kg/h |
| `optimiser_gap_fuel_kg` | float64 | gap size, kg, on the hindsight row only when it is a forecast plan strictly lower than the truth-optimised plan; `NaN` elsewhere |

The truth-optimised row has `source == "truth"`, `lead_h == 0`, `is_truth_optimised == True`.

---

## 5. File layout

| Path | Contents |
|---|---|
| `data/cache/era5.zarr`, `hres.zarr`, `graphcast.zarr`, `pangu.zarr` | core datasets (gitignored) |
| `data/cache/neuralgcm.zarr` | add-on, `fetch --with neuralgcm` |
| `data/cache/neuralgcm_ens.zarr` | add-on, `--with neuralgcm_ens`, has `member` (one chunk per member) |
| `data/cache/geopotential_era5.zarr`, `geopotential_hres.zarr`, `geopotential_graphcast.zarr`, `geopotential_pangu.zarr` | stretch (S2), `--with geopotential` |
| `data/results/regret.parquet` | full results (§4) |
| `data/results/neuralgcm_regret.parquet`, `neuralgcm_sensitivity.parquet`, `ensemble_regret.parquet`, `geostrophic.parquet` | opt-in results (§2.14), same names under `tests/fixture_results/` for the fixture config |
| `tests/fixtures/<dataset>.zarr` | committed, < 5 MB total, same naming as `data/cache/`; `neuralgcm.zarr` and `neuralgcm_ens.zarr` are the add-on fixtures |
| `tests/fixture_results/regret.parquet` | committed fixture results (§4) |
| `notebooks/regret_report.ipynb` | the report notebook |
| `reports/report.html`, `reports/report-fixture.html` | full and fixture reports |
| `qa/<ID>/report.md`, `qa/<ID>/*.png`, `qa/<ID>/scratch/` | QA output; scratch is gitignored |

---

## 6. Figures (`src/regret/figures/<name>.py`)

**Rendering rule.** Each module exports `FIG_ID: str` and exactly one `build_*` returning a `plotly.graph_objects.Figure`. Builders never call `fig.show()` or write files. HTML is always `fig.to_html(div_id=FIG_ID, ...)`, so the figure's div id is stable. The notebook loads plotly.js once, inline (`plotly.offline.init_notebook_mode(connected=False)`), and shows each figure with `fig.to_html(div_id=FIG_ID, full_html=False, include_plotlyjs=False)` (the showcase map also needs `geo_assets_html()`, §6.2); T28b owns the notebook. Standalone figure pages use `fig.write_html(path, include_plotlyjs=True, div_id=FIG_ID)`, except the showcase map, which uses `showcase_map.write_html` (§6.2).

`df` is the §4 results DataFrame (read with `pd.read_parquet`). Sources appear in order of first appearance in `df`.

| Module | `FIG_ID` | Signature | Task |
|---|---|---|---|
| `headline` | `fig-headline` | `build_headline(df: pd.DataFrame) -> go.Figure` (two stacked `go.Table` bands from `stats.aggregate(df)`) | T18, B3, B10 |
| `showcase_map` | `fig-showcase-map` | `build_showcase_map(cfg: Config, *, plans: dict \| None = None) -> go.Figure` | T20, B7 |
| `lead_regret` | `fig-lead-regret` | `build_lead_regret(df: pd.DataFrame) -> go.Figure` | T22, B5, B6 |
| `wind_error` | `fig-wind-error` | `build_wind_error(df: pd.DataFrame) -> go.Figure` | T24, B6, B11 |
| `sanity` | `fig-sanity` | `build_sanity(df: pd.DataFrame) -> go.Figure` | T26, B9 |
| `geostrophic` (opt-in) | `fig-geostrophic` | `build_geostrophic(df: pd.DataFrame) -> go.Figure`, `df` = `geostrophic.parquet`; also `geostrophic_summary(df) -> str` | S2, S3, B14 |
| `neuralgcm` (opt-in) | `fig-neuralgcm` | `build_neuralgcm(df: pd.DataFrame) -> go.Figure`, `df` = `neuralgcm_regret.parquet` | N1c |
| `ensemble` (opt-in) | `fig-ensemble` | `build_ensemble(df: pd.DataFrame, addon_df: pd.DataFrame) -> go.Figure`, `df` = `ensemble_regret.parquet`, `addon_df` = `neuralgcm_regret.parquet` | S1 |

Report order (SPEC §5.2), as the notebook's sections: 1–5 `fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity`; 6 geostrophic (`fig-geostrophic`); 7 NeuralGCM add-on (`fig-neuralgcm`); 8 ensemble robust plan (`fig-ensemble`); 9 Method. Sections 6, 7 and 8 are **opt-in**: each is shown only when its file exists next to `cfg.results_path` (`geostrophic.parquet`; `neuralgcm_regret.parquet`; `ensemble_regret.parquet`), and when it is absent the notebook shows a note naming the commands that produce it and no figure. A clean clone's report therefore has five figures plus three notes; with every opt-in file, **eight figure IDs** are in use.

Figure labels use the CONTEXT.md terms (plan, hindsight plan, regret, wind error, lead time, forecast source) and units: lead in `h`, fuel in `kg`, time in `min`, wind in `m/s`.

### 6.1 `style` (B6)

```python
SOURCE_COLOURS: dict[SourceName, str]   # hres #1f77b4, graphcast #2ca02c, pangu #9467bd, persistence #7f7f7f, neuralgcm #17becf
SOURCE_SYMBOLS: dict[SourceName, str]   # hres circle, graphcast diamond, pangu square, persistence x, neuralgcm triangle-up
FALLBACK = "#8c564b"; FALLBACK_SYMBOL = "star"
def colour(source: SourceName) -> str   # SOURCE_COLOURS.get(source, FALLBACK)
def symbol(source: SourceName) -> str   # SOURCE_SYMBOLS.get(source, FALLBACK_SYMBOL)
```

**Rule:** every figure takes a forecast source's colour and marker symbol from `style` (`colour()`, `symbol()`), so a source looks the same everywhere. No figure keeps its own colour table or positional colours. The hindsight plan and truth-optimised plan use colours no source uses (the map's hindsight plan is orange).

### 6.2 Showcase map (`showcase_map`, T20, B4, B7)

```python
BASEMAP_KEY = "world_110m"; DEFAULT_LEAD_H = 24
def showcase_plans(cfg: Config) -> dict      # keys: flight, truth, plans, replays, hindsight
def build_showcase_map(cfg: Config, *, plans: dict | None = None) -> go.Figure
def basemap_json() -> str                    # vendored plotly.js topojson (figures/geo/world_110m.json)
def geo_assets_html() -> str                 # <script> setting window.PlotlyGeoAssets.topojson.world_110m
def write_html(fig: go.Figure, path) -> None # standalone page: plotly.js and basemap inlined
```

- `showcase_plans(cfg)` follows the per-flight procedure (§2.11, steps 1–4) for `config.showcase_flight(cfg)` at every `cfg.leads_h` (every source at every lead, plus the truth-optimised plan), so the map needs only the cache, not `regret.parquet`. `build_showcase_map(cfg, plans=None)` calls it when `plans` is `None`; pass the dict from a prior call to reuse it (tests do). The hindsight plan is the one chosen by the tie rule from those candidates; the same hindsight path is shown at every lead. The map also reads `truth_winds` and `forecast_winds` for the wind-speed background and the slider.
- **Interaction:** a lead dropdown and a forecast-wind slider; changing the lead refreshes the active wind background as well as the slider steps.
- **Basemap is inlined, no CDN.** The map is a `Scattergeo`, and plotly.js fetches `https://cdn.plot.ly/un/world_110m.json` at view time unless `window.PlotlyGeoAssets.topojson.world_110m` already holds it. `geo_assets_html()` emits that `<script>` from the vendored file, so the map makes no network request (SPEC §2). The notebook cell that shows `fig-showcase-map` injects `geo_assets_html()` before the figure; a standalone page uses `write_html`, which does so itself and inlines plotly.js. Anything embedding the map without those two paths would trigger the fetch.
- Colours and symbols come from `style` (§6.1); the background is a monotone grey scale with the jet core darkest, and the persistence line is dashed with a white halo.

### 6.3 Headline (`headline`, T18, B3, B10)

- Two stacked `go.Table` bands in one figure: **Fuel** (`fuel_kg`, `fuel_pct`) and **Time and CO₂** (`time_min`, `co2_kg`, plus the zero-regret share). Each band shows source, lead time, then mean (90% CI), median and p90 per metric. The notebook (not the builder) adds a caption telling narrow-screen readers to scroll sideways (B13).
- A mean (90% CI) cell is always two lines (`mean<br>[lo, hi]`), so row height never depends on text width: every row is `ROW_H` px, every header `HEADER_H` px.
- `layout_height(n_rows: int) -> int` is the figure height with both bands fully visible (headers, `n_rows` rows per band, band labels, gap, margins); `build_headline` sets it. `REPORT_WIDTH = 1100` px is the width the table targets: the report's output area is 1,154 px at a 1,200 px viewport. `WIDTH` is the widest band's column widths plus margins.
- `SOURCE_LABELS` maps source names to display labels (`hres` → IFS HRES, `graphcast` → GraphCast, `pangu` → Pangu-Weather, `persistence` → Persistence baseline, `neuralgcm` → NeuralGCM); an unlisted source shows its own name.

### 6.4 Lead-regret and sanity layout

- `lead_regret`: 2 × 2 panels, shared lead-time x-axis; the top row has the forecast sources by direction (eastbound, westbound) and **persistence is on its own bottom row**, so its much larger regret does not squash the others (B5). Linear axes, lead ticks `12, 24, 48, 72, 120`, per-source symbols, an annotation labels the CI band, and the height is set explicitly (`_HEIGHT_PX = 700`).
- `sanity`: 2 × 2 panels (replay time by direction, fuel-flow range, optimiser-gap count, optimiser-gap size), legend off, height set explicitly (`HEIGHT_PX = 780`) so JupyterLab does not draw it ~360 px tall with colliding titles (B9).

### 6.5 Wind-error figure (`wind_error`, T24, B6, B11)

Two panels, forecast sources left and the persistence baseline right, each with its own linear axes (persistence's wind error is ~10× the others'); x is wind error in m/s, y is regret in kg.

- **Y-cap rule.** Each panel's y-range is `[lo, top]` with `top = 1.08 × percentile(regret, 99)` of that panel's plans and `lo` just below `min(0, min regret)`.
- **Pinned plans.** A plan above `top` is never hidden or clipped: it is drawn at its true x as a marker pinned `4%` of the axis height below the top edge, with its true regret in the hover. An annotation above the panel title (outside the plot area, so it covers no plan) reads "N plans above X kg shown at top edge (max Y kg)".
- **Median bins.** Plans are context (faint points); trends are binned medians on **common bins**: `n_bins = clamp(fewest // 15, 2, 8)`, where `fewest` is the smallest plan count of any source in the panel, with interior edges at the quantiles of the panel's pooled wind error, so every source shares the same x-bins. The fixture's 30 plans per source give 2 bins; the full results (600) give 8.
- **Per-bin minimum.** A source draws a bin's median only with at least `min(15, max(5, fewest // (2·n_bins)))` plans in it (7 on the fixture, 15 on the full results, so the shipped figure is unchanged).
- **Legend.** Every forecast source always has a legend entry, even when it has no median points. Entries are grouped by source (`legendgroup`), and the pinned-plan markers have no entry of their own.

### 6.6 Geostrophic figure (`geostrophic`, S2, S3, B14)

- `build_geostrophic(df)` plots `ageostrophic_fraction` by lead time per source with ERA5 as the reference; `FIG_ID = "fig-geostrophic"`. The linear y-axis is zoomed to the data and labelled as not starting at 0; hover is x-unified so every source shows at one lead.
- `geostrophic_summary(df) -> str` writes the caption sentence from the results (ERA5's level, the largest gap, and which sources sit above ERA5, if any), never from fixed numbers. The notebook shows it only with the figure.

### 6.7 NeuralGCM add-on and ensemble figures (`neuralgcm`, `ensemble`, N1c, S1)

- `build_neuralgcm(df)` reuses `build_lead_regret` (§6.4) for the add-on's five sources: persistence on its own bottom row, lead ticks at the leads, source colours and symbols from `style`. It sets the title to "<n>-source comparison on <flights> flights, 12-hourly planning" and moves the CI annotation below the five-entry legend, inside the figure (paper `y = -0.30`, B16). Height 900 px with the forecast-source row about 342 px tall, regret y-axes `rangemode="tozero"`, and `hovermode="x unified"` with each source's `mean [lo, hi] kg` in the label; CI-band traces take no hover (B15). Only this module adjusts the figure; `lead_regret.py` is unchanged.
- `build_ensemble(df, addon_df)` draws mean floored fuel regret (kg) against lead time (h) for the mean-robust and p90-robust plans (solid lines, neutral colours that no source uses) beside the add-on's NeuralGCM deterministic plan and the best core source by mean regret (dashed, `style` colours), each with a shaded 90% CI band. The title states M and the flight count; an annotation says the regret is floored at 0 against the add-on hindsight plan. Height `_HEIGHT_PX = 520`; `hovermode="x unified"` with `mean [lo, hi] kg` per line, CI bands excluded from hover (B15).
