# T27 QA: sanity panel

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `0868a62`. `src/regret/figures/sanity.py` last changed in `34fa4c4` (B6 attempt 2) and had no uncommitted changes. B8 was editing the notebook in parallel. This QA doesn't touch it.
Browser: `playwright` MCP (Chrome), viewport 1200 × 807.
Data:
- the fixture, `tests/fixture_results/regret.parquet` (126 rows), for the SNC figure;
- the full results that ship, `data/results/regret.parquet` (2,520 rows, 120 of them truth-optimised), for the page, the hover, the content and the reader view.

## Summary

| # | Check | Result |
|---|---|---|
| 1 | SNC: `build_sanity` in JupyterLab | **PASS** |
| 2 | SBC on `qa/T27/scratch/fig.html`, *F* = `fig-sanity` | **PASS** |
| 3 | Hover: median eastbound replay time is lower than westbound | **PASS**: 321.2 min vs 419.6 min (real `page.mouse.move`) |
| 4a | 4 subplots with the right titles | **PASS** |
| 4b | x labels use source names, not raw ids | **PASS** |
| 4c | Axis titles carry units | **PASS** |
| 4d | Gap count per source matches the full results (12: HRES 6, GraphCast 5, Pangu 1) | **PASS** (figure = parquet = T17) |
| 5a | Reader view: each panel readable | **PASS standalone**, **FAIL in JupyterLab** (each plot area is 56 px tall) |
| 5b | Fuel-flow panel inside 4,000–8,000 kg/h | **PASS** (6,381–7,371 kg/h) |
| 5c | Gap panels make sense with so few gaps | **PASS with notes** (empty persistence slot has no label; n is not shown) |

The figure meets T27's check line. The one failure is the 5a reader-view finding in JupyterLab, plus some minor notes in step 5.

## Step 1: SNC

- `qa/T27/scratch/make_nb.py` (nbformat) wrote `qa/T27/scratch/check.ipynb` with 3 cells:
  1. `regret.offline.install_if_requested()`, then `os.chdir(<repo root>)`.
  2. Read the **fixture** parquet, `fig = build_sanity(fx)`, `fig.show()`.
  3. Read the **full** parquet, `build_sanity(df)`, `show()`, then `write_html('qa/T27/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)`. Cell 3 also displays the full figure, so the reader view can be judged inside JupyterLab.
- Neither server was running (both `curl` checks exited 7). I started both with the exact *Shared runtime resources* commands (`REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture …`).
- JupyterLab's restored workspace reopened B6's `qa/B6/scratch/check-final.ipynb`. I closed it with **Discard**, so that file is unchanged.
- I chose Run → Run All Cells through the real menu, then polled until Idle (about 4 s).
- `browser_evaluate` results:
  - `.jp-OutputArea .js-plotly-plot`: **2** (fixture and full) ✔
  - `[data-mime-type="application/vnd.jupyter.stderr"]`: **0** ✔
  - Status bar: `Python 3 (ipykernel) | Idle` ✔
  - Prompts: `[1]`, `[2]`, `[3]`
  - Stdout: `fixture rows 126`, `full rows 2520 ; wrote qa/T27/scratch/fig.html`
- The console logged 3 × "A kernel is required to send debug messages". This is the same debugger-panel noise B5 and B6 saw, and SNC does not check the console.
- Screenshot: `qa/T27/notebook.png`, showing the full-results figure in JupyterLab.

## Step 2: SBC

- Leaving JupyterLab raised a `beforeunload` dialog. I accepted it and loaded the page fresh, so the logs below come from a clean load.
- `#fig-sanity .main-svg`: **3** ✔
- Console errors: **1**, the allowed `/favicon.ico` 404 ✔
- Network: only `GET http://127.0.0.1:8765/qa/T27/scratch/fig.html → 200` ✔
- Screenshot: `qa/T27/chrome.png`, full page, taken before any hover.
- Standalone layout: 1184 × 807 px. Each of the 4 plot areas is 461 × 235 px.

## Step 3: Hover

