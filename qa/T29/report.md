# T29 QA: notebook and report

Date: 2026-10-01 · Branch `grilltest` · HEAD `16ecf44` (B9 = `fde6d64`). The working tree was clean at the start.

- Browser: `playwright` MCP (Chrome).
- Data: fixture config (`REGRET_CONFIG=fixture`, `REGRET_BLOCK_NETWORK=1`), with 6 flights and 30 forecast plans per source. The reader view below was judged on this sample, so sparse panels may reflect the sample, not the design.
- `reports/report-fixture.html` is current (mtime 21:14:05, after B9's commit at 21:13:25), so I didn't regenerate it.
- Neither server was running (both `curl` checks exited 7). I started both with the exact *Shared runtime resources* commands and stopped them at the end (both `curl` checks exit 7 again, and nothing listens on 8888 or 8765).

## Summary

| # | Check | Result |
|---|---|---|
| 1a | JupyterLab Run All: 0 stderr outputs | **PASS** (0 stderr, 0 `application/vnd.jupyter.error`) |
| 1b | Exactly 5 `.jp-OutputArea .js-plotly-plot` | **PASS** (5 in the DOM at once, the five core IDs) |
| 1c | `elapsed_s` < 120 | **PASS**: `elapsed_s=3.7` |
| 1d | `qa/T29/notebook.png`; notebook not saved | **PASS, with a process note** (see step 1): JupyterLab's 120 s autosave wrote outputs to the tracked file before I could close it with Discard. I restored it with `git checkout`, and `git status` is clean. |
| 2a | JupyterLab: every sanity plot area ≥ ~180 px tall (B9) | **PASS**: 4 × 260 px tall (281 px wide) at a 768 px output area |
| 2b | JupyterLab: overlap sweep, all 5 figures | **PASS**: 0 intersections in each figure |
| 3a | SBC: `.main-svg` for all 5 IDs | **PASS** (3 each) |
| 3b | SBC: 0 console errors except favicon | **PASS** (1 error, the `/favicon.ico` 404) |
| 3c | SBC: no requests outside 127.0.0.1:8765 or `data:` | **PASS**: one request (`report-fixture.html`, read with `static: true`); `window.PlotlyGeoAssets.topojson` is present, so the basemap is inlined |
| 3d | "Assumptions and limitations" heading followed by 8 bullets | **PASS** (an `H3`, then a `UL` with 8 `LI`) |
| 4 | Report overlap sweep at 1,200 px and 768 px | **PASS**: 0 intersections in each figure at both widths |
| 5a | Order as in SPEC §5.2 | **PASS** |
| 5b | Captions match figures | **FAIL** (fixture): the wind-error scatter has no median lines, though both the caption and the in-figure note describe them |
| 5c | Headline table fully visible | **FAIL**: all 20 rows show, but at 1,200 px only 9 of 15 columns are visible (5 of 15 at 768 px); the rest need a sideways scroll |
| 5d | Showcase map shows the jet with the plans on it | **PASS** |
| 5e | Lead-time and scatter figures make the comparison readable | Lead time **PASS**; scatter **FAIL** (fixture), same cause as 5b |
| 5f | Limitations complete | **PASS**: all 8 SPEC §7 items, with 2 wording notes |
| 5g | No CONTEXT.md avoided words in visible text | **PASS**: every hit is a defined term or allowed in context (table below) |

## Failures for the lead

1. **Step 5c, headline table not fully visible.**
   - **Expected:** a reader sees the whole table (fuel, fuel %, time, CO₂ and zero-regret share; SPEC §5.2 item 1).
   - **Actual:** the table has a fixed width of 1,739 px (`layout.width`). The output `div` is 1,154 px wide at a 1,200 px viewport and 722 px at 768 px, and it clips with `overflow-x: auto`.
     - At 1,200 px, columns 10–15 are cut off at the right edge: Time median, Time p90, all three CO₂ columns, and Zero-regret share. "Time (r" is cut mid-word (`headline-1200.png`).
     - At 768 px, and in JupyterLab (768 px output area), only 5 columns are fully visible.
     - No horizontal scrollbar is visible in the screenshots (`headline-1200.png`, `notebook.png`), so nothing tells the reader that more columns exist.
     - **New finding, not a regression.** The 1,739 px width is B3 attempt 2's design. qa-B3 checked it on a standalone `fig.html`, where the page itself scrolls; its report records rows and headers, not horizontal clipping. The clipping comes from the notebook's and report's output area, which B3's QA didn't test.
     - Vertically, all 20 rows render: 315 cell texts = 15 headers + 300 cells, nothing clipped below the table, and the table's internal scrollbar has 0 width.
2. **Steps 5b and 5e, wind-error scatter on fixture data: no median lines and no forecast-source legend.**
   - **Expected:** the section 4 caption ("lines are each source's binned median") and the figure's own note ("Lines: binned median of each source (8 common wind-error bins)") are true, and a reader can tell the sources apart.
   - **Actual:** `report-fixture.html` has 5 traces, all `mode: markers`, and 0 `.js-line` paths. The legend has one entry, "Persistence baseline", because the forecast point traces set `showlegend: false` and the median traces carry the legend.
   - **Cause:** in `wind_error.py`, `_MIN_BIN_POINTS = 15`. With 30 plans per source over 8 bins, no bin qualifies, so no median trace is drawn.
   - The full `reports/report.html` is fine: it has 3 median traces (8 points each), 3 drawn lines and 4 legend entries.
   - So this affects only the fixture report and a fixture notebook run. Those are what T30 tests and what someone running the fixture config would see (`wind-1200.png`).

## Step 1: JupyterLab run-all

- I opened `http://127.0.0.1:8888/lab/tree/notebooks/regret_report.ipynb?token=regret-dev`. JupyterLab's restored workspace also reopened `qa/T27/scratch/check.ipynb`, a gitignored scratch file from T27, which I didn't run.
- I chose Run → Run All Cells through the real menu, then polled until `elapsed_s=` appeared and no prompt showed `[*]`.
  - The kernel was fresh: the execution counts were `[1]`–`[7]` for the 7 code cells.
  - The status bar read `Python 3 (ipykernel) | Idle`.
- **Results**, collected while scrolling the windowed notebook end to end. All 5 plots were also in the DOM at the same time:

  | Check | Result |
  |---|---|
  | `[data-mime-type="application/vnd.jupyter.stderr"]` | 0 |
  | `…jupyter.error` | 0 |
  | `.jp-OutputArea .js-plotly-plot` | 5: `fig-headline` 1739×1063, `fig-showcase-map` 748×760, `fig-lead-regret` 748×700, `fig-wind-error` 748×635, `fig-sanity` 748×780 |
  | stdout | `elapsed_s=3.7` |
  | output MIME types | only `text/html` and `application/vnd.jupyter.stdout` |

- Screenshot: `qa/T29/notebook.png`, showing the headline table at the top of the outputs. It also shows the table cut off at the right edge of the 768 px output area (finding 1).
- **Process note: autosave wrote the notebook.**
  - The notebook opened at 21:17:03 (+0800) and Run All finished within seconds.
  - JupyterLab's **autosave** (default interval 120 s) then saved both open documents. `jupyter.log` shows:
    - `21:19:03.760 Saving file at /qa/T27/scratch/check.ipynb`, a gitignored file from T27, also rewritten;
    - `21:19:04.895 Saving file at /notebooks/regret_report.ipynb`: sources identical, 8 outputs added (+3,746 lines).
  - My tab-close click came about 4 s after that, at 21:19:08. Because the document was already clean, no Save/Discard dialog appeared, so the "close with Discard" instruction could not be applied.
  - The File menu has no Autosave toggle. In JupyterLab 4 it is probably under Settings ("Autosave Documents"); I haven't verified this.
  - I copied the autosaved file to `qa/T29/scratch/regret_report.autosaved.ipynb` and restored the original with `git checkout -- notebooks/regret_report.ipynb`.
  - `git status` now shows only `qa/T29/`, and the JupyterLab shutdown wrote nothing more.
  - **Recommendation for future QA (T32, S4):** turn off autosave before Run All (Settings menu, unverified), or run a copy in `qa/<ID>/scratch/`. Either way, check `git diff --quiet notebooks/regret_report.ipynb` afterwards.

## Step 2: JupyterLab, sanity heights and overlap sweep

- **Sanity plot areas** (from `gd._fullLayout.yaxisN._length`), with the output area 768 px and the figure 748 × 780 (`layout.height = 780`):

  | Axis | Height (px) | Width (px) | y title |
  |---|---|---|---|
  | `yaxis` | 260 | 281 | replay time (min) |
  | `yaxis2` | 260 | 281 | fuel flow (kg/h) |
  | `yaxis3` | 260 | 281 | gap count (plans) |
  | `yaxis4` | 260 | 281 | mean gap size (kg) |

  All are ≥ 180 ✔. Screenshot: `qa/T29/notebook-sanity.png`.
- **Overlap sweep:** the script is `qa/T29/scratch/overlap.js`. It runs `querySelectorAll` per `#fig-…` over:
  - `text[class$="title"]`, `.annotation`, `.legend` and each `.legend .traces`;
  - `.updatemenu-container`, `.slider-container` and `.colorbar`;
  - every `g[class$="tick"] text`, grouped by axis class, with colour-bar ticks grouped per colour bar.

  It compares `getBoundingClientRect` pairwise and excludes parent/child pairs, same-axis tick pairs and legend item-to-item pairs. Elements with zero size or that are hidden are dropped and counted; none were dropped.

  | Figure | Elements swept | Intersections |
  |---|---|---|
  | fig-headline | 0 (a Plotly table has no titles, ticks or legend) | 0 |
  | fig-showcase-map | 2 titles, 1 annotation, legend + 5 items, dropdown, slider, colour bar + 6 ticks | **0** |
  | fig-lead-regret | 4 titles, 5 annotations, legend + 4 items, 20 ticks | **0** |
  | fig-wind-error | 5 titles, 4 annotations, legend + 1 item, 23 ticks | **0** |
  | fig-sanity | 6 titles, 7 annotations, 34 ticks | **0** |

- **Positive control:** on the report page, I used `Plotly.relayout` to move `fig-lead-regret`'s legend to x = −0.08. A targeted inline snippet, using the same pairwise `getBoundingClientRect` test as `overlap.js` (not the script itself), then detected `legend ∩ ytitle "mean fuel regret (kg)"`. `overlap.js` keeps both of those element kinds, so it would catch the same collision. The second half of that snippet, which moved an annotation, found nothing. I reloaded the page before measuring anything else.

## Step 3: SBC on `reports/report-fixture.html`

| Check | Result |
|---|---|
| Page | `http://127.0.0.1:8765/reports/report-fixture.html` at a 1,200 × 900 viewport |
| `#<id> .main-svg` | 3 for each of `fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity` ✔ |
| Console | 1 error: `404 … /favicon.ico` (allowed) ✔ |
| Network (`browser_network_requests`, `static: true`) | 1 request: `GET /reports/report-fixture.html → 200` ✔ |
| Basemap | `performance` resource entries list only `/favicon.ico`; `window.PlotlyGeoAssets.topojson` is set, so the basemap is inlined, not fetched ✔ |
| Limitations heading | `H3` "Assumptions and limitations" (after stripping the `¶` anchor), whose `nextElementSibling` is a `UL` with **8** `LI` ✔ |
| Screenshot | `qa/T29/chrome.png` (full page, 1,200 px) |

## Step 4: overlap sweep on the report page

I ran the same script after a fresh load at each width. At 768 px I used `browser_resize`, reloaded, and confirmed `innerWidth = 768`. Both widths show no horizontal page overflow (`document.documentElement.scrollWidth == innerWidth`).

| Figure | 1,200 px: size, intersections | 768 px: size, intersections |
|---|---|---|
| fig-headline | 1739×1063, 0 (nothing to sweep) | 1739×1063, 0 |
| fig-showcase-map | 1134×760, **0** | 702×760, **0** |
| fig-lead-regret | 1134×700, **0** | 702×700, **0** |
| fig-wind-error | 1134×635, **0** | 702×635, **0** |
| fig-sanity | 1134×780, **0** | 702×780, **0** (plot areas 4 × 260 px tall) |

The element counts match the JupyterLab table above. Screenshots: `chrome.png` (1,200 px), `chrome-768.png`, `map-1200.png`, `map-768.png`, `lead-1200.png`, `wind-1200.png`, `headline-1200.png`.

## Step 5: reader view

**Order (5a ✔):**

1. H1 Forecast Regret, with the intro
2. 1. Headline
3. 2. Showcase flight
4. 3. Regret vs lead time
5. 4. Wind error vs fuel regret
6. 5. Sanity panel
7. 6. Method, assumptions and limitations, with the H3 Assumptions and limitations

This matches SPEC §5.2 items 1–6.

**Captions (5b):**

- **Headline: matches.** The caption says "mean (with 90% CI), median and p90 regret in fuel, time and CO₂ … pooled". The columns are fuel kg, fuel %, time and CO₂, each as mean (90% CI), median and p90, plus zero-regret share: 15 columns × 20 rows (4 sources × 5 leads).
- **Showcase map: matches.**
  - "Hindsight plan drawn as a wide translucent band beneath them": trace 7 is 7 px wide, opacity 0.5, orange and dotted. It's drawn before the forecast plans (2 px), so it sits beneath them.
  - At 24 h it equals Pangu-Weather (its legend says "= Pangu-Weather, 24 h"), so most of it hides under that line. That is the data.
  - The dropdown (Lead time, active = 24 h) and the background slider (ERA5 … Persistence baseline) are both present.
- **Lead time: matches.** Top row "Forecast sources", bottom row "Persistence baseline", Eastbound and Westbound columns. Lines are means; shaded bands are labelled "Shaded bands: 90% CI of the mean".
- **Wind error: does not match on the fixture** (failure 2). The pinned plan is present: "1 plan above 580 kg shown at top edge (max 903 kg)". The marker sits 4% below the top edge by design (`_PIN_INSET`).
- **Sanity: matches.** It shows replay time by direction, fuel-flow range, and optimiser-gap count and size. B9's additions are there:
  - "0 gaps" labels;
  - `n=1` on each gap-size bar;
  - "max equal for all plans: same initial mass";
  - neutral grey boxes.

**Headline table (5c): FAIL**, failure 1. Rows: 20/20 visible. Columns: 9/15 at 1,200 px, 5/15 at 768 px and in JupyterLab.

**Showcase map (5d ✔):**

- The ERA5 background shows a clear dark jet band from the US east coast across to about 30°W, at roughly 40–50°N.
- The IFS HRES, GraphCast and Pangu-Weather plans and the hindsight band all run along it.
- The persistence plan (dashed, white halo) arcs north of it. That is the contrast the map is meant to show.
- The legend and colour-bar title ("ERA5 (truth) wind (m/s)") are clear at both widths.

**Lead time and scatter (5e):**

- **Lead time: readable.** Persistence is on its own scale (to about 8,000 kg), and the forecast row (to about 800 kg) separates the sources at long lead, with marker symbols per source.
  - Eastbound: IFS HRES reaches about 480 kg at 120 h vs about 100 kg for GraphCast.
  - Westbound: the sources overlap. That is the data (6 flights).
- **Scatter: not readable on the fixture** (failure 2). With no medians and no source legend, the faint (opacity 0.25) points can't be told apart. On the full report the medians and legend are present.

**Limitations (5f ✔):** all 8 SPEC §7 items are present, in order. Two wording notes, not failures:

- Bullet 4 reads "the truth (ERA5) is treated as truth but is itself a model", which is slightly circular. SPEC has "ERA5 is treated as truth but is itself a model".
- Bullet 8 adds "and so is GenCast". That is extra information, not a change of scope.

**Avoided words (5g ✔):**

- I parsed every `_Avoid_` term in CONTEXT.md (36 terms) and grepped whole words, case-insensitively, over `document.body.innerText`, every `svg text`, and each figure's `data` and `layout` JSON. That covers names, hovertemplates, customdata, dropdown and slider args, with `x`, `y`, `z`, `lat` and `lon` stripped.
- No hits for route, trajectory, oracle, analysis, optimal, observations, simulation, score, horizon, RMSE, trip, penalty or loss.

| Hit | Context | Verdict |
|---|---|---|
| error | "Wind error vs fuel regret", "wind error (m/s)", "wind-error bins", "Wind error is the RMS…", hover "wind error %{x:.2f} m/s" | OK: **Wind error** is a defined CONTEXT term. "error" is avoided only as a name for regret. |
| error | "How much does a weather forecast's error cost…", "1. Headline: what forecast error costs" | OK: refers to forecast inaccuracy, not regret. |
| model | "…ERA5 is treated as truth but is itself a model." | OK: SPEC §7's own wording, about a weather model. It doesn't name a forecast source. |

**Minor notes** (not failures; for the lead to judge):

- The page `<title>` is "Notebook", so the browser tab and bookmark say "Notebook", not "Forecast Regret". That is nbconvert's default.
- The showcase map title uses the raw flight id "JFK-LHR-20200209T0000"; the section heading already says "JFK→LHR, 2020-02-09".
- The headline header says "CO2 (kg)" where the caption says CO₂.
- The showcase map has about 80 px of empty space between the legend and the slider label at 1,200 px.
- Sanity, gap count: the y axis ticks 0, 0.2 … 1 for integer counts. That's fixture data (1 gap per source), but integer ticks (`dtick=1`) would read better.
- Sanity, fuel-flow panel: the "max equal for all plans: same initial mass" annotation sits mid-panel, about 80 px below the flat maximum line it explains.

## Files

- `report.md` (this file).
- Screenshots:
  - notebook: `notebook.png`, `notebook-sanity.png`;
  - report pages: `chrome.png` (SBC, full page, 1,200 px), `chrome-768.png`;
  - figures: `headline-1200.png`, `map-1200.png`, `map-768.png`, `lead-1200.png`, `wind-1200.png`.
- Scratch (gitignored): `overlap.js`, `jupyter.log`, `http.log`, PID files, and `regret_report.autosaved.ipynb`.
