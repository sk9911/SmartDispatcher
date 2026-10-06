# B7 QA: showcase map interaction and layout fixes

Date: 2026-10-01 · Branch `grilltest` · HEAD `df9e7fa` (`showcase_map.py` last changed in `c0ab242`, B7) · Browser: `playwright` MCP (Chrome), viewport 1200 × 807 · Config: `fixture` (showcase flight `JFK-LHR-20200209T0000`) · Plotly.js 4.1.1

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_showcase_map` (fixture) | **PASS** |
| 2 | SBC on `qa/B7/scratch/fig.html`, *F* = `fig-showcase-map`; land and coastlines drawn | **PASS** |
| 3 | Behavioural desync check (GraphCast at 24 h → 72 h → step 2), real clicks | **PASS** |
| 3a | (T21) after 72 h, hovering a plan shows `lead 72 h` | **PASS** |
| 4 | Legend: 5 entries (4 sources + hindsight) at 12, 24, 48, 72 and 120 h | **PASS** |
| 5 | Hindsight band below the forecast plans; Pangu-Weather visible; hover aimed at a plan does not return the band; hindsight legend and hover say which plan it equals | **PASS** (with a data-driven note on overlapping forecast plans) |
| 6 | No overlaps among title, dropdown, legend, slider labels and colour bar | **FAIL** in JupyterLab (768 px); PASS at the default width (1184 px) |
| 7 | Legend click at 72 h: opacity 0.5, trace hidden | **PASS** |
| 8 | Reader view | Jet ✔ (the band is hard to tell from the squares) · plans partly distinguishable · Persistence weak over the jet (findings below) |

**1 failure** (step 6, JupyterLab width), reported to the lead.

## Step 1: SNC

- `qa/B7/scratch/check.ipynb` was written by `scratch/make_nb.py`, the T21 generator with paths changed to `qa/B7/`.
  - Cell 1: `regret.offline.install_if_requested()`, `os.chdir(<repo root>)`, `display(HTML(showcase_map.geo_assets_html()))`.
  - Cell 2: `build_showcase_map(get_config('fixture'))`, `fig.show()`, `showcase_map.write_html(fig, 'qa/B7/scratch/fig.html')`, and a printout of the traces.
- JupyterLab was not running (`api/status` exit 7), so I started it with the exact *Shared runtime resources* command. Its PID is in `scratch/jlab.pid`.
- The restored workspace reopened `qa/B6/scratch/check.ipynb`, which had unsaved changes. I closed it with **Discard**, so its file was not written. Only the B7 notebook was open for the counts.
- Run → Run All Cells from the menu. Idle after about 5 s.
- `browser_evaluate`, scoped to the active notebook panel:
  - `.jp-OutputArea .js-plotly-plot`: **1** ✔
  - `[data-mime-type="application/vnd.jupyter.stderr"]`: **0** ✔
  - status bar: `Python 3 (ipykernel) | Idle` ✔
  - prompts: `[1]`, `[2]`; stdout `n_traces 26`
- The basemap draws in the notebook: `PlotlyGeoAssets.topojson` has `world_110m`, and the land and coastline paths have `d` lengths of 88,752 and 90,748 characters.
- `fig.html` was written fresh by the notebook: 5.36 MB, mtime 15:03:08. I deleted the builder's older copy first.
- The console showed 2 × "A kernel is required to send debug messages". That is JupyterLab debugger noise, as in T21, and SNC does not check the console.
- The figure renders 768 × 650 px. Screenshots: `notebook.png` (24 h) and `notebook-12h.png`.

## Step 2: SBC

- The static server was not running (exit 7), so I started it with `uv run python -m http.server 8765 --bind 127.0.0.1`. Its PID is in `scratch/http.pid`.
- `#fig-showcase-map .main-svg`: **3** ✔
- Console errors: **0** ✔
- Network, including static: only `GET http://127.0.0.1:8765/qa/B7/scratch/fig.html → 200`. There is no `cdn.plot.ly` request ✔
- Land path `d` is 88,269 characters and coastlines 90,244. Land and coastlines are drawn ✔
- Screenshot: `chrome.png`, full page, before any interaction.

## Step 3: Behavioural desync check

All of this ran in one page load (`scratch/desync.js` in `browser_run_code_unsafe`).

**How the interactions were driven.** The slider was clicked with a real `page.mouse.click`. The target x is the centre of the step's own label (`.slider-label-group text`), and the target y is the rail's centre, so rail padding does not skew it. The dropdown was clicked with real Playwright locator clicks. The background hover is a real `page.mouse.move` onto the southern-most background square nearest the page centre, far from every plan; a `plotly_hover` listener confirmed curve 0. No `Plotly.restyle`, `relayout` or `Fx.hover` was used.

The **background sum** below is the sum of `gd._fullData[0].marker.color`, which shows the values really changed, not just the title.

| State | `.cbtitle` | `sliders[0].active` | Current value | Grip x | Background sum | Background hover |
|---|---|---|---|---|---|---|
| Fresh load (24 h) | `ERA5 wind (m/s)` | 0 | `Background: ERA5` | 72 | 31444.1 | — |
| Slider step 2 at 24 h | `GraphCast, lead 24 h (m/s)` | 2 | `Background: GraphCast` | 544 | 31209.8 | — |
| **72 h button** | **`ERA5 wind (m/s)`** ✔ | **0** ✔ | **`Background: ERA5`** ✔ | **72** ✔ | **31444.1** (= ERA5) ✔ | `ERA5 analysis: 17.6 m/s` ✔ |
| **Slider step 2 at 72 h** | **`GraphCast, lead 72 h (m/s)`** ✔ | 2 | `Background: GraphCast` | 544 | **30505.1** (new field) ✔ | **`GraphCast forecast, lead 72 h: 27.3 m/s`** ✔ |

- The 72 h button switched the visible plans to traces 16 to 20 (all at 72 h), and the background trace 0 stayed visible.
- T21's desync is fixed. The field, title, slider state, grip and hover all go back to ERA5 on a lead change. Step 2 then loads the 72 h GraphCast field: its sum differs from both ERA5 and GraphCast at 24 h.
- Screenshots: `desync-1-graphcast-24h.png`, `desync-2-after-72h-button.png` and `desync-3-graphcast-72h.png`.

