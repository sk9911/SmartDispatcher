# S4 QA: stretch figures (geostrophic balance, section 6)

Date: 2026-10-01 · Branch `grilltest` · HEAD `4581444` (S3 = `b001d0a`). The working tree was clean at the start.

- **Browser:** `playwright` MCP (Chrome).
- **Servers:** neither was running at the start (both `curl` checks exited 7, and `lsof` found nothing).
  - Path (a): I started both from the working tree's root, with the *Shared runtime resources* commands and the fixture config:
    - static server: uv PID 45539, listener PID 45545;
    - JupyterLab: uv PID 45541, listener PID 45546.
  - Path (b): I stopped both, then served **the T32 clone's root** on 8765 (uv PID 45821, listener PID 45825).
  - Every server was stopped by its PID at the end.
- **Step 1:** `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture uv run regret report` exited 0. Its only output was the usual ipykernel TCP warning. Afterwards `git status` was still clean, so the regenerated `reports/report-fixture.html` is byte-identical to the committed one.

## Verdict: FAIL on 2 items; every other item passes

| # | Step | Result |
|---|---|---|
| 1 | Regenerate the fixture report | **PASS**: rc 0, byte-identical to HEAD |
| 2a | SBC: `.main-svg` for all 6 IDs | **PASS**: 3 each for `fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity` and `fig-geostrophic` |
| 2b | SBC: console | **PASS**: 1 error, the allowed `/favicon.ico` 404 |
| 2c | SBC: network | **PASS**: only `GET /reports/report-fixture.html → 200`; `performance` resources show only the favicon |
| 2d | "Assumptions and limitations" | **PASS**: `H3`, then a `UL` with **8** `LI` |
| 2e | Section order | **PASS**: 1 Headline … 5 Sanity panel, **6 Stretch: geostrophic balance at 250 hPa**, **7 Method, assumptions and limitations** |
| 3a | Fits container, 6 figures at 1,200 px | **PASS** (table below) |
| 3b | Overlap sweep at 1,200 and 768 px | **PASS**: 0 intersections in all 6 figures at both widths |
| 4a | JupyterLab Run All (scratch copy): 0 stderr | **PASS**: 0 `stderr`, 0 `error`; prompts `[1]`–`[8]`; Idle |
| 4b | Exactly 6 `.jp-OutputArea .js-plotly-plot` | **PASS**: the 6 IDs above |
| 4c | `elapsed_s` < 120 | **PASS**: `elapsed_s=3.7` (Run All to Idle took 3.9 s) |
| 4d | Overlap sweep in the notebook | **PASS**: 0 intersections in all 6 figures |
| 5a | Hover shows the source, lead and value | **PASS**, with a caveat that belongs to 5f |
| 5b | One line per forecast source; colours and symbols from `style`; consistent with the other figures | **PASS** |
| 5c | ERA5 drawn as a reference line | **PASS**: "ERA5 (reference)", dashed, `#333333` |
| 5d | Axis titles with units | **PASS** (see the note) |
| 5e | Ticks at 12/24/48/72/120 | **PASS** |
| 5f | Reader view: can the differences be seen? | **FAIL**: see Failure 2 |
| 6a | Caption matches the figure (ERA5 ≈ 0.21, forecasts within 0.025 and slightly lower) | **FAIL** on the fixture: see Failure 1 |
| 6b | "possible explanation, not a finding" wording | **PASS** |
| 6c | "Not done: NeuralGCM … ensemble robust plan" line present and accurate | **PASS** |
| 6d | Ageostrophic fraction used as CONTEXT.md defines it | **PASS** |
| 6e | No avoided words | **PASS**: 0 hits in section 6; page-wide hits are the same accepted ones as R1 |
| 7a | Clone at `b001d0a`, no `geostrophic.parquet` | **PASS** |
| 7b | SBC on the clone's `reports/report.html`, 5 IDs | **PASS**: 3 `.main-svg` each; 0 console errors; only the page requested |
| 7c | Opt-in note visible, naming both commands | **PASS** |
| 7d | No `fig-geostrophic`; 0 stderr | **PASS** |
| 7e | Fits container and the overlap sweep at 1,200 and 768 px | **PASS** |
| 8 | End state | **PASS**: `git status --porcelain -- notebooks/` empty; servers stopped by PID; browser closed |

