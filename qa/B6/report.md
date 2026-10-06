# B6 QA: wind error scatter readability and shared source colours

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `f3e7312`; the figures last changed in `79dc073` (B6), and `src/regret/figures/{wind_error,lead_regret,style,sanity}.py` had no uncommitted changes. The B7 builder's uncommitted edits were in `showcase_map.py` and its test only, which these figures don't import.
Browser: `playwright` MCP (Chrome), viewport 1200 × 807. Data: the full results that ship, `data/results/regret.parquet` (2,520 rows, of which 2,400 are forecast plans).

## Summary

| # | Check | Result |
|---|---|---|
| 1a | SNC: wind-error figure in JupyterLab | **PASS** |
| 1b | SBC on `qa/B6/scratch/wind.html`, *F* = `fig-wind-error` | **PASS** |
| 1c | Hover on a forecast point and a persistence point shows the flight, source and lead (h) | **PASS** (real `page.mouse.move`) |
| 1d | Point count = 2,400 | **PASS** (600 per source) |
| 1e | Reader view: sources distinguishable by colour and symbol | **FAIL for the bulk** (they can be told apart only in the legend and the tail) |
| 1f | Reader view: wind-error vs regret relationship visible in the forecast panel | **FAIL for the bulk** (visible only as a widening upper tail; the median trend spans 9.6 px of a 340 px panel) |
| 1g | Reader view: persistence clearly separate | **PASS** |
| 2a | Lead figure height ≥ 650 px | **PASS**: 700 px, both standalone and in JupyterLab |
| 2b | No collisions between titles, row titles and legend | **PASS standalone**, **FAIL in JupyterLab**: the legend box overlaps the "Forecast sources" row title by 3 px |
| 2c | Each line shows its source's marker symbol | **PASS** |
| 2d | Legend click hides a source in both panels | **PASS** |
| 2e | The CI legend key no longer toggles nothing (B6 check line) | **FAIL**: clicking it greys the key, and all 8 bands stay drawn |
| 3 | Each source has the same colour in the wind-error, lead-time and sanity figures | **PASS** |

## Step 1: wind-error scatter

### 1a. SNC

- `qa/B6/scratch/check.ipynb` was written by `scratch/make_nb.py` (nbformat) and has three cells:
  - Cell 1 calls `regret.offline.install_if_requested()`, then `os.chdir(<repo root>)`.
  - Cell 2 reads the full parquet, calls `build_wind_error(df)` and `fig.show()`, prints the counts, and writes `wind.html` with `write_html(..., include_plotlyjs=True, div_id=FIG_ID)`.
  - Cell 3 builds the lead-time figure, shows it so it can be measured in JupyterLab, and writes `lead.html` and `sanity.html` the same way.
- Neither server was running (both `curl` checks exited 7). I started both with the exact *Shared runtime resources* commands.
- JupyterLab's restored workspace reopened `qa/T21/scratch/check.ipynb`. I closed it with Discard, so that file was unchanged.
- I chose Run → Run All Cells through the real menu, then polled until Idle.
- `browser_evaluate` results:
  - `.jp-OutputArea .js-plotly-plot`: **2**, the wind figure and the lead figure ✔
  - `[data-mime-type="application/vnd.jupyter.stderr"]`: **0** ✔
  - Status bar: `Python 3 (ipykernel) | Idle` ✔
  - Prompts: `[1]`, `[2]`, `[3]`
- Stdout: `rows 2520 forecast_plan_rows 2400`; `rows_per_source {'hres': 600, 'graphcast': 600, 'pangu': 600, 'persistence': 600}`; `traces [('IFS HRES', 600), ('GraphCast', 600), ('Pangu-Weather', 600), ('Persistence baseline', 600)]`.
- JupyterLab's console logged 3 × "A kernel is required to send debug messages". This is the same debugger-panel noise B5 saw, and SNC does not check the console.
- The wind figure renders 520 px tall in JupyterLab, with no collisions between the title, the subplot titles, the axis titles and the legend.
- Screenshot: `qa/B6/notebook.png`.

### 1b. SBC

- Navigating away from JupyterLab raised a `beforeunload` dialog. I accepted it and then loaded the page fresh, so the logs below are from a clean load.
- `#fig-wind-error .main-svg`: **3** ✔
- Console errors: **1**, the allowed `/favicon.ico` 404 ✔
- Network: only `GET http://127.0.0.1:8765/qa/B6/scratch/wind.html → 200` ✔
- Screenshot: `qa/B6/wind.png`, full page, taken before any interaction. It is also saved as `qa/B6/chrome.png`, the name in the PLAN check line.

The layout, from `gd._fullLayout` and `_fullData`:

- The title reads "Wind error vs fuel regret, per forecast plan". The subplot titles read "Forecast sources" and "Persistence baseline".
- All 4 axes are `linear`, and each panel has its own x and y axis:
  - forecast panel: x −1.1…30.8 m/s, y −239…3,801 kg;
  - persistence panel: x 4.7…77.2 m/s, y −616…9,791 kg.
- Each plot area is 417 × 340 px.

| Trace | Axes | Colour | Symbol | Size | Opacity |
|---|---|---|---|---|---|
| IFS HRES | x/y | `#1f77b4` | circle | 5 | 0.5 |
| GraphCast | x/y | `#2ca02c` | diamond | 5 | 0.5 |
| Pangu-Weather | x/y | `#9467bd` | square | 5 | 0.5 |
| Persistence baseline | x2/y2 | `#7f7f7f` | x | 5 | 0.5 |

The legend uses the `SOURCE_LABELS` names.

### 1c. Hover

