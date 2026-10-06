# T21 QA: showcase map (`build_showcase_map`)

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `79dc073` (B6; this commit also last touched `showcase_map.py`, an import-only change to shared colours) · Browser: `playwright` MCP (Chrome), viewport 1200 × 807 · Config: `fixture` (flight `JFK-LHR-20200209T0000`)

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_showcase_map` (fixture config) | **PASS** |
| 2 | SBC on `qa/T21/scratch/fig.html`, *F* = `fig-showcase-map`; basemap inlined; land and coastline paths drawn | **PASS** |
| 3a | 72 h dropdown: hover text of every visible plan trace includes `72 h` | **PASS** |
| 3b | Slider step 2 (after 72 h): `.cbtitle` = that source's name, and it includes `72 h` | **PASS** |
| 3c | Hover on a plan trace: `.hoverlayer` text includes its source name | **PASS** (Plotly fallback: real mouse move through `browser_run_code_unsafe`; see below) |
| 3d | Legend click: that trace's legend item opacity 0.5 | **PASS** |
| 4 | Reader view | Jet ✔ · plans hard to tell apart ✘ · background readable, with caveats · **dropdown does not keep the background in sync** ✘ (not pass/fail; findings below) |

No checked step failed. Reader-view findings 1 to 3 below are bug-fix candidates and have been sent to the lead.

## Step 1: SNC

- `qa/T21/scratch/check.ipynb` was written with nbformat (`scratch/make_nb.py`).
  - Cell 1 calls `regret.offline.install_if_requested()`, then `os.chdir(<repo root>)`, then `display(HTML(showcase_map.geo_assets_html()))`.
  - Cell 2 calls `build_showcase_map(get_config('fixture'))`, then `fig.show()` and `showcase_map.write_html(fig, 'qa/T21/scratch/fig.html')`, and prints the traces.
- JupyterLab was not running (`api/status` curl exit 7), so I started it with the exact *Shared runtime resources* command (PID in `scratch/jlab.pid`).
- The restored workspace reopened `qa/B5/scratch/check.ipynb`. I closed it; no save dialog appeared, and its file is unchanged. Only the T21 notebook was open for the counts.
- I chose Run → Run All Cells from the menu. It was finished and Idle within about 4 s.
- `browser_evaluate` results:
  - `.jp-OutputArea .js-plotly-plot`: **1** ✔
  - `[data-mime-type="application/vnd.jupyter.stderr"]`: **0** ✔
  - status bar: `Python 3 (ipykernel) | Idle` ✔
  - prompts: `[1]`, `[2]`
  - stdout: `n_traces 26`. That is the background trace, plus 5 leads × (4 sources + hindsight).
- The basemap draws in the notebook too: `window.PlotlyGeoAssets.topojson` has `world_110m`. The geo layers draw paths with `d` lengths of land 88,651, coastlines 90,656 and countries 140,422 characters.
- JupyterLab's console logged 2 × "A kernel is required to send debug messages". That is the same JupyterLab debugger-panel noise as in B5; SNC does not check the console.
- Screenshot: `qa/T21/notebook.png`. The figure renders 768 × 650 px in the notebook.

## Step 2: SBC

- The page is `fig.html` (5.3 MB), written by `showcase_map.write_html` in the notebook.
- The static server was not running (exit 7), so I started it with `uv run python -m http.server 8765 --bind 127.0.0.1` (PID in `scratch/http.pid`).
- `#fig-showcase-map .main-svg`: **3** ✔
- Console errors: **1**, the allowed `/favicon.ico` 404 ✔
- Network (`browser_network_requests`, static included): only `GET http://127.0.0.1:8765/qa/T21/scratch/fig.html → 200`. There is **no** `cdn.plot.ly` request, so the basemap is inlined ✔
- Geo layers draw non-trivial paths: `.layer.land path` `d` is 88,262 characters and `.layer.coastlines path` is 90,248 (countries 139,922) ✔
- `window.PlotlyGeoAssets.topojson` keys: `world_110m`. Plotly.js is 4.1.1.
- Screenshot: `qa/T21/chrome.png`, full page, before any interaction.

## Step 3: Interactions

Each interaction ran on a fresh page load, so no state carried over between them.

**Tools.**

- Plotly's plan traces are SVG paths with **no accessibility ref** in `browser_snapshot`, so `browser_hover` cannot target them. For 3c, I used the *Plotly interactions* fallback. In `browser_run_code_unsafe`, I took a screen point on the rendered `path.js-line` with `getPointAtLength(0.35·L)` and `getScreenCTM()`, then called `page.mouse.move` to that point. That is a real mouse event, not `Plotly.Fx.hover`.
- The dropdown (3a) and the legend toggle (3d) used `browser_click` on snapshot refs.
- The slider (3b) used `page.mouse.click` at the step's tick on the rail, also a real click.
- No scripted `Plotly.restyle` or `Plotly.relayout` was used for any check.