I didn't try `browser_hover`, because Plotly's drag layer intercepts it (T25, B6). Instead, as the *Plotly interactions* rule allows, I used `browser_run_code_unsafe` to move the real mouse (`page.mouse.move`, 5 steps). The target was each box's median pixel: `xaxis.d2p(direction)` and `yaxis.c2p(calcdata[i][0].med)`, offset by the `xy` drag rectangle. Each hover showed 8 labels in `.hoverlayer .hovertext`. Each label names its statistic, and the median label is the one marked with the trace name:

| Box | Median label in `.hoverlayer` | `calcdata` median | Mean (dashed) |
|---|---|---|---|
| eastbound | `eastbound(eastbound, median: 321.1511)` | 321.151 min (**5.35 h**) | 320.812 min |
| westbound | `westbound(westbound, median: 419.6031)` | 419.603 min (**6.99 h**) | 420.181 min |

- **Eastbound median 321.2 min < westbound 419.6 min** ✔. The difference is 98.5 min.
- These match pandas on the parquet (321.15 and 419.60).
- Screenshots: `qa/T27/hover-eastbound.png`, `qa/T27/hover-westbound.png`.

Minor notes, not checked:

- The hover has no unit, and it shows 4 decimals. `sanity.py` sets `hovertemplate="%{y:.1f} min…"`, but Plotly does not apply it to the box-statistic labels. Outlier hovers may still use it, but I didn't test that.
- The 8-label stack for westbound spills across the gap onto the fuel-flow panel. This is cosmetic.

## Step 4: Content

These values were read from the rendered figure (`gd._fullLayout`, `gd.calcdata`, the `.x3tick`/`.x4tick` text) and cross-checked against the parquet with `qa/T27/scratch/data_check.py`.

- **4a ✔** Subplot titles: "replay time by direction", "fuel-flow range", "optimiser-gap count", "optimiser-gap size".
- **4b ✔** The rendered x tick text in both gap panels reads `IFS HRES`, `GraphCast`, `Pangu-Weather`, `Persistence baseline`. The underlying x values remain the ids, which the colour lookup uses.
- **4c ✔** Axis titles:
  - y: `replay time (min)`, `fuel flow (kg/h)`, `gap count (plans)`, `mean gap size (kg)`;
  - x: `forecast source` on the gap panels. The top row is categorical (direction, min/max), so it needs no unit.
- **4d ✔** Gap counts:

| Source | Bar (figure) | Parquet | T17 | Gap sizes (kg) | Bar = mean (kg) |
|---|---|---|---|---|---|
| IFS HRES | 6 | 6 | 6 | 0.2, 0.7, 1.3, 2.8, 4.4, 4.7 | 2.34 |
| GraphCast | 5 | 5 | 5 | 0.5, 1.0, 1.4, 1.5, 2.7 | 1.42 |
| Pangu-Weather | 1 | 1 | 1 | 0.1 | 0.14 |
| Persistence baseline | 0 | 0 | — | — | NaN (no bar) |
| **Total** | **12** | **12** | **12** | | |

The 120 truth-optimised rows carry no gap values (all null), so including them in the panel changes nothing.

## Step 5: Reader view (full results)

### 5a. Readability

- **Standalone (`chrome.png`): readable.** I saw no collisions between titles, ticks or axis titles. This was a visual check only: `overlap.js`'s selectors (`.xtitle`, `.ytitle`, `.xtick text`, `.ytick text`) match only the first axis, so it did not measure the y2–y4 titles, the x3/x4 titles or the source tick labels. The boxes and bars are clear, and the colours of the four sources match `style` (`#1f77b4`, `#2ca02c`, `#9467bd`, `#7f7f7f`).
- **JupyterLab (`notebook.png`): FAIL, too squashed.**
  - **Expected:** each panel is readable in the notebook (SPEC §2 platform).
  - **Actual:** the figure has no explicit height, so it renders 768 × 360 px, and **every plot area is 271 × 56 px**.
  - The y-axis titles are longer than the 56 px plots, so "fuel flow (kg/h)" and "mean gap size (kg)" run past their panels into the row gap and next to the neighbouring panel.
  - The "optimiser-gap count" subplot title touches the row-1 tick labels "eastbound"/"westbound" (1–2 px overlap, measured with `qa/T27/scratch/overlap.js`). That list is partial: the script checks only first-axis titles and ticks, so the y2–y4 title overruns were seen in the screenshot, not measured. The FAIL rests on the 56 px plot areas alone. B6's copy of `overlap.js` has the same limit.
  - The rotated source labels take more height than the bars do.
  - The boxes remain legible, but only just. The lead-regret figure (B6) fixed the same problem with an explicit height (≥ 650 px).