I did not retry `browser_hover`, because T25 showed that Plotly's drag layer intercepts it. Instead I used the *Plotly interactions* rule, which accepts a real mouse move. With `browser_run_code_unsafe`, I moved the real mouse (`page.mouse.move`, 5 steps) onto pixel positions computed with `xaxis.c2p` and `yaxis.c2p`. I aimed at isolated points, so the snapped point is the one I meant.

| Aimed at | `.hoverlayer` text | Matches |
|---|---|---|
| Forecast panel, the highest-regret IFS HRES point (19.75 m/s, 3,561.8 kg) | `flight LHR-JFK-20200207T1200 · source hres · lead (h) 120 · wind error 19.75 m/s · fuel regret 3561.8 kg` | ✔ |
| Persistence panel, the highest-regret point (55.09 m/s, 9,175.2 kg) | `flight LHR-JFK-20200207T1200 · source persistence · lead (h) 72 · wind error 55.09 m/s · fuel regret 9175.2 kg` | ✔ |

Each label has a flight ID, a source and a lead in hours ✔. Screenshots: `qa/B6/hover-forecast.png` and `qa/B6/hover-persistence.png`.

In the dense corner the hover is not reliable. I aimed at an IFS HRES point at 2.49 m/s and 5.9 kg, and the label showed a **Pangu-Weather** point (`LHR-JFK-20200229T1200`, 48 h, 2.60 m/s, 0.0 kg). T25 saw the same thing, and the overlap counts in 1f explain it.

The hover's `source` field shows raw IDs (`hres`, `persistence`), while the legend uses `SOURCE_LABELS`. This is minor and not checked.

### 1d. Point count

- Decoded `gd._fullData[i]._length`: 600, 600, 600 and 600, **total 2,400** ✔
- Rendered `.points path` per trace: 600, 600, 600 and 600 ✔
- The notebook printed `forecast_plan_rows 2400`, which is 2,520 rows minus the 120 truth-optimised ones.

### 1e–1g. Reader view

I measured every point's pixel position in the browser, using `calcdata` and `c2p` on the forecast panel's 417 × 340 px plot area. Spearman ρ comes from Python on the same data.

**The forecast panel holds 1,800 points.** The numbers below show how they are spread.