## Failures for the lead

### Failure 1 (step 6a): on the fixture page, the section 6 caption doesn't match the figure

- **Expected:** the caption says, "ERA5 sits at about 0.21. The three forecast sources stay within 0.025 of it and are slightly more balanced (lower)." The figure beside it should show that.
- **Actual:** in `report-fixture.html` and in the JupyterLab run, **IFS HRES at 24 h is 0.2137, above ERA5's 0.2129.** The hover reads "IFS HRES · lead 24 h · ageostrophic fraction 0.214", and ERA5 reads 0.213.
  - Every other forecast point is lower than ERA5.
  - "Within 0.025" holds: the largest gap is 0.0146 (Pangu-Weather, 120 h).
- **Fixture values** (`tests/fixture_results/geostrophic.parquet`):

  | lead (h) | ERA5 | IFS HRES | GraphCast | Pangu-Weather |
  |---|---|---|---|---|
  | 12 | 0.2129 | 0.2100 | 0.2031 | 0.2033 |
  | 24 | 0.2129 | **0.2137** | 0.2035 | 0.1992 |
  | 48 | 0.2129 | 0.2114 | 0.2007 | 0.2001 |
  | 72 | 0.2129 | 0.2122 | 0.2011 | 0.1994 |
  | 120 | 0.2129 | 0.2064 | 0.1991 | 0.1983 |

- **Context:** the caption is static markdown written from the full results. On the working tree's full `data/results/geostrophic.parquet`, every forecast point is below ERA5 (0.2107), and the largest gap is 0.0244. So the caption is true for the full results and false at one point on the fixture, the same pattern as R1's fixture-caption failure.

### Failure 2 (step 5f): the figure doesn't let a reader see the differences the caption describes

- **Expected:** a reader can see that the forecasts sit slightly below ERA5, and can tell the sources apart, by eye and by hover.
- **Actual:** the y-axis starts at 0 (range 0–0.229), so on the fixture all four lines sit in a **21.6 px band of the 320 px plot**.
  - The scale, measured from `_fullLayout.yaxis` at 1,200 px, is 1,396 px per unit. The gaps below are the y-differences times that scale.

    | lead (h) | ERA5 − IFS HRES (px) | \|GraphCast − Pangu-Weather\| (px) |
    |---|---|---|
    | 12 | 4.0 | 0.2 |
    | 24 | −1.1 | 6.0 |
    | 48 | 2.1 | 0.8 |
    | 72 | 1.0 | 2.4 |
    | 120 | 9.1 | 1.1 |

  - GraphCast and Pangu-Weather are within 2.5 px of each other at 4 of 5 leads, so their markers (size 9) sit on top of each other.
  - IFS HRES is within about 4 px of ERA5's dashed line at 4 of 5 leads, so the line hides the reference.
  - `notebook.png` and `geostrophic-hover.png` show this: the four lines look like two.
- **Hover:** a real `page.mouse.move` onto GraphCast's 48 h point returned "Pangu-Weather · lead 48 h · 0.200". With `hovermode: "closest"`, GraphCast at 48 h (and at 12 h, 0.2 px apart) can't be reached by hover. GraphCast at 24 h, where the gap is 6 px, does hover correctly ("GraphCast · lead 24 h · 0.203").
- **The full results have the same problem.** This is an estimate from `data/results/geostrophic.parquet` at the same plot height, not measured in a browser: about 1,416 px per unit, all lines within about 35 px, ERA5 − IFS HRES 2.0–7.8 px, and GraphCast vs Pangu-Weather 0.4–6.0 px (≤ 1.4 px at 12, 48 and 72 h). The shipped figure is affected, not just the fixture.
- **Likely cause (from reading the code; not tested):** `yaxis=dict(..., rangemode="tozero")` in `src/regret/figures/geostrophic.py`.