- Minor:
  - The four box traces use Plotly's default colours (`#636efa`, `#EF553B`, teal, `#ab63fa`), not `style`.
  - The "maximum fuel flow" purple is close to Pangu-Weather's `#9467bd` in the panel below. A reader could link the two, though they are unrelated.

### 5b. Fuel-flow range: inside 4,000–8,000 kg/h ✔

- Minimum fuel flow: 6,381–6,773 kg/h (median 6,594).
- Maximum fuel flow: **7,370.6 kg/h on all 2,520 rows**, so its box collapses to one flat line at the top of the panel.
- This is a property of the model, not a figure bug. In `replay.py` the cruise fuel flow depends only on mass, at a fixed TAS and flight level. Every plan starts at `initial_mass_kg()`, so the maximum is always the first segment's flow.
- The panel is fine as a sanity check, but its "range" only shows how much the aircraft lightened. A reader with no caption may take the flat line for a bug. That is worth a caption, perhaps in B8.

### 5c. Gap panels with 12 gaps

- **Count panel: makes sense.** The bars read 6 / 5 / 1 / 0, and the integer axis is clear.
- **Size panel: makes sense, with caveats:**
  - Each bar is a mean over n = 6, 5 and 1 gaps, but n and the spread are not shown. For example, Pangu-Weather's 0.14 kg bar is a single plan.
  - The gaps are tiny: at most 4.7 kg against trip fuel of 33–58 t, which is about 0.01%. That is the reassuring message a sanity panel should give, but the figure does not say it.
- **Persistence baseline:** the slot is empty in both panels (count 0, mean NaN), with no label. A reader cannot tell "no gaps" from "missing". A "0" or "n/a" annotation would settle it.

### Physical plausibility

- **Replay times:**
  - eastbound 281–372 min (median 5.35 h);
  - westbound 389–511 min (median 6.99 h).
  - Over the 5,540 km LHR–JFK great circle, these imply mean ground speeds of **638 kt** (fastest eastbound), 559 kt (eastbound median), 428 kt (westbound median) and 351 kt (slowest westbound).
  - The fastest eastbound replay, 4 h 41 min, is very quick for a subsonic airliner. It is plausible only with a strong jet-stream tailwind and the model's constant-TAS cruise with no climb or descent.
  - Medians are short of real block times for the same reason (no climb, descent or taxi).
  - This is an observation, not a failure.
- **Trip fuel** (`fuel_kg`, not plotted here):
  - eastbound 33.1–43.2 t;
  - westbound 45.1–58.2 t, with **283 westbound plans above 50 t**.
  - This is internally consistent: about 7 t/h (median `fuel_kg / time`, 6,961 kg/h) × 7–8.5 h. So the > 50 t values follow from the long westbound times and the fuel-flow level, not from an arithmetic error. Whether about 7 t/h suits the modelled type is a model question, outside this figure.

## Failures reported to the lead

1. **Step 5a (reader view, JupyterLab).**
   - **Expected:** each panel is readable in the notebook.
   - **Actual:** the figure renders 360 px tall in JupyterLab, with 56 px plot areas. The y titles run past their panels, and the "optimiser-gap count" title touches the row-1 tick labels.
   - **Suggested owner:** `sanity.py` (an explicit height, as `lead_regret` has).

Minor, not failures:
- the box hover has no unit, and the `hovertemplate` is ignored;
- the box colours don't come from `style`;
- the empty persistence slot is unlabelled;
- n is not shown on the gap-size bars;
- the flat max-fuel-flow line has no caption.

## Housekeeping

- I stopped JupyterLab and the static server by PID, then confirmed both `curl` checks fail again. I closed the browser.
- Scratch files are in `qa/T27/scratch/` (gitignored): `make_nb.py`, `check.ipynb`, `fig.html`, `data_check.py`, `overlap.js`, and the logs.