**a. 72 h dropdown** (`browser_click` on the header, then on `72 h`)

- The header reads `72 h▼`, and `updatemenus[0].active` is 3.
- The visible plan traces and their hover text:
  - 16 `IFS HRES plan, lead 72 h`
  - 17 `GraphCast plan, lead 72 h`
  - 18 `Pangu-Weather plan, lead 72 h`
  - 19 `Persistence baseline plan, lead 72 h`
  - 20 `Hindsight plan (Pangu-Weather, lead 24 h); shown with lead 72 h` ✔
- A real hover on the Persistence baseline path at 72 h showed `.hoverlayer` = `Persistence baseline plan, lead 72 h` ✔
- Screenshot: `qa/T21/dropdown-72h.png`.

**b. Slider step 2 after 72 h**

- Step indices count from 0, so index 2 is the third step, **GraphCast**; index 0 is ERA5. I clicked its tick at (554, 611).
- `.cbtitle` = `GraphCast forecast wind speed at 250 hPa, lead 72 h (m/s)` ✔: it has the source name and `72 h`.
- The slider's current value reads `Background: GraphCast`, and `sliders[0].active` is 2.
- Index 1 (IFS HRES) also gave the right title, in Load C.
- PLAN.md's T21 wording says "its hover text includes `72 h`". This pass rests on `.cbtitle`. The background trace's hover is `%{marker.color:.1f} m/s` (`showcase_map.py`, `hovertemplate` of the `Wind speed` trace), and the slider steps restyle only `marker.color` and the colour-bar title. So hovering the wind squares never shows the source or the lead. A reader can't hover the background to see which field is drawn, which compounds reader-view finding 1.
- Screenshot: `qa/T21/slider-step2-72h.png`.

**c. Hover** (default 24 h, real mouse move; a `plotly_hover` listener confirmed the curve)

- Persistence baseline (trace 9): `.hoverlayer` = `Persistence baseline plan, lead 24 h`, and the event curve was 9 ✔
- IFS HRES (trace 6): at the same 35% point, the hover went to **Hindsight plan** (curve 10). The hindsight line, 4 px wide and drawn later, sits on top of HRES there. See reader-view finding 4.

**d. Legend click** (`browser_click` on the Persistence baseline `.legendtoggle`, at 24 h)

- Persistence baseline opacity **`0.5`**; the other four stayed at `1` ✔
- `gd.data` with `visible: 'legendonly'`: only trace 9, Persistence baseline at 24 h ✔

## Step 4: Reader view

**Is the 2020-02-09 eastbound hindsight plan visibly riding the jet? Yes.**

- The hindsight plan is the **Pangu-Weather 24 h plan**, chosen by the tie rule. It is the red dotted line, and it runs along the yellow-green ribbon of fastest wind across the Atlantic.
- In numbers (`scratch/jet.py`, ERA5 at departure):

  | Path | Mean speed (m/s) | Mean u (m/s) |
  |---|---|---|
  | Hindsight plan | 82.7 | 76.5 |
  | Great circle | 64.0 | 60.8 |

- Latitude of the hindsight plan against the jet core (the latitude of maximum ERA5 speed at each longitude):

  | Longitude | Hindsight lat | Jet-core lat | Core speed (m/s) | Speed on hindsight (m/s) |
  |---|---|---|---|---|
  | 60°W | 44.3 | 42.0 | 99.6 | 75.8 |
  | 50°W | 47.5 | 46.5 | 102.0 | 94.6 |
  | 40°W | 49.6 | 49.5 | 109.2 | 107.5 |
  | 30°W | 51.3 | 51.0 | 105.3 | 103.1 |
  | 20°W | 52.1 | 52.5 | 98.3 | 95.8 |
  | 10°W | 52.5 | 52.5 | 75.3 | 75.3 |

  From 50°W to 10°W the plan stays within 1° of the jet core. It leaves the core only at the two ends, where it must reach JFK and LHR.

**Can the plans be told apart? Mostly not, except Persistence.**

These are rendered pixel distances on the 1200-px page: for each sampled point of one path, the distance to the nearest point of the other.

| Lead | Forecast-source pairs (HRES, GraphCast, Pangu): median gap | Persistence vs others: median gap |
|---|---|---|
| 12 h | 0.8–3.6 px | 7–11 px |
| 24 h | 0.4–3.8 px | 9–11 px |
| 48 h | 0.7–0.9 px | 8–11 px |
| 72 h | 0.7–4.0 px | 2–4 px |
| 120 h | 1.5–4.0 px | 19–21 px |