## Path (a): fixture, working tree

### Step 2: SBC on `reports/report-fixture.html` (1,200 × 900)

- `document.title` is "Forecast Regret".
- The page has no horizontal scroll (`scrollWidth` 1200 = `innerWidth`).
- `data-mime-type="application/vnd.jupyter.stderr"` matches 0 elements.
- Screenshot: `chrome.png` (full page).

### Step 3: Fits container and overlap sweep

The container is `.jp-OutputArea-output`; the svg width is the widest of each figure's `.main-svg`.

| Figure | 1,200 px: svg / client / scroll | 768 px: svg / client / scroll |
|---|---|---|
| fig-headline | 1067 / 1154 / 1154 ✔ | 1067 / 722 / 1087 (the accepted B13 narrow-screen case) |
| fig-showcase-map | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
| fig-lead-regret | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
| fig-wind-error | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
| fig-sanity | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
| fig-geostrophic | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |

- **Overlap sweep:** I used `scratch/sweep_run.js`, copied from T32, with `fig-geostrophic` added to its ID list. I ran it after a fresh load at each width.
- It found 0 intersections in every figure at both widths.
- `fig-geostrophic` swept 3 titles (the figure title, `xtitle` and `ytitle`), the legend plus 4 items, and 10 ticks.
- The other figures' counts match R1.

### Step 4: JupyterLab run-all (scratch copy, fixture config)

- **Setup:**
  - I copied `notebooks/regret_report.ipynb` to `qa/S4/scratch/regret_report.ipynb`.
  - I opened it in a reset workspace (`/lab/workspaces/s4/tree/qa/S4/scratch/regret_report.ipynb?reset`). The only document tab was the scratch copy.
- **Run:** Run → Run All Cells through the real menu. I waited for no `[*]` prompt, `elapsed_s=` present, and Idle.
- **Outputs:**
  - MIME types were only `text/html` (8) and `application/vnd.jupyter.stdout` (1); 0 stderr and 0 error.
  - Prompts `[1]`–`[8]`. JupyterLab renders only the cells in view, so cells 1–5 first read blank; scrolling through showed all eight.
  - **6 plots**, the 6 IDs. **`elapsed_s=3.7`**.
  - Status: "Python 3 (ipykernel) | Idle".
- **Fits container in the notebook:** 768 px output area. All 5 figures are 748 px; the headline is 1,067 px (the B13 case).
- **Overlap sweep in the notebook:** 0 intersections in all 6 figures.
- Screenshot: `notebook.png` (section 6, the code cell and the figure).

### Step 5: the geostrophic figure

- **Hover (5a):** I used a real `page.mouse.move` via `browser_run_code_unsafe` (*Plotly interactions* rule). The hover template is `"%{fullData.name}<br>lead %{x} h<br>ageostrophic fraction %{y:.3f}"`.
  - IFS HRES 24 h gave "IFS HRES · lead 24 h · ageostrophic fraction 0.214".
  - GraphCast 24 h gave "GraphCast · lead 24 h · 0.203".
  - ERA5 gave "ERA5 (reference) · ageostrophic fraction 0.213", with no lead, because it is a flat reference.
  - The coincident-point problem is under Failure 2.
- **Lines and style (5b):** 3 forecast traces, `lines+markers`, width 2:

  | Trace | colour | symbol | `style.SOURCE_COLOURS` / `SOURCE_SYMBOLS` | Same in `fig-lead-regret` and `fig-wind-error` |
  |---|---|---|---|---|
  | IFS HRES | `#1f77b4` | circle | `hres` ✔ | ✔ |
  | GraphCast | `#2ca02c` | diamond | `graphcast` ✔ | ✔ |
  | Pangu-Weather | `#9467bd` | square | `pangu` ✔ | ✔ |

  The names use the same labels as the other figures. Persistence is absent, which is right: S2 computes no geostrophic value for it.