**3a (T21's 72 h hover).** The lead buttons restyle `marker.color` and `hovertemplate` with `null` for every plan trace, so I checked that the plan hovers survive. At 72 h, I ran real mouse moves onto two vertices of each plan:

| Target | Result |
|---|---|
| Pangu-Weather | `Pangu-Weather plan, lead 72 h` (both) ✔ |
| Persistence baseline | `Persistence baseline plan, lead 72 h` (both) ✔ |
| GraphCast | `GraphCast plan, lead 72 h` (1 of 2; the other returned Persistence, see the note in step 5) ✔ |
| IFS HRES | 1 of 2 returned `IFS HRES plan, lead 72 h` (from the hindsight probe); its own probes returned Persistence or GraphCast, which overlap it at 72 h |
| Hindsight band | `Hindsight plan; best plan in hindsight is Pangu-Weather, lead 24 h; shown with lead 72 h` ✔ |

Every hover text includes `lead 72 h`. I measured pixel distances between plans only at 24 h (step 5). T21 measured the median gap between Persistence and the other plans at 72 h as 2–4 px, so the 72 h hovers that went to Persistence most likely come from that overlap. I did not measure them in this run.

## Step 4: Legend at every lead

The leads were chosen with real dropdown clicks.

| Lead | `.legend .traces` | Entries (trace index) |
|---|---|---|
| 12 h | **5** ✔ | Hindsight plan (1), IFS HRES (2), GraphCast (3), Pangu-Weather (4), Persistence baseline (5) |
| 24 h | **5** ✔ | Hindsight plan (= Pangu-Weather, 24 h) (6), IFS HRES (7), GraphCast (8), Pangu-Weather (9), Persistence baseline (10) |
| 48 h | **5** ✔ | 11 to 15, same names as 12 h |
| 72 h | **5** ✔ | 16 to 20 |
| 120 h | **5** ✔ | 21 to 25 |

Each lead shows its own traces, and all opacities are 1.

## Step 5: Hindsight band

- **Draw order** at 24 h, from the DOM order of `.trace.scattergeo`: 6 (band), then 7, 8, 9 and 10. The band is drawn first, under every forecast plan ✔
- **Band style:** width 9, `#222222`, opacity 0.45, `dash: dot`. It has 116 vertices (`hindsight[::5]`); each forecast plan has 25.
- **Visible on top: pixel check.** I sampled 199 points along each 24 h `path.js-line` in a viewport screenshot (`scratch/px24.png`, `scratch/px_run.js`). For each point I checked whether a pixel within 1 px is the line's own colour (tolerance 40):

  | Plan | Own colour visible |
  |---|---|
  | Pangu-Weather | **199/199** ✔ (T21: 0%, fully hidden) |
  | Persistence baseline | 199/199 |
  | GraphCast | 101/199 |
  | IFS HRES | 58/199 |

  HRES and GraphCast are not covered by the band. They are covered by the Pangu-Weather line, which is drawn after them and shares their waypoints over much of the flight. At 24 h, **8 of 10 sampled HRES vertices are 0 px from a Pangu-Weather vertex**, and 5 of 10 GraphCast vertices are. So the forecast plans really are identical there. PLAN.md's B7 entry records short-lead overlap of forecast plans as the data, not a defect.
- **Hover aimed at a forecast plan** (real mouse moves onto data vertices at 24 h, curve number from a `plotly_hover` listener):
  - Pangu-Weather: **18/18 returned Pangu-Weather**, including 8 vertices at index multiples of 5, which coincide exactly with band vertices. **0 hits on the band** ✔
  - Persistence: 10/10 returned itself.
  - GraphCast: 5/10 returned itself. The other 5 returned Pangu-Weather, at vertices 0 px from a Pangu-Weather vertex.
  - IFS HRES: 2/10 returned itself. The other 8 returned Pangu-Weather, all at vertices 0 px from a Pangu-Weather vertex.
  - **No probe on any forecast plan returned the band** ✔
  - Where two plans share a vertex, Plotly gives the hover to the later trace. That is the same data overlap as above, not the band.
- **Band hover:** I aimed real mouse moves at the 6 band vertices farthest (7 to 8 px) from any forecast vertex. All 6 returned the band, with the text `Hindsight plan (= Pangu-Weather, 24 h); best plan in hindsight is Pangu-Weather, lead 24 h; shown with lead 24 h` ✔ Screenshot: `hindsight-hover-24h.png`.
- **Legend name:** `Hindsight plan (= Pangu-Weather, 24 h)` at 24 h ✔. At the other leads it is plain `Hindsight plan`, with the hover saying `best plan in hindsight is Pangu-Weather, lead 24 h`. That is correct, since it equals no plan at those leads.
- **Endpoints:** the band starts exactly at JFK. It ends at (−0.586, 51.497), against Pangu-Weather's last point at LHR (−0.454, 51.47). `[::5]` drops the final ~9 km, about 1 px on screen. Not visible.

## Step 6: Layout overlaps (FAIL in JupyterLab)

I measured `getBoundingClientRect` of the title (`text.gtitle`), the dropdown header (`.updatemenu-header-group`), the "Lead time" annotation text, the legend background and each legend item, the slider current value and each step label, the colour bar (`g.colorbar`) and `.cbtitle`. Each element's own children and zero-size rects were skipped (`scratch/layout.js`). The dropdown was closed at every measurement, and every lead was measured.

**Default width (static page, figure 1184 px): no overlaps at any lead** ✔ At 24 h, for example:

| Element | Box |
|---|---|
| Title | y 16 to 36 |
| "Lead time" | x 20 to 80 |
| Dropdown | x 105 to 180, y 82 to 115 |
| Legend | x 287 to 1089, y 85 to 114, one row |
| Slider current value | y 580 to 594 |
| Slider step labels | y 637 to 651, separate |
| Colour bar | x 1110 to 1181 |

**JupyterLab output (figure 768 px): overlaps at every lead** ✘

| Lead | Intersections (overlap w × h px) |
|---|---|
| 12, 48, 72, 120 h | dropdown × "Lead time" (7.6 × 14.5); dropdown × legend (75 × 29), on the Hindsight plan item; "Lead time" × legend (43.6 × 14.5) |
| 24 h | dropdown × "Lead time" (7.6 × 14.5); the legend wraps to 2 rows and its second row (Persistence baseline) runs under the dropdown (75 × 19); "Lead time" × legend (32.6 × 11.7) |

- The legend is right-anchored (`x: 1.0, xanchor: right`) on the same row as the dropdown. At 768 px its width runs past the left edge of the plot area, so it slides under the dropdown and the "Lead time" label.
- Visible effect, at 24 h in `notebook.png`: the reader sees `Lead tim` and `e baseline`, because "Persistence baseline" is cut by the dropdown.
- At 12 h, in `notebook-12h.png`: the reader sees `Lead tim` and `an`, because "Hindsight plan" is behind the dropdown.
- The dropdown also covers the last letters of "Lead time" (7.6 px) at this width.
- PLAN.md's QA rules make JupyterLab one of the two target platforms, so this fails the B7 layout requirement there.

## Step 7: Legend click at 72 h

- 72 h was chosen with real clicks. Then a real `page.mouse.click` on the Persistence baseline `.legendtoggle`.
- Persistence baseline legend item opacity: **0.5**; the other four stayed at 1 ✔
- `gd.data[20].visible` is **`legendonly`**, and its line is no longer drawn (no `path.js-line`) ✔
- Persistence at the other leads (traces 5, 10, 15 and 25) stays `false`. The per-source `legendgroup` did not turn hidden leads into `legendonly` ✔. `.legend .traces` is still 5 ✔
- Screenshot: `legend-click-72h.png`.
- Observation, not a failure: after the click, choosing 120 h restores every 120 h trace and trace 20 goes back to `false`. A hidden source does not stay hidden across a lead change, because the button's `visible` list overrides the legend state. A reader who hides Persistence must hide it again at each lead.

## Step 8: Reader view

Not pass/fail. Measured at 24 h (`chrome.png`, `plans-zoom-24h.png` at device scale).

**Greys direction.** Low speed is white (`rgb(255,255,255)` at 0.2 m/s), and high speed is near-black (`rgb(15,15,15)` at 105.5 m/s). Squares have opacity 0.8. So the jet is the dark band.

**Does the hindsight plan visibly ride the jet? Its path does; the band itself is hard to see.**

- The band runs along the darkest squares, from Newfoundland to Ireland, as T21 measured: 82.7 vs 64.0 m/s mean speed.
- But the 9-px `dot` dash renders as a row of **grey squares**, the same size, shape and grey as the background cells. The legend symbol is also two grey squares. Over the jet it reads as more background, not as a line.
- WCAG contrast of the band against the squares it crosses: median **1.49**, minimum 1.22, and 28 of 50 samples below 1.5. Graphics need 3:1.

**Are the plans distinguishable?** Partly.

- Pangu-Weather (purple) is drawn on top and fully visible.
- GraphCast (green) separates on the western half.
- IFS HRES (blue) shows only where it leaves Pangu-Weather, mostly east of 30°W. That is about 29% of its length; elsewhere it is identical to Pangu-Weather (step 5).
- Persistence separates clearly to the north.
- At 72 h the four lines bunch together over the jet (`desync-2-after-72h-button.png`).
- This is mostly the data, as recorded in PLAN.md.

**Is the persistence baseline's grey line visible on the grey background?** Visible, but weak over the jet.

- `#7f7f7f` gives 4.0:1 against white, so it reads well over land, gaps and slow-wind cells.
- Against the squares it actually crosses at 24 h: median contrast **1.83**, minimum **1.02**, with 14 of 48 samples below 1.5 and all 48 below 3.
- In `plans-zoom-24h.png`, it fades where it passes over the mid-grey jet edge north of Newfoundland.
- The forecast colours fare similarly over the darkest cells (HRES median 1.87, GraphCast 2.50, Pangu-Weather 2.18). They stay readable because of their hue, which the grey Persistence line lacks.

**Other notes (minor):**

0. **Vocabulary:** the background hover text that B7 added for ERA5 reads `ERA5 analysis: 17.6 m/s` (`hover_era5` in `showcase_map.py`). CONTEXT.md lists "Analysis" under *Truth*'s `_Avoid_` terms, and CLAUDE.md requires CONTEXT.md terms in UI text. This is not a step failure, since the hover does name the field, but the wording breaks the language rule. Something like `Truth (ERA5): … m/s` would comply.
1. The geo area is 559 px wide inside a 1184-px figure (`chrome.png`), leaving wide blank margins at the default width.
2. In JupyterLab, the Plotly modebar sits over the end of the title ("departure") while the pointer is over the figure (`notebook.png`, `notebook-12h.png`). This is Plotly's default modebar, shown on hover.

## Failures reported to the lead

1. **Step 6, layout in JupyterLab.**
   - Expected: no intersections among the title, dropdown, legend, slider labels and colour bar at JupyterLab's output width.
   - Actual: at 768 px the right-anchored legend overlaps the dropdown (75 × 19–29 px) and the "Lead time" label (33–44 × 12–15 px) at every lead. The dropdown also overlaps "Lead time" (7.6 × 14.5 px). "Persistence baseline" (24 h) and "Hindsight plan" (other leads) are hidden behind the dropdown. Evidence: `notebook.png`, `notebook-12h.png`.

Reader-view items sent as candidates, not failures:

- the hindsight band reads as background squares (contrast median 1.49);
- the Persistence line is weak over the jet (median 1.83, minimum 1.02);
- the legend hide state resets on lead change;
- the ERA5 background hover uses "analysis", an avoided term for *Truth* (CONTEXT.md).

## Teardown

- JupyterLab (8888) and the static server (8765) were stopped by PID (`scratch/*.pid`), children first.
- Afterwards both `curl` checks exit 7, and `lsof` shows nothing listening on either port.
- The browser was closed.

---

## Attempt 2 (0b8b5b7)

Date: 2026-10-01 · Branch `grilltest` · HEAD `c9737dc` (`showcase_map.py` last changed in `0b8b5b7`) · Browser: `playwright` MCP (Chrome), viewport 1200 × 807 for SNC and the 768 px layout, 1200 × 1000 for everything else (only the height changed, so JupyterLab's output stays 768 px wide) · Config: `fixture` · Plotly.js 4.1.1

Scripts are in `scratch/a2/`. `desync.js` and `steps.js` are attempt 1's scripts with only the screenshot names changed to `*-attempt2.png`. `layout_*.js` add a check that every element lies inside the figure. `reader.js` does the pixel work.

### Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_showcase_map` (fixture) | **PASS** |
| 2 | SBC on `qa/B7/scratch/fig.html`, *F* = `fig-showcase-map` | **PASS** |
| 3 | Desync check (GraphCast at 24 h → 72 h → step 2), real clicks | **PASS** |
| 3a | After 72 h, hovering a plan shows `lead 72 h` | **PASS** |
| 4 | Legend: 5 entries at 12, 24, 48, 72 and 120 h | **PASS** |
| 5 | Hindsight band: drawn under the plans, orange, never takes a forecast plan's hover, its own hover and legend name are right | **PASS** |
| 6 | No overlaps among title, dropdown, "Lead time", legend and its entries, slider and its labels, colour bar | **PASS** in JupyterLab (768 px) and standalone (1184 px), at every lead |
| 6a | No "analysis" (or any other CONTEXT.md avoided term) in UI text; background hover reads `ERA5 (truth): … m/s` | **PASS** |
| 7 | Legend click at 72 h: opacity 0.5, trace hidden | **PASS** |
| 8 | Reader view | **Jet now faint** (core vs quiet contrast 1.42:1, attempt 1 about 4:1) · orange band visible by hue · Persistence visible (median 2.73:1, was 1.83) · plans told apart as in attempt 1 |

**0 step failures.** The reader-view concern is that the jet stream is now faint (details below). It is reported to the lead as the main finding, but it is not a step failure: B7's check asks for a lighter scale and does not set a contrast floor for the jet.

### Step 1: SNC

- Neither server was running (both `curl` checks exit 7). I started both with the *Shared runtime resources* commands; their PIDs are in `scratch/a2/*.pid`.
- `check.ipynb` and `fig.html` were deleted, then `check.ipynb` was regenerated with `scratch/make_nb.py` (unchanged).
- The restored workspace reopened `qa/B6/scratch/check2.ipynb` (marked dirty). I closed it with **Discard**, so that file was not written.
- Run → Run All Cells from the menu. All prompts were numbered after 6.3 s.
- Results:
  - `.jp-OutputArea .js-plotly-plot`: **1** ✔
  - stderr outputs: **0** ✔
  - status bar: `Python 3 (ipykernel) | Idle` ✔
  - stdout: `n_traces 26`
- The basemap is drawn (`PlotlyGeoAssets.topojson.world_110m` present; land `d` 88,410 characters, coastlines 90,443).
- The figure is **768 px** wide.
- Console: 2 errors from JupyterLab's debugger ("A kernel is required to send debug messages"), as in attempt 1. SNC does not check the console.
- Screenshots: `notebook-attempt2.png` (24 h) and `notebook-12h-attempt2.png`, taken as figure-element shots at viewport height 1000 so the slider is included.

### Step 2: SBC

- `#fig-showcase-map .main-svg`: **3** ✔
- Console errors: **1**, the allowed `/favicon.ico` 404 ✔
- Network, including static resources: only `GET /qa/B7/scratch/fig.html → 200`; no `cdn.plot.ly` request ✔
- Land and coastlines are drawn (88,018 and 90,034 characters).
- The figure is 1184 px wide.
- Screenshot: `chrome-attempt2.png`.

### Step 3: Desync check

This used the same method as attempt 1: real `page.mouse.click` on the slider, real locator clicks on the dropdown, and a real `page.mouse.move` for the background hover. No `restyle`, `relayout` or `Fx.hover` was used.

| State | `.cbtitle` | `sliders[0].active` | Current value | Background sum | Background hover |
|---|---|---|---|---|---|
| Fresh load (24 h) | `ERA5 wind (m/s)` | 0 | `Background: ERA5` | 31444.1 | `ERA5 (truth): 17.6 m/s` (separate fresh load) |
| Slider step 2 at 24 h | `GraphCast, lead 24 h (m/s)` | 2 | `Background: GraphCast` | 31209.8 | — |
| **72 h button** | **`ERA5 wind (m/s)`** ✔ | **0** ✔ | **`Background: ERA5`** ✔ | **31444.1** (= ERA5) ✔ | **`ERA5 (truth): 17.6 m/s`** ✔ |
| **Slider step 2 at 72 h** | **`GraphCast, lead 72 h (m/s)`** ✔ | 2 | `Background: GraphCast` | **30505.1** (new field) ✔ | **`GraphCast forecast, lead 72 h: 27.3 m/s`** ✔ |

Screenshots: `desync-1-graphcast-24h-attempt2.png`, `desync-2-after-72h-button-attempt2.png` and `desync-3-graphcast-72h-attempt2.png`.

**3a.** Real hovers at 72 h on two vertices of each plan:

- every hover text includes `lead 72 h` ✔;
- Pangu-Weather 2/2 and Persistence 2/2 returned themselves;
- GraphCast 1/2 returned itself, and the other returned Persistence;
- IFS HRES 0/2 returned itself; its probes returned Persistence and GraphCast. HRES was returned by one of the hindsight probes;
- the band returned `Hindsight plan; best plan in hindsight is Pangu-Weather, lead 24 h; shown with lead 72 h`.

The HRES and GraphCast probes that returned other plans are the 72 h overlap of plans that attempt 1 and T21 described (2–4 px apart). It is the same as attempt 1.

### Step 4: Legend at every lead

| Lead | `.legend .traces` | Entries (trace index) |
|---|---|---|
| 12 h | **5** ✔ | Hindsight plan (1), IFS HRES (2), GraphCast (3), Pangu-Weather (4), Persistence baseline (5) |
| 24 h | **5** ✔ | Hindsight plan (= Pangu-Weather, 24 h) (6), 7 to 10 |
| 48 h | **5** ✔ | 11 to 15 |
| 72 h | **5** ✔ | 16 to 20 |
| 120 h | **5** ✔ | 21 to 25 |

All entries have opacity 1.

### Step 5: Hindsight band

- **Draw order** at 24 h: 6 (band), then 7, 8, 9 and 10 ✔
- **Style, as rendered** (from `getComputedStyle` on the band's `path.js-line`):
  - stroke `rgb(255,127,14)`, stroke-opacity 0.95, width 7 px (attempt 1: 9), dash `7px, 7px`;
  - trace group opacity 0.5;
  - net alpha 0.475. Over white it renders as a pale peach: theory gives `rgb(255,194,141)`, and the median of 203 pixels on the dashes was `rgb(246,193,141)`.
- **Forecast-plan hovers** at 24 h, from real mouse moves onto plan vertices:
  - Persistence: 10/10 returned itself.
  - GraphCast: 5/10 returned itself; the other 5 returned Pangu-Weather.
  - IFS HRES: 2/10 returned itself; the other 8 returned Pangu-Weather.
  - Pangu-Weather: **18/18** returned itself, including 8 vertices that coincide with band vertices.
  - **No probe returned the band** ✔. The probes that returned Pangu-Weather sit on shared vertices, as in attempt 1.
- **Band hover:**
  - I aimed real mouse moves at 6 band vertices that are 6.7 to 8.8 px from any forecast vertex but lie on Pangu-Weather's line segments (0.1 px), since the band follows Pangu-Weather's path.
  - The band still won the hover at all 6, because Plotly picks the nearest vertex.
  - All 6 returned the band, with the text `Hindsight plan (= Pangu-Weather, 24 h); best plan in hindsight is Pangu-Weather, lead 24 h; shown with lead 24 h` ✔
- **Legend name:**
  - At 24 h it is `Hindsight plan (= Pangu-Weather, 24 h)` ✔
  - At the other leads it is plain `Hindsight plan`, which is correct.

### Step 6: Layout (PASS at both widths)

The same measurement as attempt 1 (`getBoundingClientRect`, an element's own children skipped, dropdown closed, pointer moved off the figure), at every lead. Measured:

- title;
- dropdown header;
- "Lead time";
- legend background and each of the 5 entries;
- slider current value, rail and each step label;
- colour bar and `.cbtitle`.

**Intersections: none at any lead, at either width. No element lies outside the figure.**

| | JupyterLab, figure 768 px | Standalone, figure 1184 px |
|---|---|---|
| Title | x 0 to 608 (relative), y 10 to 31 | y 18 to 39 |
| "Lead time" right edge → dropdown left edge | **32 px** gap (attempt 1: overlapped by 7.6 px) | 89 px gap |
| Dropdown | y 73 to 106 rel. (above the map top at 109.5) | y 81 to 114 (map top 117.5) |
| Map (geo) bottom → legend top | 13.6 px | 13.5 px |
| Legend | **2 rows at 24 h** (row 2: Persistence baseline at x 10 to 174 rel.); 1 row at the other leads | 1 row at every lead |
| Legend bottom → slider current value | 31.5 px at 24 h (2 rows); 60.5 px at the others | 60.6 px |
| Slider step labels | separate, y 738.6 to 753 rel. | separate, y 746.6 to 761 |
| Colour bar | x 687 to 758 rel., right of the legend's right edge (656 rel.) | x 1110 to 1181 |

All 5 legend entries are fully visible at every lead. At 24 h in JupyterLab the legend wraps to 2 rows, left-anchored, as the attempt-2 change intended.

The figure is 760 px tall, and the JupyterLab viewport at height 807 cut off the slider's step labels below the fold. This is an ordinary notebook scroll, not an overlap.

Not a failure: Plotly's default modebar, shown while the pointer is over the figure, still sits over the end of the title in JupyterLab (modebar x 896 to 1144 page, title right edge 986; y overlap about 14 px). It is hidden when the pointer leaves, it is Plotly chrome rather than a figure element, and B7's list does not include it. Same as attempt 1, note 2.

### Step 6a: Wording

One `browser_evaluate` collected 79 strings:

- every SVG `text` node;
- every trace's `name`, `hovertext` and `hovertemplate`;
- the colour-bar title, the plot title and the annotations;
- every slider step's colour-bar title and hovertemplate;
- every dropdown button's restyle arguments and its replacement slider steps.

I matched them against `analysis` and every other `_Avoid_` term in CONTEXT.md (route, trajectory, model, horizon, forecast step, oracle, optimal plan, simulation, score, loss and so on): **0 matches** ✔

The background hover reads `ERA5 (truth): 17.6 m/s` both on a fresh load and after the 72 h button reset the background. Those are the two code paths that set it ✔

Minor, not a failure: the colour-bar title and the slider's first label still say `ERA5 wind (m/s)` and `ERA5` without "(truth)". Neither uses an avoided term.

### Step 7: Legend click at 72 h

- After a real click on the Persistence baseline `.legendtoggle`:
  - its legend item opacity is **0.5**, and the other four stay at 1 ✔;
  - `data[20].visible` is `legendonly`, and its line is not drawn ✔;
  - traces 5, 10, 15 and 25 stay `false` ✔.
- Choosing 120 h afterwards restores all five entries. As in attempt 1, the hide state does not carry across a lead change.
- Screenshot: `legend-click-72h-attempt2.png`.

### Step 8: Reader view

I measured at 24 h, standalone. The background colour of each of the 600 cells was read at its centre pixel from a screenshot taken with all five plans hidden by real legend clicks (`background-only-24h-attempt2.png`). The same view with the plans is `reader-24h-attempt2.png`.

The measured colours match the theory: the scale runs from white to `#b0b0b0` at opacity 0.8, with `cmax` 111.3 m/s. The ERA5 maximum is 105.5 m/s, so its darkest possible cell is `rgb(192,192,192)` over white.

#### Is the jet stream still clearly visible? **No. It is still there, but faint.**

| Cell set | n | Median speed | Median grey (rendered) |
|---|---|---|---|
| Jet core (top decile, ≥ 60.1 m/s) | 96 | 76.8 m/s | **211** |
| Cells under the hindsight path | 36 | 89.6 m/s | **204** |
| Quiet (< 20 m/s) | 271 | 11.9 m/s | **247** |
| Land fill, no cell (`#eeeeee`) | — | — | 238 |

The table gives these WCAG contrasts. A graphical object needs 3:1.

| Comparison | Attempt 2 | Attempt 1 (Greys, same cells, computed) |
|---|---|---|
| Jet core vs quiet | **1.42 : 1** | about 3.96 : 1 |
| Under the hindsight path vs quiet | **1.53 : 1** | about 5.59 : 1 |
| Jet core vs land | **1.29 : 1** | about 4.15 : 1 |
| Fastest cell (105.5 m/s) vs white | 1.76 : 1 | about 10.9 : 1 |

The attempt-1 column is computed from the Greys scale attempt 1 reported (white to `rgb(15,15,15)`), not measured on a page.

Cross-sections from north to south (latitude: speed m/s → grey):

- **48.5° W:** 58.5°: 27.6 → 239 · 53.5°: 44.2 → 230 · 51°: 61.5 → 220 · **48.5°: 92.8 → 202** · **46°: 95.6 → 201** · 43.5°: 76.2 → 212 · 38.5°: 33.7 → 236 · 33.5°: 11.3 → 249
- **28.5° W:** 56°: 48.5 → 228 · **51°: 103.9 → 196** · 48.5°: 80.8 → 209 · 43.5°: 44 → 230 · 38.5°: 8.7 → 250

So the whole speed range from 10 to 100 m/s spans only about 50 grey levels, roughly 249 down to 196.

What a reader sees, judged from `background-only-24h-attempt2.png` and `reader-24h-attempt2.png`:

- a soft, slightly darker band of light-grey squares from Newfoundland towards Ireland;
- it is noticeable if you look for it, but it does not read as a jet at a glance;
- its darkest squares are only a little darker than the land fill, so over Labrador and Iberia the cells merge into the land.

The plans still visibly follow the slightly darker band. But the story the map tells, that the hindsight plan rides the jet, now depends on the reader finding a 1.4–1.5:1 band. In attempt 1 it was about 4–5.6:1. **Attempt 2 traded jet visibility for plan visibility.** A mid-point would keep both: a scale whose top lands near grey 130–150 after blending would give the jet about 2.5–3:1 against quiet cells and still leave the coloured lines readable. That is a suggestion for the lead, not a fix.

#### Is the orange hindsight band clearly visible? **Yes, by hue. Its luminance contrast is low.**

- It renders as a pale peach dashed band 7 px wide, the only warm colour on the map. It stands out in both screenshots, including in JupyterLab.
- WCAG contrast is low because of the 0.475 net alpha: 1.57:1 over white, 1.33:1 over the jet core and 1.30:1 over cells under the path.
- Colour difference (CIELAB ΔE76) is about 41 against every grey. That is a large hue difference, and it is why the band reads.
- In attempt 1 the band looked like background squares (contrast 1.49, no hue). That problem is gone.
- Readers with a red–green colour vision deficiency will still see a light-on-light band. Raising the opacity would help them.

#### Is the Persistence line visible? **Yes. Clearly better than attempt 1.**

- Pixels along the line against the background at the same pixel: median **2.73:1**, minimum 1.18; 110 of 198 samples below 3 and 8 below 1.5.
- In attempt 1 the median was 1.83, with 14 of 48 below 1.5. Those numbers are not like for like: attempt 1 compared the line with the cells it crossed, while this compares it with the pixel beneath, which includes the white gaps between squares and so raises the median. The theory values over the jet below (2.67 vs attempt 1's 1.83 median) still show a real improvement.
- In theory `#7f7f7f` gives 4.0:1 over white, 2.67:1 over the jet core and 2.49:1 over cells under the path.
- It reads clearly on its northern track in both screenshots.

#### Can the plans be told apart? **Yes, as far as the data allow. Same as attempt 1.**

- Measured line-pixel contrasts against the background: IFS HRES median 3.13, Pangu-Weather 3.09, Persistence 2.73, GraphCast 2.60.
- These are higher than attempt 1's because the background is lighter. Where Pangu-Weather is drawn over IFS HRES or GraphCast, the sample measures the line on top, so the HRES and GraphCast figures partly reflect Pangu-Weather.
- At 24 h, Pangu-Weather (drawn on top, purple) hides most of IFS HRES and about half of GraphCast where they share waypoints. That is the data (step 5, and PLAN.md's B7 entry).
- GraphCast separates in the west, HRES east of about 30° W, and Persistence to the north.
- At 12 h (`notebook-12h-attempt2.png`) all five are distinct over most of the route.

### Failures reported to the lead

None. Every check step passed.

Reader-view finding sent to the lead as the headline:

- **The jet is faint.** Jet core vs quiet cells is 1.42:1, cells under the hindsight path vs quiet is 1.53:1, and jet core vs land is 1.29:1. Attempt 1 was about 4:1, 5.6:1 and 4.2:1. The darkest ERA5 cell is `rgb(192,192,192)`.

Minor notes:

- The band's luminance contrast is 1.3–1.6:1, so it relies on hue.
- The colour bar says `ERA5 wind`, not "(truth)".
- The modebar covers the end of the title on hover.
- The legend hide state resets on a lead change.

### Teardown

- JupyterLab (8888) and the static server (8765) were stopped by PID (`scratch/a2/*.pid`), children first.
- Afterwards both `curl` checks exit 7, and `lsof` shows nothing listening on either port.
- The browser was closed.

## Final check (5572d59)

Date: 2026-10-01 · Branch `grilltest` · HEAD `5572d59` (`showcase_map.py` last changed here) · Browser: `playwright` MCP (Chrome), viewport 1200 × 1000, DPR 1. So the JupyterLab output is **768 px** wide and the standalone figure **1,184 px** · Config: `fixture`.

The scope is the user-approved final pass (a smooth monotone background scale and a white halo under the persistence line) plus a regression check of earlier behaviour. Scripts are in `scratch/final/`: `desync.js`, `layout_*.js`, `reader.js` (jet, plans) and `pers.js` (persistence, halo hover, legend per lead).

### Summary

| # | Check | Result |
|---|---|---|
| B1 | Jet visibility: core vs quiet ≥ 2.5:1, core vs moderate ≥ 1.3:1 | **PASS** at both widths. Standalone: **2.98:1** and **2.17:1** (all cells), 3.02 and 2.20 sea-only. JupyterLab 768 px: **3.02:1** and **2.20:1**. The builder had 3.08 and 2.25 |
| B2 | Persistence dashed, with a white halo; halo has no legend entry and takes no hover; legend click hides line and halo | **PASS**. Legend click checked at both widths; style, legend count and hover probes standalone |
| B3 | All four forecast plans visible at 24 h; Pangu-Weather vs IFS HRES | **PASS** at both widths. The overlap is in the data: 19 of 25 waypoints are identical. Pangu-Weather is drawn on top, so IFS HRES is the one partly covered, not Pangu-Weather |
| B4a | Desync sequence with real clicks | **PASS** |
| B4b | 0 layout intersections at 24 h and 72 h, 768 and 1,184 px | **PASS** |
| B4c | Colour-bar title "ERA5 (truth) wind (m/s)" | **PASS** on 3 paths: fresh load, after the 72 h button, and after returning to slider step 0 |

**0 failures.**

### Setup, SNC and SBC

- Neither server was running. I started both with the *Shared runtime resources* commands; their PIDs are in `scratch/final/*.pid`.
- `scratch/final/make_nb.py` writes `scratch/check-final.ipynb`, which is attempt 2's notebook writing to `scratch/fig-final.html`. I deleted the old file first.
- **SNC:**
  - Run → Run All Cells from the menu took 6.6 s.
  - `.jp-OutputArea .js-plotly-plot`: **1** ✔
  - stderr: **0** ✔
  - `Idle` ✔
  - The figure is 768 px wide.
  - stdout: `n_traces 31`
  - Screenshots: `notebook-24h-final.png` and `notebook-72h-final.png`.
- **SBC:**
  - `.main-svg`: **3** ✔
  - Console errors: **0** ✔
  - Network: only `GET /qa/B7/scratch/fig-final.html → 200`; no `cdn.plot.ly` ✔
  - The basemap is inlined (`PlotlyGeoAssets.topojson.world_110m`; land path 88,018 characters).
  - Screenshots: `chrome-24h-final.png` and `chrome-72h-final.png`.

**Trace map** (it changed: one halo per lead, so the figure now has 31 traces, not 26):

| Index | Trace |
|---|---|
| 0 | background |
| 1–6 | 12 h |
| 7–12 | 24 h |
| 13–18 | 48 h |
| 19–24 | 72 h |
| 25–30 | 120 h |

Each lead block is: hindsight, IFS HRES, GraphCast, Pangu-Weather, **halo** (`meta.kind = "halo"`, no name), Persistence baseline. So the halos are traces 5, 11, 17, 23 and 29, each drawn just before its persistence line. At 24 h the DOM draw order is 0, 7, 8, 9, 10, 11, 12.

### B1. Jet visibility ✔

**Method**, the same as attempt 2's step 8:

- At 24 h, standalone, I hid all five plans with real `page.mouse.click`s on the legend toggles.
- Afterwards traces 7–12 were all `legendonly`, and only trace 0 was drawn. So the halo was hidden too and can't affect the samples.
- I took a screenshot (`background-only-24h-final.png`; the same view with plans is `reader-24h-final.png`) and read the rendered grey at each of the 600 cell centres.
- Classes use the ERA5 field: quiet < 20, moderate 20–60, core ≥ 60 m/s.
- The ratio is the WCAG contrast of the class medians.
- For the land/sea split, I hid trace 0 with `Plotly.restyle` for one screenshot, purely as a measurement. It is not part of any behaviour check.

| Class | Cells | Median speed | Median grey | Range | Of which on land |
|---|---|---|---|---|---|
| Quiet (< 20) | 271 | 11.9 m/s | **244** | 203–255 | 107 |
| Moderate (20–60) | 593 | 33.5 m/s | **210** | 138–255 | 199 |
| Core (≥ 60) | 96 | 76.8 m/s | **142** | 95–171 | 15 |
| Cells under the hindsight path | 36 | 89.6 m/s | **123** | — | — |

| Ratio | All cells | Sea cells only | Threshold | Builder | Attempt 2 |
|---|---|---|---|---|---|
| Core vs quiet | **2.98 : 1** ✔ | 3.02 : 1 | ≥ 2.5 | 3.08 | 1.42 |
| Core vs moderate | **2.17 : 1** ✔ | 2.20 : 1 | ≥ 1.3 | 2.25 | — |
| Moderate vs quiet | 1.37 : 1 | 1.37 : 1 | — | — | — |

**JupyterLab, 768 px** (same method; `scratch/final/reader_nb.js`; no land/sea split, because that step used `Plotly.restyle`):

- Quiet, moderate and core medians are grey **244**, **210** and **141**.
- Core vs quiet is **3.02:1** ✔ and core vs moderate **2.20:1** ✔.
- The 10 m/s bins step down monotonically, 249 → 97.
- Screenshot: `background-only-24h-notebook-final.png`.
- The geo area renders at the same 609 × 469 px in both layouts. The 768 px figure narrows the margins, not the map, which is why the numbers barely move.

My numbers are 0.05–0.10 below the builder's. That is consistent with sampling a single centre pixel per cell, and it is well clear of both thresholds.

**The scale is monotone.** Median grey of sea cells by 10 m/s bin:

| Bin (m/s) | 0 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Median grey | 250 | 237 | 223 | 209 | 193 | 181 | 166 | 146 | 127 | 111 | 97 |

The steps are 12–19 levels each, with no plateau. The B7c defect (35–111 m/s all one dark grey) is gone.

**Reader view:** yes, the jet stands out as a band that the hindsight plan rides.

- With the plans hidden, the darkest squares on the map form one continuous band from Newfoundland to Ireland at about 45–52° N, fading through mid-grey to near-white north and south. It is the first thing the eye finds.
- With the plans shown, the orange hindsight band and the three forecast plans run along the dark core. The cells under the hindsight path (median grey 123) are darker than the core's own median (142).
- The persistence plan runs along the band's lighter northern edge, so the contrast between the two reads at a glance.

### B2. Persistence line and halo ✔

**Style**, from `getComputedStyle` on `path.js-line`:

| Trace | Stroke | Width | Dash | Hover | In legend | Legend group |
|---|---|---|---|---|---|---|
| Persistence baseline (12) | `rgb(127,127,127)` | 3 px | `9px, 9px` | `text` | yes | `persistence` |
| Halo (11) | `rgb(255,255,255)`, opacity 1 | 6 px | none | `skip` | no | `persistence` |

**Legend: 5 entries at every lead** ✔. At 12, 48, 72 and 120 h they are: Hindsight plan / IFS HRES / GraphCast / Pangu-Weather / Persistence baseline. At 24 h the first entry is "Hindsight plan (= Pangu-Weather, 24 h)". The halo adds no entry.

**The halo takes no hover** ✔:

- I made 24 real `page.mouse.move`s onto halo pixels over cells darker than grey 200: 12 at the line's centre in dash gaps (where only the halo is drawn) and 12 at 2.5 px off the line's centre.
- `plotly_hover` curve numbers: persistence (12) 10 times, background (0) 11 times and hindsight (7) 3 times. A halo index (5, 11, 17, 23 or 29) appeared **0 times**.

**A legend click on "Persistence baseline" hides both** ✔:

- After a real click, traces 11 and 12 are both `legendonly`, neither is drawn, and the legend item opacity is 0.5. The same holds in JupyterLab at 768 px.
- Clicking again restores both.
- The other plans are unaffected.

**Visible over the jet core** ✔, with a caveat on where it is:

- At 24 h the persistence plan runs along the jet's **northern edge**. 60% of 599 samples along it lie on the white gaps between cell rows.
- 98 samples (16%) lie on cell pixels darker than grey 170 (about ≥ 60 m/s), and 63 of those are on a dash.
- There, the dash (grey 127) against the cell (median 154) is only 1.42:1. But each dash is edged by the white halo: the median at 2.5 px off-centre is grey 208, still on the anti-aliased edge, and dash vs halo is 2.6:1.
- In the 3× zoom (`plans-zoom-24h-final.png`), the dashes read clearly as grey on a white track wherever they cross mid- and dark-grey cells. The B7c defect, a faint line over dark cells (1.49:1, no halo), is fixed.

### B3. Plans at 24 h ✔: shared waypoints, not a drawing-order problem

**Every plan is visible somewhere.**

- Method: I took a screenshot with all plans shown. Then, for each plan in turn, I hid only that plan with a real legend click, took another screenshot and clicked it back.
- A sample on the plan's own path counts as visible if hiding the plan changes that pixel (RGB sum of differences > 30).

| Plan | Path samples where it is visible | Of samples over core cells |
|---|---|---|
| IFS HRES | **74 / 299 (24.7%)** | 74 / 245 |
| GraphCast | 150 / 299 (50.2%) | 120 / 249 |
| Pangu-Weather | **267 / 299 (89.3%)** | 229 / 245 |
| Persistence baseline | 224 / 299 (74.9%; dash gaps on white don't change) | 105 / 148 |

At 768 px in JupyterLab (same method): IFS HRES **71 / 299 (23.7%)**, GraphCast 149 (49.8%), Pangu-Weather 267 (89.3%), Persistence 223 (74.6%). Waypoint sharing and DOM order are identical.

**Pangu-Weather vs IFS HRES** (data from `gd._fullData`, pixels from the geo projection):

| Pair at 24 h | Waypoints | Identical lat/lon at the same index | Longest identical run | Coincident vertex pixels (< 1 px) |
|---|---|---|---|---|
| IFS HRES vs Pangu-Weather | 25 / 25 | **19** | **14** | 19 |
| GraphCast vs Pangu-Weather | 25 / 25 | 13 | 12 | 13 |
| IFS HRES vs GraphCast | 25 / 25 | 7 | 5 | 7 |

- **The cause is the data.** IFS HRES and Pangu-Weather share 19 of 25 waypoints exactly, 14 of them in a row, so their lines lie on the same pixels.
- **Drawing order is correct.** Pangu-Weather (trace 10) is drawn after IFS HRES (8) and GraphCast (9), so along the shared stretch **Pangu-Weather is on top**. Hiding it changes 229 of 245 samples over the core.
- So IFS HRES is the line that is partly covered: it is visible where the paths part (24.7% of its length; blue appears beside the purple in `plans-zoom-24h-final.png`).
- The builder's screenshot impression was the reverse of what happens: Pangu-Weather does not sit under IFS HRES.
- This is the same "short-lead overlap is the data" situation as in PLAN.md's B7 entry, not a defect.

### B4. Unchanged behaviour ✔

**Desync**, with real clicks only (`page.mouse.click` on slider steps, locator clicks on the dropdown, `page.mouse.move` for hovers):

| State | `.cbtitle` | `active` | Background sum | Background hover | Halos `visible` |
|---|---|---|---|---|---|
| Fresh load, 24 h | **ERA5 (truth) wind (m/s)** | 0 | 31444.1 | — | 24 h only (`d` length 1162) |
| Slider step 2, 24 h | GraphCast, lead 24 h (m/s) | 2 | 31209.8 | — | 24 h only |
| **72 h button** | **ERA5 (truth) wind (m/s)** ✔ | **0** ✔ | **31444.1** ✔ | `ERA5 (truth): 17.6 m/s` ✔ | **72 h only** ✔ (`d` 1094) |
| **Slider step 2, 72 h** | **GraphCast, lead 72 h (m/s)** ✔ | 2 | **30505.1** ✔ | `GraphCast forecast, lead 72 h: 27.3 m/s` ✔ | 72 h only |
| Slider step 0, 72 h | **ERA5 (truth) wind (m/s)** ✔ | 0 | 31444.1 ✔ | — | 72 h only |

The button `visible` arrays include the new halo traces: the 24 h halo is hidden and the 72 h halo shown. Screenshots: `desync-1-graphcast-24h-final.png`, `desync-2-after-72h-button-final.png` and `desync-3-graphcast-72h-final.png`.

**Layout:**

- I used attempt 2's measurement on these elements: title, dropdown, "Lead time", legend background and each entry, slider current value, rail and step labels, colour bar and `.cbtitle`.
- The dropdown was closed and the pointer was off the figure.
- I also checked that every element lies inside the figure.

| Width | Lead | Intersections | Outside the figure | Legend entries | Colour bar (x) | Legend right edge |
|---|---|---|---|---|---|---|
| 768 (JupyterLab) | 24 h | **0** | 0 | 5 (2 rows) | 1065–1136 page | 1023 |
| 768 (JupyterLab) | 72 h | **0** | 0 | 5 (1 row) | 1065–1136 | 1034 |
| 1,184 | 24 h | **0** | 0 | 5 (1 row) | 1110–1181 | 820 |
| 1,184 | 72 h | **0** | 0 | 5 (1 row) | 1110–1181 | 664 |

The longer colour-bar title is drawn vertically inside the colour bar (y 468–640 at 768 px), so it collides with nothing.

### Failures reported to the lead

None.

Notes:

- At 24 h, IFS HRES is visible on only 24.7% of its path, because 19 of its 25 waypoints coincide with Pangu-Weather's. That is the data, and Pangu-Weather is correctly on top.
- On its own, a persistence dash over a dark cell is 1.42:1. It reads because of the halo (2.6:1 against the halo edge), and the line mostly runs over the white gaps between cell rows.

### Teardown

- I ran a second JupyterLab pass at 768 px for B1–B3 after the first commit. Then I stopped JupyterLab (8888) and the static server (8765) by PID (`scratch/final/*.pid`), children included. Afterwards both `curl` checks exit non-zero, and nothing listens on either port.
- The browser was closed.
