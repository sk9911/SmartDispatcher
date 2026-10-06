# T32 QA: final end-to-end check

Date: 2026-10-01 · Branch `grilltest` · HEAD `b0575ab` · working tree clean at the start.

- **Clone:** `git clone . /var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret` at `b0575ab` (left in place).
- **Browser:** `playwright` MCP (Chrome).
- **Servers:** neither was running at the start (`lsof` exit 1; both `curl` checks exit 7). Both were started **from the clone's root** and stopped at the end.
- **Data paths:** the full config uses cwd-relative paths (`data/cache`, `data/results/regret.parquet`, `reports/report.html`; `config.py` lines 67–69), so the clone fetched into its own empty cache. Nothing came from the working tree's cache.

## Verdict: PASS, with no failures

| # | Step | Result |
|---|---|---|
| 1a | `uv sync` | **PASS**: rc 0, 1 s (uv's package cache was warm) |
| 1b | `uv run regret fetch` (live WeatherBench 2) | **PASS**: rc 0, 568 s wall (`elapsed_s=560.433`, "4 downloads"); the clone's `data/cache` holds 85 MB: `era5`, `hres`, `graphcast` and `pangu` `.zarr` |
| 1c | `uv run regret compute` | **PASS**: rc 0, 31 s wall; logs `wrote 2520 rows`, `elapsed_s=26.4` (< 2700) |
| 1d | `REGRET_BLOCK_NETWORK=1 uv run regret report` | **PASS**: rc 0, 7 s wall; `reports/report.html` 5,959,393 bytes |
| 2 | `time REGRET_BLOCK_NETWORK=1 uv run pytest -rs -q` in the clone | **PASS**: **291 passed, 0 skipped, 0 failed**, in 65.93 s (pytest) and **68.12 s total** (shell `time`), < 180 s |
| 3a | Clone's parquet equals the working tree's | **PASS**: `pandas.testing.assert_frame_equal` OK after sorting by `flight_id`, `source`, `lead_h`; both are 2520 × 18 |
| 3b | README headline numbers vs the clone's `build_headline` cells | **PASS** (table below) |
| 4a | SBC on the clone's `reports/report.html`, all 5 IDs | **PASS**: 3 `.main-svg` per ID; 1 console error, the allowed `/favicon.ico` 404; network shows only `GET /reports/report.html → 200`; `performance` resources show only the favicon; `PlotlyGeoAssets.topojson` is inlined |
| 4b | Showcase date | **PASS**: "2020-02-09" appears twice in the text; map title "Plans for JFK→LHR, 2020-02-09 00:00 UTC over the 250 hPa wind at departure" |
| 4c | CI brackets in the headline table | **PASS**: 80 CI cells, e.g. `294.0[229.3, 367.4]` |
| 4d | "Assumptions and limitations" | **PASS**: `H3`, followed by a `UL` with **8** `LI` |
| 4e | `document.title` | **PASS**: "Forecast Regret" |
| 4f | *Fits container*, all 5 figures at 1,200 px | **PASS** (table below) |
| 4g | Overlap sweep at 1,200 and 768 px | **PASS**: 0 intersections in every figure at both widths |
| 5 | JupyterLab Run All, full config, scratch copy | **PASS**: 0 stderr, 0 errors, **5** `.jp-OutputArea .js-plotly-plot`, **`elapsed_s=3.9`** (< 120), Idle |
| 7 | End state | **PASS**: working tree `git status --porcelain -- notebooks/` empty; servers stopped; browser closed |

### Pipeline timings (clone, `qa/T32/scratch/pipeline.log`)

| Step | Start | End | Wall | Logged |
|---|---|---|---|---|
| `uv sync` | 23:21:58 | 23:21:59 | 1 s | — |
| `regret fetch` | 23:21:59 | 23:31:27 | 568 s (9 min 28 s) | `elapsed_s=560.433` |
| `regret compute` | 23:31:27 | 23:31:58 | 31 s | `elapsed_s=26.4` |
| `regret report` (`REGRET_BLOCK_NETWORK=1`) | 23:31:58 | 23:32:05 | 7 s | — |
| **Total** | | | **607 s (~10 min)** | `=== ALL OK`, `exit=0` |

`report`'s only extra output was the usual ipykernel "running over TCP without encryption" warning.

### Step 2: test suite

- `291 passed, 316 warnings in 65.93s`; shell `time`: 68.12 s total.
- `-rs` lists no skips, and `grep -ci skip` finds 0 lines.
- **nbmake ran:** `notebooks/regret_report.ipynb::regret_report.ipynb` is collected (`addopts = "--nbmake"`).
- **Playwright in Chrome ran:** `tests/test_report_browser.py` has 4 tests: `test_no_console_errors`, `test_figures_rendered`, `test_no_network_requests` and `test_browser_is_google_chrome`. The `[chromium]` suffix is pytest-playwright's engine name; the last test asserts that it's Google Chrome.
- The browser test writes its report to `tmp_path` (`test_report_browser.py:22`). The clone's `reports/report.html` and `data/results/regret.parquet` have the same `shasum` before and after pytest (`b6d1d8a6…`, `d60a10da…`), so step 4 tested the full report from step 1d.
- The clone's `git status --porcelain` after pytest showed nothing; nbmake did not write to the notebook.

### Step 3: results match

- **Shape (§8.2):**
  - 120 unique `flight_id`;
  - `hres`, `graphcast`, `pangu` and `persistence` each have 600 rows (120 × 5) at leads `[12, 24, 48, 72, 120]`;
  - `truth` has 120 rows at lead 0;
  - 0 NaN in the four regret columns, and every regret min is 0.0 (≥ 0).
- **README vs headline cells** (the clone's report, fuel band, mean (90% CI), directions pooled):

  | README | Cell in the clone's report |
  |---|---|
  | GraphCast 120 h: **160 kg** (124–202) | `160.0 [123.5, 202.2]` ✔ |
  | Pangu-Weather 120 h: 172 kg (139–208) | `171.9 [138.7, 208.2]` ✔ |
  | IFS HRES 120 h: **294 kg** (229–367) | `294.0 [229.3, 367.4]` ✔ |
  | Persistence 12 h: 526 kg | `525.5 [442.3, 617.6]` ✔ |
  | HRES 12 h: 6 kg | `5.6 [4.0, 7.5]` ✔ |

  These 120-flight magnitudes also show that the page was the full report, not `report-fixture.html`.

### Step 4: browser on the clone's report

**Servers.** Started in `$D` with the *Shared runtime resources* commands:

- `uv run python -m http.server 8765 --bind 127.0.0.1`: uv PID 43382, listener PID 43389;
- `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=full uv run jupyter lab --no-browser --ip 127.0.0.1 --port 8888 --IdentityProvider.token regret-dev`: uv PID 43384, listener PID 43388.

JupyterLab's log says "Serving notebooks from local directory: …/tmp.nH5olDMmot/regret".

**Fits container, 1,200 × 900.** The container is `.jp-OutputArea-output`; the svg width is the widest of each figure's `.main-svg`.

| Figure | svg | clientWidth | scrollWidth |
|---|---|---|---|
| fig-headline | 1067 | 1154 | 1154 ✔ |
| fig-showcase-map | 1134 | 1154 | 1154 ✔ |
| fig-lead-regret | 1134 | 1154 | 1154 ✔ |
| fig-wind-error | 1134 | 1154 | 1154 ✔ |
| fig-sanity | 1134 | 1154 | 1154 ✔ |

The page has no horizontal scroll (`scrollWidth` 1200 = `innerWidth`).

**Overlap sweep.** I used `scratch/sweep_run.js`, copied unchanged from R1, after a fresh load at each width.

| Figure | Swept at 1,200 px | Hits at 1,200 / 768 px |
|---|---|---|
| fig-headline | 2 annotations | 0 / 0 |
| fig-showcase-map | 2 titles, 1 annotation, legend + 5 items, dropdown, slider, colour bar + 6 ticks | 0 / 0 |
| fig-lead-regret | 4 titles, 5 annotations, legend + 4 items, 19 ticks | 0 / 0 |
| fig-wind-error | 5 titles, 5 annotations, legend + 4 items, 28 ticks (25 at 768 px) | 0 / 0 |
| fig-sanity | 6 titles, 7 annotations, 36 ticks | 0 / 0 |

- At 768 px the headline table is wider than the container (1067 px). That is the narrow-screen case the lead accepted in R1/B13, with the scroll caption.
- Screenshot: `chrome.png` (full page, 1,200 px).

### Step 5: JupyterLab run-all (full config)

- **Setup:**
  - I copied the clone's `notebooks/regret_report.ipynb` to `$D/qa_scratch/regret_report.ipynb`, the same depth as `notebooks/`.
  - I opened it in a reset workspace (`/lab/workspaces/t32/tree/qa_scratch/regret_report.ipynb?reset`). Exactly one document tab was open.
- **Run:** Run → Run All Cells through the real menu. I waited for no `[*]` prompt, `elapsed_s=` present, and Idle. It took 4.5 s from the click.
- **Outputs:**
  - Prompts `[1]`–`[7]`; status "Python 3 (ipykernel) | Idle".
  - 0 `application/vnd.jupyter.stderr` and 0 `application/vnd.jupyter.error` outputs. The MIME types were only `text/html` and `application/vnd.jupyter.stdout`.
  - 5 plots: `fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity`.
  - **`elapsed_s=3.9`**.
- **Full config confirmed:** the notebook's GraphCast 120 h cell reads `160.0 [123.5, 202.2]`, the 120-flight value.
- Screenshot: `notebook.png`.

## SPEC §8 definition of done

| § | Item | ✔ | Proof |
|---|---|---|---|
| 8.1 | From a clean clone: `brew install uv && uv sync && uv run regret fetch && uv run regret compute && uv run regret report` succeeds | ✅ | `brew install uv` is already satisfied: `uv --version` prints `uv 0.12.21 (Homebrew 2026-09-29 aarch64-apple-darwin)`. In a fresh `git clone` at `b0575ab`: sync, fetch, compute and report all rc 0, `=== ALL OK`, `exit=0` (step 1). |
| 8.2 | Full Jan–Feb 2020 experiment for HRES, GraphCast, Pangu and persistence at all 5 leads | ✅ | The clone's `regret.parquet` has 120 flights × 4 sources × 5 leads = 2,400 forecast rows, plus 120 truth rows. It equals the working tree's results exactly (step 3). |
| 8.3 | `reports/report.html` generated, self-contained, with core charts (§5.2 items 1–4) and limitations | ✅ | The full `report.html` was checked over http in SBC: all 5 figures render (items 1–4 plus the sanity panel); the page is the only request; plotly.js and the topojson are inlined; "Assumptions and limitations" has 8 bullets (step 4, `chrome.png`). Loading from `file://` with zero outside requests is checked by the suite's Chrome Playwright tests, on a report built from the fixture in `tmp_path` (`test_report_browser.py:22`). The suite does not open the full report from `file://`. |
| 8.4 | Test suite green, including nbmake and Playwright in Chrome | ✅ | 291 passed, 0 skipped, including `regret_report.ipynb` (nbmake) and the 4 `test_report_browser.py` tests, with `test_browser_is_google_chrome` among them (step 2). |
| 8.5 | README: 3-line summary, how to run, headline number | ✅ | `README.md` has the summary (lines 3–4), `## Headline` (line 7: "At 120 h lead time, GraphCast costs **160 kg**…"), and `## How to run` (line 13: `uv sync` / `fetch` / `compute` / `report`). The numbers match the report (step 3). |
| 8.6 | `SPEC.md`, `CONTEXT.md` and ADRs committed | ✅ | `git ls-files --error-unmatch` finds `SPEC.md`, `CONTEXT.md`, `docs/adr/0001-own-grid-planner-not-openap-top.md` and `docs/adr/0002-weatherbench2-1p5-degree-grid.md`; all are present in the fresh clone. |

### Time limits

| Limit | Measured | ✔ |
|---|---|---|
| SPEC §6: tests in < 3 min | 68.12 s (shell `time`) | ✅ |
| SPEC §5.1: compute < 30 min (hard limit 45 min; PLAN `elapsed_s` < 2700) | `elapsed_s=26.4` (31 s wall) | ✅ |
| SPEC §5.2: notebook < 2 min | `elapsed_s=3.9` (full config, JupyterLab) | ✅ |

## Step 7: end state

- **Working tree:** `git status --porcelain -- notebooks/` printed nothing. The whole working tree showed only `?? qa/T32/`.
- **Servers:** I stopped them by the PIDs I started (43382, 43384, 43388, 43389). Afterwards `lsof` on 8765/8888 exits 1, both `curl` checks exit 7, `ps` finds none of the PIDs, and `pgrep -fl 'ipykernel|jupyter|http.server'` finds nothing (no orphaned kernel).
- **Browser:** closed.
- **Clone:** left at `/var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret`. Its only untracked file is `qa_scratch/` (the notebook copy).

## Notes, not failures

- `fetch` took 9.5 min, against the lead's estimate of about 13 min. The log shows "4 downloads" into an empty cache, and the cache holds `era5`, `hres`, `graphcast` and `pangu`. I saw no persistence store and did not check how persistence is derived.
- `uv sync` took 1 s because uv's global package cache was warm. That is how uv normally behaves, and the clone's `.venv` was created fresh.

## Files

- `report.md` (this file); screenshots `chrome.png` and `notebook.png`.
- Scratch (gitignored):
  - `pipeline.sh` and `pipeline.log`;
  - `pytest.log`;
  - `compare.py`;
  - `hash_before.txt`;
  - `sweep_run.js`, `overlap.js`, `run_overlap.js` (from R1);
  - `http.log`, `jupyter.log`, PID files and `clone_path`.