- **ERA5 (5c):** "ERA5 (reference)", `mode: lines`, dashed, `#333333`, flat at 0.2129.
- **Axes (5d):**
  - x: "lead time (h)".
  - y: "ageostrophic fraction". The quantity is a dimensionless ratio (|V − V_g| / |V|), so no unit is missing.
  - Title: "Ageostrophic fraction at 250 hPa, 30–70°N, by lead time".
- **Ticks (5e):** `tickmode: array`, `tickvals` [12, 24, 48, 72, 120]. The rendered x ticks are `12, 24, 48, 72, 120`; the y ticks are `0 … 0.2`.
- Screenshot: `geostrophic-hover.png` (1,200 px, with the ERA5 hover label showing).

### Step 6: reader view of section 6

Caption, verbatim:

> Is a forecast's wind near jet level balanced the way the real atmosphere is? The **ageostrophic fraction** is |V − V_g| / |V|, the share of the wind that the geostrophic wind V_g (from the geopotential gradient) does not explain, taken over 30–70°N and averaged over the experiment's flights. ERA5 sits at about 0.21. The three forecast sources stay within 0.025 of it and are slightly more balanced (lower). Smoother machine-learning fields are a possible explanation, not a finding; the sample is small and nothing here was tested for it.
>
> Not done: the NeuralGCM source and the ensemble robust plan. The WeatherBench 2 NeuralGCM stores start on 2020-01-01 (the first flights need initialisations from 2019-12-27) and have 12-hourly steps, while the method needs 6-hourly.

- **6a: FAIL on the fixture** (Failure 1). It holds on the full results.
- **6b: PASS.** The text says "a possible explanation, not a finding" and adds "nothing here was tested for it".
- **6c: PASS.** The line matches the lead's probe in Plan changes (2026-10-01, "N1, N2 and S1 blocked"):
  - inits start 2020-01-01, so the 10 inits from 2019-12-27 00Z to 2019-12-31 12Z are missing;
  - `prediction_timedelta` is 12-hourly, while the method needs 6-hourly steps;
  - the same gaps apply to both the deterministic and the ensemble store.
- **6d: PASS.** The caption uses |V − V_g| / |V|, 250 hPa and 30–70°N, as CONTEXT.md defines it, in bold as the defined term.
  - The method is a ratio of cos(lat)-weighted area means (`geostrophic.py` lines 10–12). "Averaged over the experiment's flights" matches `run()`: the fields are valid at each flight's departure, and the result is the mean of those fields (`n_fields` = 6 on the fixture).