- The lines are 2 px wide, so most of a forecast-source pair's length is drawn on top of itself. At 48 h, 60–71% of each pair is within 3 px.
- **At 24 h, the default view, the Pangu-Weather plan is completely hidden.** It *is* the hindsight plan: 100% of its length lies within 0.7 px of the hindsight line, which is 4 px wide and drawn on top. The legend lists Pangu-Weather, but no purple line is visible (`chrome.png`).
- The hindsight line also covers about 75% of IFS HRES at every lead up to 48 h.
- The plan colours (blue `#1f77b4`, green `#2ca02c`, purple `#9467bd`) are hues that Viridis also uses in the background. Where a line crosses squares of its own hue, it loses contrast.
- Persistence (grey) is the only plan that clearly separates, at 12, 24, 48 and 120 h.
- This is largely the data: the plans really are similar, on a 120° × 50° map. But the figure gives the reader no way to tell overlapping plans apart, such as dashes, end labels or an inset.

**Does the wind-speed background read clearly? Yes, the jet stands out, with caveats.**

- The jet is unmistakable: a yellow-green band, about 100–111 m/s (`cmax` 111.3), against blue and purple elsewhere.
- But the field is drawn as **separate 9-px squares** on a 2.5° grid. On the Mercator projection the rows spread apart toward the north, so there are white horizontal stripes between rows, wider at high latitudes. It reads as a dot matrix, not a field.
- The colour-bar title at a forecast step, `… forecast wind speed at 250 hPa, lead 72 h (m/s)`, is 420 px tall against the 438-px bar. It just fits at 650 px figure height and would clip if the figure were shorter.

**Does the dropdown keep the slider in sync with the chosen lead? No.** This is a bug; screenshot `qa/T21/desync-72h-shows-24h-background.png`.

- After choosing 72 h, stepping through all five slider steps (run in the same load as the desync below; a fresh 72 h → step 2 also passed in step 3b) gives the right field and title at each step: `ERA5 wind speed …`, then `IFS HRES …, lead 72 h`, `GraphCast …, lead 72 h`, `Pangu-Weather …, lead 72 h` and `Persistence baseline …, lead 72 h`. The background values change at each step (sums 31444, 31067, 30505, 31558, 31649).
- **But** if the slider is already on a forecast source when the lead is changed:
  1. At 24 h, click slider step GraphCast. The title becomes `… lead 24 h`.
  2. Choose 72 h. The header reads `72 h`, the plans switch to 72 h, and the slider still reads `Background: GraphCast`. **The colour-bar title still says `GraphCast forecast wind speed at 250 hPa, lead 24 h (m/s)` and the background values are unchanged** (sum 31210 before and after).
  3. Only touching the slider again loads the 72 h field.
- The cause, from reading the code: the dropdown's `update` replaces `sliders[0].steps` but does not re-apply the active step to trace 0.
- A reader comparing leads with the slider on a source sees 72 h plans over a 24 h forecast wind, labelled "24 h" in small vertical text.

**Other findings, most severe first** (bug-fix candidates are 1 to 3):

1. **The background does not follow the dropdown** (above).
2. **The legend disappears at every lead except 24 h.** Only the 24 h traces have `showlegend=True`, and the dropdown hides them. At 12, 48, 72 and 120 h, `.legend .traces` count is **0** (`dropdown-72h.png`, `slider-step2-72h.png`). The plans are then identifiable only by hover.
   - A side effect, measured at 24 h: the legend click hides only the 24 h trace. That is correct for the check, but there are no legend entries to click at other leads.
3. **The Pangu-Weather plan is invisible at 24 h** (the default view): the hindsight line covers it exactly. The hindsight also covers most of IFS HRES, and hovering HRES returns the hindsight trace.
4. **The "Lead time" dropdown overlaps the figure title.** The bounding boxes of the menu (x 19–94, y 44–77) and the title (x 67–675, y 36–57) intersect. The "Pl" of "Plans for …" is hidden behind the dropdown in both the notebook and the page (`notebook.png`, `chrome.png`).
5. **The legend overlaps the slider's current-value label** at 24 h. `Background: ERA5` (y 580–594) collides with the legend items IFS HRES and GraphCast (y 570–589) (`chrome.png`, `notebook.png`).
6. **The plan colours share hues with the Viridis background** (blue, green, purple).
7. **Minor:** the background is a dot matrix with white stripes, not a continuous field.
8. **Minor:** the colour-bar title nearly fills the bar length at forecast steps.
9. **Minor:** the hindsight hover text reads `Hindsight plan (Pangu-Weather, lead 24 h); shown with lead 72 h`. That is accurate, but a reader may not see why a 24 h forecast plan appears under 72 h. Per CONTRACTS §6 the same hindsight path is shown at every lead, so this is by design.

## Failures reported to the lead

No checked step (1 to 3) failed. Reader-view findings 1 to 9 were sent to the lead; 1 to 3 are bug-fix candidates.

## Teardown

- JupyterLab (8888) and the static server (8765) were stopped by PID (`qa/T21/scratch/*.pid`, children first).
- Afterwards both `curl` checks exit 7, and `lsof` shows nothing listening on either port.
- The browser was closed.