| Measure | Value |
|---|---|
| Central 5–95% box (x × y) | 163.7 × 21.8 px = **2.5% of the panel** (this matches the builder's measurement) |
| IQR box | 59.2 × **4.6 px** |
| Scale | 100 kg = 8.4 px; the zero line is 20 px above the bottom of the plot |
| Points within 10 px of the zero line | **1,575 of 1,800 (88%)** |
| Points under 100 kg | 1,536 of 1,800 |
| Point pairs closer than 5 px (the marker size) | **125,255**; 38,314 pairs are closer than 2 px |
| Points with no neighbour within 5 px | **60 of 1,800 (3%)** |

**How regret rises across wind-error quintiles** (forecast panel; heights in px above the bottom of the plot, where the zero line sits at 20.1 px):

| Wind error (m/s) | Median regret | Median height | 90th-percentile regret | 90th-percentile height |
|---|---|---|---|---|
| 0.7–2.0 | 0.0 kg | 20.1 px | 16.4 kg | 21.5 px |
| 2.0–3.0 | 3.1 kg | 20.4 px | 31.5 kg | 22.8 px |
| 3.0–4.6 | 15.4 kg | 21.4 px | 52.9 kg | 24.6 px |
| 4.6–7.7 | 33.2 kg | 22.9 px | 128.2 kg | 30.9 px |
| 7.7–29.0 | 113.7 kg | 29.7 px | 429.7 kg | 56.3 px |

**Spearman ρ between wind error and regret:**

| Source | ρ | Zero-regret plans | Median regret | 95th percentile | Max |
|---|---|---|---|---|---|
| IFS HRES | 0.76 | 153 of 600 | 17.0 kg | 371 kg | 3,562 kg |
| GraphCast | 0.69 | 140 | 15.5 kg | 193 kg | 1,789 kg |
| Pangu-Weather | 0.69 | 157 | 15.8 kg | 233 kg | 1,940 kg |
| Forecast sources pooled | 0.71 | | | | |
| Persistence baseline | 0.43 | 1 | 677 kg | 2,635 kg | 9,175 kg |

**The persistence panel holds 600 points.** Its 5–95% box is 208 × 84 px, 12.3% of the panel. 1,269 pairs are closer than 5 px, and 104 points have no neighbour within 5 px.

**Judgement:**

- **1e. Are the sources distinguishable?** Partly.
  - They are distinguishable in the legend, and among the outliers above about 300 kg and to the right of about 10 m/s. There, the blue circles, green diamonds and purple squares can each be told apart (`qa/B6/wind.png`).
  - In the bulk, which holds 88% of the points within 10 px of zero, they can't be told apart. The 2× device-pixel crop `qa/B6/wind-corner.png` shows a solid band 0–10 px tall, about 160 px long. Pangu-Weather is drawn last, so its purple dominates. At 5 px and 0.5 opacity, the circle, diamond and square shapes can't be read where the points overlap, and 97% of forecast points overlap another within 5 px.
- **1f. Is the wind-error vs regret relationship visible?**
  - It is visible only as a **widening upper tail**. The 90th percentile rises 35 px across the quintiles, and all 13 forecast plans above 1,000 kg have wind errors of 5.3 m/s or more (pandas query). A reader would correctly see "bigger wind errors allow much bigger regrets".
  - The **central tendency is not visible**. The median rises 9.6 px across the whole wind-error range, and the IQR band is 4.6 px tall. Yet the data has a clear monotone relationship (ρ 0.69–0.76).
  - The cause is that regret is heavy-tailed. The y range runs to 3,800 kg, set by a single 3,562 kg HRES point, while the median is 15–17 kg.
  - B6 removed T25's flaw, where persistence squashed the forecast cluster: it now has its own axis. But the forecast sources' own tail now does the same thing to their bulk. (T25's 2.4% measured something else: the full bounding box of 90 fixture points, so the two figures can't be compared.) So for the bulk, this does **not** yet meet B6's "relationship is visible" criterion.
  - Possible fixes are a design choice for the lead or builder: clip the y range at about the 99th percentile and annotate the outliers, use a symlog-style axis, or add binned medians as a line overlay.
- **1g. Is persistence clearly separate?** Yes.
  - It has its own panel and title, its own linear axes, a different colour (grey) and a different symbol (x).
  - Its 5–95% box covers 12.3% of its panel, and its cloud is readable.
  - Within persistence, the relationship is weak (ρ 0.43). The two largest regrets, 8.8k and 9.2k kg, sit at 40–55 m/s, and the largest errors, about 70 m/s, have regrets under 3k kg. The figure shows this honestly.

## Step 2: lead-time figure (`qa/B6/scratch/lead.html`)

- SBC: `#fig-lead-regret .main-svg` = 3; **0** console errors; network shows only `lead.html → 200` ✔.
- Screenshot: `qa/B6/lead.png`.

### 2a. Height

- Standalone: the rendered height is **700 px** (`layout.height` 700). Each row's plot is 249 px tall ✔.
- In JupyterLab (cell 3, 768 px wide): also **700 px** ✔. B5's 360 px squeeze is gone.

### 2b. Collisions

I tested every pair of `.gtitle`, `.annotation` (the column titles and the row titles), the x and y titles, and `g.legend` for intersecting `getBoundingClientRect` boxes.

- **Standalone (1,184 px wide):** 9 elements, **0 intersections** ✔.
- **JupyterLab (768 px wide):** **1 intersection.** ✘
  - The `g.legend` box spans x 967–1134 and y 1329–1493.
  - The "Forecast sources" row-title annotation spans x 947–970 and y 1385–1522.
  - So they overlap by **3 px horizontally**, over 108 px vertically.
  - The crop `qa/B6/notebook-lead.png` shows the vertical row title right up against the legend's line swatches (IFS HRES … Persistence baseline). Their glyphs touch rather than overlap. It is legible but cramped.
  - The cause is width-dependent: the legend sits at paper x = 1.02, which is only 0.02 of the plot width past the right edge. The row title sits at a fixed offset beyond that edge. So the narrower notebook output squeezes them together.
  - B5's other collisions are gone: the two y titles no longer overlap each other, and the two row titles no longer run into each other.

### 2c. Marker symbols

I read these from each rendered trace's bound `__data__` and its `.points path` `d` attribute.

| Source | Symbol | Panels | Line colour = marker colour |
|---|---|---|---|
| IFS HRES | circle | `x`, `x2` | `#1f77b4` ✔ |
| GraphCast | diamond | `x`, `x2` | `#2ca02c` ✔ |
| Pangu-Weather | square | `x`, `x2` | `#9467bd` ✔ |
| Persistence baseline | x | `x3`, `x4` | `#7f7f7f` ✔ |

- Each line has 5 markers, one per lead.
- The legend swatches show the same symbols.
- These are the same symbols the scatter uses ✔.

### 2d. Legend click

I clicked each source's `.legendtoggle` with a real `browser_run_code_unsafe` locator click, then waited 700 ms.

| Click | Legend opacity | Traces set to `legendonly` | Rendered traces (`x` / `x2` / `x3` / `x4`) | Bands drawn |
|---|---|---|---|---|
| Before any click | all 1 | none | 7 / 6 / 2 / 2 | 8 |
| IFS HRES | 0.5 (others 1) | HRES band and line on `x` and `x2` | **5 / 4** / 2 / 2 | 6 ✔ |
| Persistence baseline | 0.5 | Persistence band and line on `x3` and `x4` | 7 / 6 / **0 / 0** | 6 ✔ |

After each check I clicked the entry again, and the figure returned to the starting state.

Screenshots: `qa/B6/lead-click-hres.png` and `qa/B6/lead-click-persistence.png`.

### 2e. CI legend key ✘

- Clicking "shaded: 90% CI" changes the key's legend opacity from 1 to **0.5**. Only the dummy key trace becomes `legendonly`.
- The rendered `.js-fill` bands stay at **8**, so every CI band is still drawn.
- The code gives the key `legendgroup="ci"`, but no band is in that group, so clicking it still has no visible effect.
- This is B5's minor finding #4, unchanged. B6's check line requires "the CI legend key no longer toggles nothing (give it no click effect or a clear legend group)".
- Screenshot: `qa/B6/lead-click-ci.png`.

## Step 3: colour consistency

I read the colours from the rendered DOM (`getComputedStyle`), not only from the figure JSON, and normalised `rgb()` to hex:

- wind error: each point's `fill` and each legend swatch;
- lead time: the line `stroke`, the marker `fill` and the band `fill`, whose base colour is drawn at fill-opacity 0.2;
- sanity: each bar's `fill`, mapped to its x category through `xaxis3._categories` and `xaxis4._categories`.

| Source | `style.SOURCE_COLOURS` | Wind error | Lead time (line / marker / band) | Sanity (gap count / gap size) |
|---|---|---|---|---|
| hres | `#1f77b4` | `#1f77b4` | `#1f77b4` / `#1f77b4` / `#1f77b4` | `#1f77b4` / `#1f77b4` |
| graphcast | `#2ca02c` | `#2ca02c` | `#2ca02c` ×3 | `#2ca02c` ×2 |
| pangu | `#9467bd` | `#9467bd` | `#9467bd` ×3 | `#9467bd` ×2 |
| persistence | `#7f7f7f` | `#7f7f7f` | `#7f7f7f` ×3 | `#7f7f7f` ×2 |

All four sources have the same colour in all three figures ✔.

- The sanity page passed its own load check: `.main-svg` = 3 and 0 console errors.
- Screenshot: `qa/B6/sanity.png`.

Two notes that are not checked:

- The CI band traces' invisible outline (`stroke-width: 0`) still carries Plotly default colours (`#636efa`, `#ffa15a` …). Nothing is drawn, so a reader never sees them.
- The sanity figure's x axis shows raw IDs (`hres`, `graphcast` …), and so does the scatter hover's `source` field, where the legends use `SOURCE_LABELS`.

## Failures reported to the lead

1. **Step 2e, the CI legend key.**
   - Expected: the "shaded: 90% CI" entry either has no click effect, or hides the bands as a clear legend group.
   - Actual: clicking it greys the key to opacity 0.5, and all 8 CI bands stay drawn. Its `legendgroup="ci"` contains no bands.
2. **Step 2b, a collision in JupyterLab.**
   - Expected: no `getBoundingClientRect` intersection between the titles, row titles and legend.
   - Actual: at the notebook's 768 px output width, `g.legend` (x 967–1134) overlaps the "Forecast sources" row title (x 947–970) by 3 px. The glyphs touch, and the text stays legible. There are 0 intersections standalone at 1,184 px.
3. **Step 1f, the reader view.**
   - Expected: the wind-error vs regret relationship is visible in the forecast panel.
   - Actual: it is visible only as a widening upper tail.
     - The 5–95% box is 2.5% of the panel, and the IQR band is 4.6 px tall.
     - The median rises 9.6 px across the full wind-error range, against ρ 0.69–0.76 in the data.
     - 88% of the points are within 10 px of zero, and 97% overlap a neighbour within 5 px.
4. **Step 1e, the reader view.**
   - Expected: the forecast sources can be told apart by colour and symbol.
   - Actual: they can be told apart in the legend and among the points above about 300 kg. In the bulk (88% of points within 10 px of zero), the 5 px, 0.5-opacity markers merge into one band in which Pangu-Weather's purple dominates (`qa/B6/wind-corner.png`).

Every other step passed.

## Teardown

- JupyterLab (8888) and the static server (8765) were stopped by PID (`qa/B6/scratch/*.pid`).
- Afterwards both `curl` checks exit 7, and `lsof` shows nothing listening on either port.
- The browser was closed.

---

# Attempt 2 (34fa4c4)

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `ba6146f`. The figures under test are also unchanged at `0b8b5b7`, the B7 commit that landed during the run. The figures last changed in `34fa4c4`, and `src/regret/figures/{wind_error,lead_regret,sanity,style}.py` had no uncommitted changes. The only uncommitted change at the start was the B7 builder's `showcase_map.py`, which these figures don't import.
Browser: `playwright` MCP (Chrome), viewport 1200 × 807, the same as attempt 1, so the JupyterLab output is **768 px** wide (measured on `.js-plotly-plot`).
Data: everything ran on the full results, `data/results/regret.parquet` (2,400 forecast plans). That includes the notebook, which is stricter than the fixture the lead allowed.

## Summary

| # | Check | Result |
|---|---|---|
| 1a | SNC in JupyterLab (`qa/B6/scratch/check2.ipynb`) | **PASS** |
| 1b | SBC on a fresh `qa/B6/scratch/wind2.html`, *F* = `fig-wind-error` | **PASS** |
| 1c | Hover on a pinned marker shows its true regret, flight, source and lead | **PASS**, with a hover-precision note |
| 1d | Hover on a median-line point | **PASS** |
| 1e | Plotted points + pinned points = 2,400 | **PASS**: 2,376 + 24 |
| 1f | The annotations' counts and maximums | **PASS** |
| 1g | No layout intersections in the wind-error figure, standalone (1,184 px) and in JupyterLab (768 px) | **PASS** |
| 2a | Reader view: the per-source median lines are distinguishable | **PASS, qualified**: they separate in bins 6–8 and coincide in bins 1–5, where the medians are within 7 kg of each other |
| 2b | Reader view: the median lines rise with wind error | **PASS** |
| 2c | Reader view: the points serve only as context | **PASS** |
| 2d | Reader view: no plan is hidden | **FAIL (minor)**: the two cap annotations' boxes cover 11 plotted plans. Pins and annotations are otherwise correct. |
| 3a | Lead figure: CI annotation present, no "90% CI" legend entry, legend horizontal | **PASS** |
| 3b | Lead figure: no intersections, standalone and in JupyterLab | **PASS**. Attempt 1's 3 px collision at 768 px is gone. |
| 3c | Lead figure: a legend click hides a source in both panels | **PASS** |
| 4 | Sanity figure: x axis shows source labels | **PASS** |
| 5 | Same colour per source across the wind-error, lead-time and sanity figures | **PASS** |

## Setup

- Neither server was running (both `curl` checks exited 7). I started both with the exact *Shared runtime resources* commands (JupyterLab with `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture`).
- `qa/B6/scratch/make_nb2.py` writes `check2.ipynb`, which has three cells:
  - Cell 1 calls `regret.offline.install_if_requested()`, then `chdir`s to the repo root.
  - Cell 2 calls `build_wind_error` on the full parquet, shows the figure and writes `wind2.html`.
  - Cell 3 calls `build_lead_regret` (and shows it), then `build_sanity`, and writes `lead2.html` and `sanity2.html`.
  - Every HTML file uses `write_html(..., include_plotlyjs=True, div_id=FIG_ID)`. I deleted any old `*2.html` first, so the pages are fresh.
- JupyterLab's workspace restored attempt 1's `check.ipynb`. I closed it with Discard, so the file is unchanged.
- Reference values came from Python (`scratch/ref2.py`), computed independently of the browser.

## Step 1: wind-error scatter

### 1a. SNC

- I chose Run → Run All Cells through the real menu.
- Prompts: `[1]`, `[2]`, `[3]`.
- `.jp-OutputArea .js-plotly-plot`: **2** ✔
- `[data-mime-type="application/vnd.jupyter.stderr"]`: **0** ✔
- Status bar: `Python 3 (ipykernel) | Idle` ✔
- Both outputs measure 768 px wide. The wind figure is 580 px tall and the lead figure 700 px.
- JupyterLab's console logged the same 3 × "A kernel is required to send debug messages" debugger noise as attempt 1. SNC does not check the console.
- Screenshots: `qa/B6/notebook-attempt2.png` (wind) and `qa/B6/notebook-lead-attempt2.png`.

### 1b. SBC on `wind2.html`

- I accepted JupyterLab's `beforeunload` dialog, then loaded the page fresh.
- `#fig-wind-error .main-svg`: **3** ✔
- Console errors: **0** ✔ (no favicon 404 this time either)
- Network: only `GET http://127.0.0.1:8765/qa/B6/scratch/wind2.html → 200` ✔
- Screenshot: `qa/B6/chrome-attempt2.png`, full page, taken before any interaction. This is the `chrome.png` the PLAN check line asks for. I didn't overwrite attempt 1's `chrome.png`.

The layout, from `gd._fullLayout` and `_fullData`:

- All 4 axes are `linear`.
  - Forecast panel: y −22.7…757.1 kg, x −1.1…30.8 m/s.
  - Persistence panel: y −136.6…4,554.3 kg, x 4.7…77.1 m/s.
- Each plot area is 471 × 340 px standalone.

| Trace kind | Size | Opacity | Outline | In legend |
|---|---|---|---|---|
| Faint points (per source) | 4 | 0.25 | none | only Persistence baseline |
| "… (median)" lines, forecast panel only | 9, plus a 3 px line | 1 | white 1 px | yes |
| "… (above range)" pins | 9 | 1 | black 1.5 px | no |

Each source keeps its symbol: IFS HRES circle, GraphCast diamond, Pangu-Weather square, Persistence baseline x.

### 1c–1d. Hover

I used a real `page.mouse.move` through `browser_run_code_unsafe`, as the *Plotly interactions* rule allows. Positions came from `c2p` plus the axis offsets.

| Aimed at | `.hoverlayer` text |
|---|---|
| IFS HRES pin, 19.75 m/s (true 3,561.8 kg), 4 px right of centre | `flight LHR-JFK-20200207T1200 · source IFS HRES · lead (h) 120 · wind error 19.75 m/s · true fuel regret 3,561.8 kg (above the plotted range)` ✔ |
| Persistence pin, 55.09 m/s | `flight LHR-JFK-20200207T1200 · source Persistence baseline · lead (h) 72 · wind error 55.09 m/s · true fuel regret 9,175.2 kg (above the plotted range)` ✔ |
| IFS HRES median, bin 8 | `IFS HRES (median) · median wind error 12.99 m/s · median fuel regret 226.8 kg` ✔ |

- The source field now uses `SOURCE_LABELS` ("IFS HRES", "Persistence baseline"), not raw ids ✔. This fixes attempt 1's note.
- Screenshots: `qa/B6/hover-pinned-attempt2.png` and `qa/B6/hover-median-attempt2.png`.

**Hover-precision note (not a failure):**

- With the mouse exactly on the centre of the 3,562 kg HRES pin, the label shows the **GraphCast** pin at 19.60 m/s (1,422.3 kg). That pin sits 2.2 px away and is drawn later.
- Sweeping in 1 px steps, the HRES 3,562 kg label appears only from +3 to +6 px right of centre.
- I swept the three tightest pin pairs in 0.5 px steps. Every plan in them can be reached by hover:
  - GraphCast 7.27 / Pangu-Weather 7.18 m/s, 1.3 px apart;
  - Persistence 31.73 / 31.52 m/s, 1.4 px apart;
  - HRES 18.68 / 18.84 m/s, 2.3 px apart.

### 1e. Point count ✔

`_fullData[i]._length` over the faint and "(above range)" traces, leaving out the three median traces:

| Source | Plotted | Pinned | Total |
|---|---|---|---|
| IFS HRES | 591 | 9 | 600 |
| GraphCast | 594 | 6 | 600 |
| Pangu-Weather | 597 | 3 | 600 |
| Persistence baseline | 594 | 6 | 600 |
| **Total** | **2,376** | **24** | **2,400** |

The rendered `.points path` counts are the same.

### 1f. Annotations ✔

| Panel | Annotation text | Python check |
|---|---|---|
| Forecast | "18 plans above 757 kg shown at top edge (max 3,562 kg)" | 18 rows > 757.1 kg (HRES 9, GraphCast 6, Pangu 3); max 3,561.8 ✔ |
| Persistence | "6 plans above 4,554 kg shown at top edge (max 9,175 kg)" | 6 rows > 4,554.3 kg; max 9,175.2 ✔ |

- The pinned customdata values run from 861.6 to 3,561.8 kg (forecast) and from 4,925.7 to 9,175.2 kg (persistence). All of them are above their caps.
- The caption under the plot reads: "Lines: binned median of each source (8 common wind-error bins); faint points: single plans".

### 1g. Layout intersections ✔

I tested `getBoundingClientRect` pairs over `.gtitle`, `.annotation`, `.xtitle`, `.ytitle`, `g.legend`, `.xtick text` and `.ytick text`:

- Standalone at 1,184 px: 24 elements, **0** intersections. The legend fits on 1 row.
- JupyterLab at 768 px: 21 elements, **0** intersections. The legend wraps to 2 rows (three "(median)" entries, then "Persistence baseline"), and the caption stays clear below it, 17 px above the figure's bottom edge. Nothing falls outside the figure.

## Step 2: reader view (revised criterion)

All measurements are on the standalone forecast panel: plot area 471 × 340 px, 2.29 kg/px, zero line at 330.1 px from the top.

**Medians per bin.** The common interior bin edges are 1.66, 2.24, 2.84, 3.68, 4.96, 6.77 and 9.99 m/s. All 8 bins have at least 15 points per source.

| Bin | HRES (kg) | GraphCast (kg) | Pangu (kg) | Vertical spread across the 3 lines (px) | Pairwise gaps H–G / H–P / G–P (px) | Spread in bin x positions (px) |
|---|---|---|---|---|---|---|
| 1 (~1.3 m/s) | 0.0 | 0.0 | 0.0 | 0.0 | 0 / 0 / 0 | 2.0 |
| 2 | 0.0 | 1.5 | 0.0 | 0.7 | 0.7 / 0 / 0.7 | 0.2 |
| 3 | 3.9 | 3.0 | 4.5 | 0.7 | 0.4 / 0.3 / 0.7 | 0.6 |
| 4 | 8.1 | 9.3 | 7.8 | 0.7 | 0.6 / 0.1 / 0.7 | 1.5 |
| 5 | 23.8 | 16.8 | 18.3 | 3.1 | 3.1 / 2.4 / 0.7 | 1.7 |
| 6 | 32.3 | 41.1 | 20.8 | 8.8 | 3.8 / 5.0 / 8.8 | 2.0 |
| 7 | 56.9 | 52.2 | 64.5 | 5.3 | 2.0 / 3.3 / 5.3 | 1.9 |
| 8 (~13 m/s) | **226.8** | **131.1** | **158.8** | **41.8** | 41.8 / 29.7 / 12.1 | 3.9 |

From the first bin to the last, each line rises: HRES 0.0 → 226.8 kg (98.9 px), GraphCast 0.0 → 131.1 kg (57.1 px), Pangu-Weather 0.0 → 158.8 kg (69.2 px). Attempt 1's median rose 9.6 px.

**2a. Are the median lines distinguishable?** Yes, where the data differ. The verdict is qualified.

- In **bins 6–8** (wind error above about 5 m/s), each line can be told apart by colour and symbol. At bin 8 they end 12–42 px apart, and their order (HRES > Pangu > GraphCast) is clear (`qa/B6/wind-medians-attempt2.png`).
- In **bins 1–5**, the three medians are within 7 kg of each other, so their vertical spread is 0–3.1 px against a 9 px marker. The markers sit on top of each other, and Pangu-Weather's squares, drawn last, cover the HRES circles and GraphCast diamonds. A reader sees one purple line there.
- This is a statistical tie in the data, not a drawing defect, like the B5 precedent ("lines overlap at 12–24 h because the sources are statistically tied"). No line is hidden along its whole length.
- The lead should decide whether "distinguishable" is met by separation only above about 5 m/s.

**2b. Do they rise with wind error?** Yes. All three lines are monotone non-decreasing across the 8 bins, and the rise is now 57–99 px tall.

**2c. Do the points serve only as context?** Yes.

- The points are 4 px at 0.25 opacity. The medians are 9 px opaque markers on a 3 px line, with a white outline.
- The faint forecast points have no legend entry. Clicking a median's legend entry hides that source's whole group, because they share a legendgroup.
- Draw-order note (`.scatterlayer .trace` order): HRES points → HRES median → HRES pins → GraphCast points → GraphCast median → … → Pangu pins. So the GraphCast and Pangu faint points are drawn over the HRES median line, and the Pangu points over the GraphCast median. At 0.25 opacity this only dims the lines, and I could still see every segment from bin 5 up.
- Minor: the legend key for "Persistence baseline" is its faint 4 px, 0.25-opacity x, which is barely visible (`chrome-attempt2.png`).

**2d. Is any plan hidden?** No plan is lost, but 11 are visually covered. ✘ (minor)

What works:

- Every plan above a cap is pinned: 18 forecast and 6 persistence. Each sits at `top − 4%`, which is 725.9 kg and 4,366.6 kg (13.6 px below the top edge). Each has its true value in hover, and the annotation gives the count and maximum.
- **No real point sits above or near the pinned row.** The highest plotted plans are 699.4 kg and 4,209.7 kg, and none is within 9 px of the row. So a reader can't mistake a real point for a pinned one.

What doesn't:

- **The annotation boxes cover points.** Each cap annotation has a white box at 0.75 opacity in its panel's upper left: forecast x 98–333, y 106–137; persistence x 651–890, y 106–137.
  - Underneath are **8 forecast plans** (4 HRES, 1 GraphCast, 3 Pangu) and **3 persistence plans**.
  - A 0.25-opacity point under a 0.75 white box shows at about 6% contrast, so these plans can't be seen. They are in the 600–700 kg (forecast) and 3,700–4,200 kg (persistence) range, which is the sparse tail where each point is meant to show.
  - These counts were measured standalone at 1,184 px, where the forecast box spans about half the panel's width. In JupyterLab at 768 px the box keeps its width but the panel shrinks, so the box spans about 85% of it (up to about 27 m/s, against about 15.5 m/s standalone; `notebook-attempt2.png`). More plans are likely covered there. I didn't measure that count.
- **Coincident pins.** Seven forecast pin pairs and two persistence pairs are closer than 9 px, the marker size. The closest are 1.3 px (GraphCast 7.27 / Pangu 7.18 m/s), 1.4 px (persistence 31.73 / 31.52) and 2.2–2.3 px. Grouping pins closer than 9 px gives 12 clusters for the 18 forecast plans (7.18, 7.27 and 7.77 m/s form one cluster of three). Only 3 pairs are closer than 3 px, so a reader sees about 15 distinct pins. The annotation count and the hover (1c) still account for every one, so I report this as a note, not a failure.
- The pinned row sits just above the 700 kg gridline. A reader who skips the annotation could read the pins as about 725 kg. The annotation directly below the row reduces that risk.

## Step 3: lead-time figure (`lead2.html`)

- SBC: `.main-svg` = 3, **0** console errors, only `lead2.html → 200` ✔. Screenshot: `qa/B6/lead-attempt2.png`.
- **CI label** ✔:
  - The annotation "Shaded bands: 90% CI of the mean" is present.
  - The `.legendtext` entries are exactly "IFS HRES", "GraphCast", "Pangu-Weather" and "Persistence baseline". None is a CI entry.
  - All 8 "… 90% CI" traces have `showlegend=false`. Attempt 1's CI key that toggled nothing is gone.
- **Legend** ✔: `orientation: "h"`, on 1 row both standalone and at 768 px.
- **Intersections** ✔: 13 elements (titles, row and column titles, axis titles, ticks, legend, CI annotation), **0** intersections standalone at 1,184 px and **0** in JupyterLab at 768 px.
  - Attempt 1's 3 px collision between the legend and the "Forecast sources" row title is fixed, because the legend now sits below the plots.
  - In JupyterLab, the CI annotation sits 14 px above the figure's bottom edge.
- **Legend click** ✔: I used a real locator click on `.legendtoggle` and waited 700 ms.

| Click | Legend opacity | Set to `legendonly` | Rendered traces (`x` / `x2` / `x3` / `x4`) | `.js-fill` |
|---|---|---|---|---|
| Before | all 1 | none | 6 / 6 / 2 / 2 | 8 |
| IFS HRES | 0.5, others 1 | HRES line and CI on `x` and `x2` | **4 / 4** / 2 / 2 | 6 |
| Persistence baseline | 0.5 | Persistence line and CI on `x3` and `x4` | 6 / 6 / **0 / 0** | 6 |
| Toggled back | all 1 | none | 6 / 6 / 2 / 2 | 8 |

Screenshots: `qa/B6/lead-click-hres-attempt2.png` and `qa/B6/lead-click-persistence-attempt2.png`.

## Step 4: sanity figure (`sanity2.html`) ✔

- SBC load: `.main-svg` = 3, **0** console errors.
- The x tick text on both lower panels (`x3`, `x4`) reads "IFS HRES", "GraphCast", "Pangu-Weather", "Persistence baseline". These are no longer raw ids.
- Both axis titles read "forecast source". No tick labels overlap at 1,184 px.
- Screenshot: `qa/B6/sanity-attempt2.png`.

## Step 5: colours ✔

These are from rendered `getComputedStyle`:

| Source | `SOURCE_COLOURS` | Wind error (points / median line / median marker / pin) | Lead time (line / marker / CI band at 0.2) | Sanity (gap count / gap size bars) |
|---|---|---|---|---|
| hres | `#1f77b4` | `#1f77b4` ×4 | `#1f77b4` ×3 (both panels) | `#1f77b4` ×2 |
| graphcast | `#2ca02c` | `#2ca02c` ×4 | `#2ca02c` ×3 | `#2ca02c` ×2 |
| pangu | `#9467bd` | `#9467bd` ×4 | `#9467bd` ×3 | `#9467bd` ×2 |
| persistence | `#7f7f7f` | `#7f7f7f` (points, pins; no median line) | `#7f7f7f` ×3 | `#7f7f7f` ×2 |

## Failures reported to the lead

1. **Step 2d: annotation boxes cover plotted plans.**
   - Expected: no plan is hidden.
   - Actual: each cap annotation's 0.75-opacity white box (`bgcolor rgba(255,255,255,0.75)`, paper x 0.02 / y 0.92 of each panel) sits over faint 0.25-opacity points. 8 forecast plans (600–700 kg) and 3 persistence plans (3,700–4,200 kg) under them are effectively invisible.
   - These counts are standalone (1,184 px). At 768 px the box covers about 85% of the forecast panel's width, so more plans are likely covered there (not measured).
   - Pins, counts and maximums are otherwise correct.

Notes for the lead's judgement (not failures):

- **2a:** the median lines coincide in bins 1–5. The medians are within 7 kg of each other (≤ 3.1 px apart, under a 9 px marker), and Pangu-Weather is drawn on top. They separate only in bins 6–8 (8.8, 5.3 and 41.8 px). This is a data tie, as in B5.
- **Pins:** 7 forecast and 2 persistence pin pairs are under 9 px apart, the closest 1.3 px. Every plan is still counted in the annotation and reachable by hover. The 3,562 kg HRES pin's hover shows the GraphCast pin when the mouse is at its exact centre; the HRES label appears 3–6 px to the right.
- The "Persistence baseline" legend key is a faint 4 px x at 0.25 opacity and is hard to see.

## Teardown

- I closed the browser.
- I stopped JupyterLab (8888) and the static server (8765) by PID, and their children too. Afterwards both `curl` checks exit 7, and `lsof` shows nothing listening on either port.

# Final check (870cbdd)

Date: 2026-10-01 · Branch `grilltest` · HEAD `5572d59`. `wind_error.py` last changed in `870cbdd` · Browser: `playwright` MCP (Chrome), viewport 1200 × 1000, so the JupyterLab output is **768 px** wide and the standalone figure **1,184 px** · Data: the full results, `data/results/regret.parquet`.

The scope is only the user-approved fix: the two cap annotations moved above the panels. Everything else passed in attempt 2.

## Summary

| # | Check | 1,184 px standalone | 768 px JupyterLab |
|---|---|---|---|
| A1 | Each cap annotation is outside its panel's plot area | **PASS**: 26.5 px above the plot top | **PASS**: 26.5 px above |
| A1 | Plotted plans under an annotation box | **PASS: 0** (attempt 2: 11) | **PASS: 0** |
| A2 | Annotation text, counts and maximums unchanged | **PASS** | **PASS** |
| A3 | Layout intersections (title, subplot titles, cap annotations, note, legend, axis titles, ticks) | **PASS: 0** of 24 elements, none outside the figure | **PASS: 0** of 21, none outside |

**0 failures.**

## Setup

- Neither server was running (both `curl` checks exit 7). I started both with the *Shared runtime resources* commands. Their PIDs are in `qa/B7/scratch/final/*.pid`, since one pair served both reports.
- `scratch/final/make_nb.py` writes `scratch/check-final.ipynb`:
  - Cell 1 runs `regret.offline.install_if_requested()` and `chdir`s to the repo root.
  - Cell 2 runs `build_wind_error` on the full parquet, shows the figure and writes `scratch/wind-final.html` (`include_plotlyjs=True, div_id=FIG_ID`).
  - I deleted the old file first, so the page is fresh.
- The restored workspace reopened an old `check.ipynb`. I closed it, and nothing was saved.
- The measurement code is in `scratch/final/measure.js`:
  - Plot areas come from `_fullLayout.xaxis{,2}._offset/_length` and `yaxis{,2}`, plus the figure's `getBoundingClientRect`.
  - Annotation and layout boxes are `getBoundingClientRect` on `g.annotation`, `.gtitle`, `.xtitle`, `.ytitle`, `g.legend` and the tick texts.
  - Every drawn marker (`.points path.point`: faint points, pins and median markers) is tested for box overlap with each cap annotation.

## SNC (768 px)

- I chose Run → Run All Cells from the menu, and it finished in 4.0 s.
- `.jp-OutputArea .js-plotly-plot`: **1** ✔
- stderr: **0** ✔
- Status bar: `Idle` ✔
- stdout: `wrote wind-final.html 2520` (2,400 forecast plans plus the hindsight rows)
- Screenshot: `qa/B6/notebook-final.png`

## SBC on `wind-final.html` (1,184 px)

- `#fig-wind-error .main-svg`: **3** ✔
- Console errors: only the allowed `/favicon.ico` 404 ✔
- Network: only `GET 127.0.0.1:8765/qa/B6/scratch/wind-final.html → 200` ✔
- Screenshot: `qa/B6/chrome-final.png`, full page, taken before any interaction

## A1. Annotations outside the plot area; no plan covered ✔

| Width | Panel | Plot area (l, t, r, b) | Annotation box (l, t, r, b) | Intersects a plot area? | Gap to plot top | Markers under the box |
|---|---|---|---|---|---|---|
| 1,184 | Forecast | 88, 133, 559, 473 | 88.5, 75.5, 323.5, 106.5 | no | 26.5 px | **0** |
| 1,184 | Persistence | 641, 133, 1112, 473 | 641.5, 75.5, 880.5, 106.5 | no | 26.5 px | **0** |
| 768 | Forecast | 458, 460, 737.7, 800 | 458.5, 402.5, 693.5, 433.5 | no | 26.5 px | **0** |
| 768 | Persistence | 786.3, 460, 1066, 800 | 786.5, 402.5, 1025.5, 433.5 | no | 26.5 px | **0** |

- Each annotation now sits above its subplot title ("Forecast sources" and "Persistence baseline", 23 px tall), which itself sits directly on the plot area. So nothing in the data area is covered.
- No box is drawn behind the text any more (`bgcolor` was removed).
- At 768 px, the left annotation ends 93 px before the right panel's annotation begins.
- Every marker was tested: 2,376 faint points, 24 pins and 24 median markers. The drawn counts are unchanged from attempt 2: HRES 591 + 9, GraphCast 594 + 6, Pangu-Weather 597 + 3, Persistence 594 + 6.

## A2. Text, counts and maximums ✔

| Panel | Rendered text (both widths) | Python reference (`_y_range` on the parquet) |
|---|---|---|
| Forecast | "18 plans above 757 kg shown at top edge / (max 3,562 kg)" | 1,800 plans, cap 757.1 kg, **18** above, max **3,561.8** kg ✔ |
| Persistence | "6 plans above 4,554 kg shown at top edge / (max 9,175 kg)" | 600 plans, cap 4,554.3 kg, **6** above, max **9,175.2** kg ✔ |

The wording matches attempt 2. The only change is the `<br>` line break before "(max …)".

## A3. Layout intersections ✔

Elements measured: title, two subplot titles, two cap annotations, the note, legend, axis titles and tick labels (tick vs tick of the same axis skipped).

- **1,184 px:** 24 elements, **0** intersections, **0** outside the figure. The legend is on 1 row. From the top:
  - title y 15.6–36.1;
  - annotations y 75.5–106.5;
  - subplot titles y 109.5–132.5;
  - legend y 541–570;
  - note y 609.5–626.5;
  - figure bottom y 643.
- **768 px:** 21 elements, **0** intersections, **0** outside the figure. The legend wraps to 2 rows. From the top:
  - title y 342.6–363.2;
  - annotations y 402.5–433.5;
  - subplot titles y 436.5–459.5;
  - legend y 868–926;
  - note y 936.5–953.5;
  - figure bottom y 970.

The new risks were clipping at the top or crowding the main title. Neither happens: the title-to-annotation gap is 39 px at both widths. The figure height grew from 580 to 635 px.

## Failures reported to the lead

None.

## Teardown

See the B7 "Final check" section's teardown: one JupyterLab and one static server served both checks, and both were stopped at the end.