- **6e: PASS.**
  - I grepped all 36 CONTEXT.md `_Avoid_` terms, whole word and case-insensitive, over `document.body.innerText`, every `svg text`, and each figure's `data`/`layout` JSON (with `x`, `y`, `z`, `lat`, `lon`, `customdata` and `text` stripped).
  - Section 6 has **0** hits. It says "forecast sources", not "models", and never "balance error".
  - Page-wide, the only hits are the same as R1: "error" (the defined Wind error term, and "forecast's error") and "model" (SPEC §7's "ERA5 … is itself a model").

## Path (b): absent file (the T32 clone)

- **Clone:** `/var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret`.
  - `git rev-parse --short HEAD` gives `b001d0a`.
  - `data/results/` holds only `regret.parquet`; `test -e data/results/geostrophic.parquet` exits 1.
  - Its only untracked path is `qa_scratch/`, from T32.
  - `reports/report.html` is 5,961,441 bytes (23:52, S3's regeneration). `curl` through 8765 returned the same size, which confirms the server was serving the clone.
- **SBC at 1,200 × 900, 5 IDs:**
  - 3 `.main-svg` each; 5 `.js-plotly-plot` in total.
  - **0** console errors; there was not even a favicon 404 this run.
  - The network shows only `GET /reports/report.html → 200`, and `performance` resources are empty. `PlotlyGeoAssets.topojson` is present.
  - `document.title` is "Forecast Regret". "Assumptions and limitations" is an `H3` followed by a `UL` with 8 `LI`.
  - The section order is the same as path (a), with 6 Stretch and then 7 Method.
- **Opt-in note (7c):** the code cell's only output is `text/markdown`, rendered in italics:

  > The geostrophic balance figure is an optional stretch and its result is not present. To produce it, run `uv run regret fetch --with geopotential` and then `uv run regret geostrophic`, then run the report again.

  - Both commands are in `<code>`.
  - It is visible: 1,154 × 52 px, `visibility: visible`, opacity 1.
  - At 768 px it wraps to 74 px with no overflow (`scrollWidth` = `clientWidth` = 722).
  - Screenshot: `absent-note.png`.
- **No figure, no stderr (7d):**
  - `#fig-geostrophic` is absent, and the string `fig-geostrophic` doesn't appear anywhere in the page HTML.
  - 0 `stderr` and 0 `error` outputs.
  - The page's MIME types are `text/html`, `text/markdown` and `text/plain`. The only `text/plain` output is `elapsed_s=3.9`, the last cell's stdout line. So the page has no stream output besides it, however nbconvert labels MIME types.
- **Fits container and overlap sweep (7e):**

  | Figure | 1,200 px: svg / client / scroll | 768 px: svg / client / scroll | Hits at 1,200 / 768 |
  |---|---|---|---|
  | fig-headline | 1067 / 1154 / 1154 ✔ | 1067 / 722 / 1087 (B13) | 0 / 0 |
  | fig-showcase-map | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ | 0 / 0 |
  | fig-lead-regret | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ | 0 / 0 |
  | fig-wind-error | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ | 0 / 0 |
  | fig-sanity | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ | 0 / 0 |

  - The sweep counts match T32's full report: lead regret 19 ticks; wind error 5 annotations and 28 ticks (25 at 768 px); sanity 36 ticks.
  - The page has no horizontal scroll at either width.
  - Screenshot: `chrome-absent.png` (full page, 1,200 px).

## Notes, not failures

- **Path (b) caption with no figure:** section 6's caption still quotes "ERA5 sits at about 0.21 … within 0.025" when the reader sees only the opt-in note. The numbers are from the full run in the working tree, not from anything on this page. This is for the lead to judge; the S3 check doesn't address it.
- **ERA5's hover** shows no lead, because the line is a flat reference. That's acceptable.
- **The y-axis title has no unit** because the ageostrophic fraction is dimensionless.
- **Console noise from stopping JupyterLab:** after I stopped the server, the open JupyterLab tab logged 13–14 connection errors, and I accepted its "unsaved changes" dialog to leave. Neither belongs to a page under test. The SBC console checks were made on fresh loads of the report pages.

## Step 8: end state

- **Notebooks:** `git status --porcelain -- notebooks/` printed nothing. The whole working tree showed only `?? qa/S4/`.
- **Servers:** stopped by the PIDs I started: 45539, 45545, 45541 and 45546 (the kernel, PID 45718, exited with JupyterLab), then 45821 and 45825. Afterwards:
  - `lsof` on 8765/8888 exits 1;
  - both `curl` checks exit 7;
  - `ps` finds none of the PIDs;
  - `pgrep -fl 'ipykernel|jupyter|http.server'` finds nothing.
- **Browser:** closed.
- **Clone:** left in place, unchanged. I only served it.

## Files

- `report.md` (this file).
- Screenshots:
  - `chrome.png`: fixture report, full page, 1,200 px;
  - `geostrophic-hover.png`: `fig-geostrophic` with the ERA5 hover label;
  - `notebook.png`: JupyterLab, section 6, after Run All;
  - `chrome-absent.png`: the clone's report, full page, 1,200 px;
  - `absent-note.png`: the clone's section 6 with the opt-in note.
- Scratch (gitignored):
  - the notebook copy `regret_report.ipynb`;
  - `sweep_run.js` (with the 6 IDs), `overlap.js` and `run_overlap.js` (from T32);
  - `report.log`, `http.log`, `http-clone.log` and `jupyter.log`;
  - the PID files.
