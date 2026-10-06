# T25 QA: wind error vs fuel regret scatter (`build_wind_error`)

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `5248d20` (figure last changed in `459b679`, T24) · Browser: `playwright` MCP (Chrome)
Data: `tests/fixture_results/regret.parquet`. Forecast sources: `hres`, `graphcast`, `pangu`, `persistence`. Leads: 12, 24, 48, 72 and 120 h.

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_wind_error` | **PASS** |
| 2 | SBC on `qa/T25/scratch/fig.html`, *F* = `fig-wind-error` | **PASS** |
| 3 | Hover on a point: `.hoverlayer` text has a flight ID, a source name and a lead in hours | **PASS, via the *Plotly interactions* fallback** (`browser_hover` was intercepted) |
| 4 | Plotted points = forecast-plan rows | **PASS** (120 = 120) |
| 5 | Reader view | Usable, with readability problems (see below). Not pass/fail |

## Step 1: SNC

- I wrote `qa/T25/scratch/check.ipynb` (scratch, gitignored) with nbformat (`scratch/make_nb.py`).
  - Cell 1: `regret.offline.install_if_requested()`, then `os.chdir(<absolute repo root>)`.
  - Cell 2: `pd.read_parquet`, `build_wind_error(df)` and `fig.show()`. It prints the number of forecast-plan rows (`~is_truth_optimised`), the rows per source, each trace's (name, point count), per-source `describe()` of `wind_error_ms` and `regret_fuel_kg`, and NaN counts. Then it runs `fig.write_html('qa/T25/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)`.
- JupyterLab was not running (`api/status` curl exit 7), so I started it with the exact *Shared runtime resources* command (`REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture`, port 8888, token `regret-dev`).
- I opened `http://127.0.0.1:8888/lab/tree/qa/T25/scratch/check.ipynb?token=regret-dev` and chose Run → Run All Cells (real `browser_click` on the menu items). Then I polled until a plot existed, the status bar said Idle and `wrote fig.html` was printed.
- `browser_evaluate` results:
  - `.jp-OutputArea .js-plotly-plot` count: **1** (≥1 ✔)
  - `[data-mime-type="application/vnd.jupyter.stderr"]` count: **0** ✔
  - status bar: `Python 3 (ipykernel) | Idle` ✔
  - stdout: `forecast_plan_rows 120`; `rows_per_source {'hres': 30, 'graphcast': 30, 'pangu': 30, 'persistence': 30}`; `traces [('hres', 30), ('graphcast', 30), ('pangu', 30), ('persistence', 30)]`; `nan wind_error 0 nan regret 0`.
- Note: JupyterLab's restored workspace also reopened two other `check.ipynb` tabs (earlier QA tasks). They were not run (prompts `[ ]`), so they added nothing to the counts above.
- Screenshot: `qa/T25/notebook.png` (plot scrolled into view, Idle in the status bar).

## Step 2: SBC

- The static server was not running (curl exit 7), so I started it with `uv run python -m http.server 8765 --bind 127.0.0.1`.
- The first `browser_navigate` away from JupyterLab raised a `beforeunload` dialog (the scratch notebook had unsaved outputs). I accepted it and navigated again, so the console and network logs below are from a clean load of `fig.html`.
- `document.querySelectorAll('#fig-wind-error .main-svg').length`: **3** (≥1 ✔)
- `browser_console_messages` (error): **0** messages (0 warnings) ✔. There was no favicon 404 either.
- `browser_network_requests` (static included): only `GET http://127.0.0.1:8765/qa/T25/scratch/fig.html → 200` ✔
- Screenshot `qa/T25/chrome.png` (full page) was taken before any interaction.
- Other facts from `browser_evaluate`: 4 traces, all `mode: "markers"`; x title `wind error (m/s)`, y title `fuel regret (kg)`, legend title `forecast source`; both axes linear; `hovermode: "closest"`.

## Step 3: Hover

- `browser_hover` on `#fig-wind-error .scatterlayer .trace:nth-child(4) .points path:nth-child(1)` (first persistence point) **timed out**: Playwright reported `<rect … class="nsewdrag drag"> from <g class="draglayer cursor-crosshair"> subtree intercepts pointer events`. This is the case the *Plotly interactions* rule covers.
- **Fallback used:** `Plotly.Fx.hover(gd, [{curveNumber: 3, pointNumber: 0}])` from `browser_evaluate`. `.hoverlayer` text:
  `flight JFK-LHR-20200208T0000 · source persistence · lead (h) 12 · wind error 36.65 m/s · fuel regret 756.8 kg`
  - flight ID matches `/JFK-LHR-2020\d{4}T\d{4}/` ✔
  - source name `persistence` ✔
  - lead in hours `lead (h) 12` ✔
- Screenshot: `qa/T25/hover.png`.
- Extra evidence that a real user's mouse hover works: with `browser_run_code_unsafe` I moved the real mouse (`page.mouse.move`) to the centre of an `hres` point's bounding box. Plotly's drag layer handled it and showed a hover label: `flight LHR-JFK-20200209T1200 · source pangu · lead (h) 12 · wind error 1.18 m/s · fuel regret 0.0 kg`. The label shows a **pangu** point (1.18 m/s, 0.0 kg), not the hres point under the cursor (`LHR-JFK-20200208T1200`, 12 h: 1.02 m/s, 6.8 kg). The two are about 2 px apart in the crowded corner, so their 6 px markers overlap (see Step 5, item 1). Hover works, but in that corner a reader can't reliably reach a given point.

## Step 4: Point count

- `gd.data[i].x` is a Plotly 6 binary-encoded object (`{bdata, dtype: "f8"}`), so `.length` on it is undefined. I counted from the decoded `gd._fullData` instead:
  - `_length` per trace: hres 30, graphcast 30, pangu 30, persistence 30, **total 120**; x, y and customdata are 30 long in each trace, and `gd.calcdata` lengths match.
  - Rendered `#fig-wind-error .scatterlayer .trace .points path`: **120** (30 per trace).
- Notebook printed `forecast_plan_rows 120`. **120 = 120 ✔** No truth-optimised rows are plotted.

## Step 5: Reader view

The axes and legend are labelled with units and CONTEXT.md terms. These problems are ordered from most to least severe:

1. **Persistence squashes the three forecast sources into the bottom-left corner, just as in qa/T23.** Both axes are linear and their ranges are set by persistence: x −3.4 to 77.3 m/s, y −555 to 9365 kg. Persistence has wind error 9.6 to 73.0 m/s (median 39.1) and regret 59.9 to 8809 kg (median 1164). The forecast sources stay below 22.1 m/s and 903 kg (medians: hres 3.1 m/s / 11.4 kg, graphcast 3.2 / 14.2, pangu 3.5 / 11.4). On a 959 × 627 px plot area:
   - all 90 hres/graphcast/pangu points fit in a 252 × 57 px box, **2.4 % of the plot area**;
   - 100 kg of regret is only 6.3 px tall, and 82 of 90 forecast points are below 100 kg; **83 of 90 are within 10 px of the zero line**;
   - **514 pairs** of forecast points are closer than one marker diameter (6 px), so most of them overlap. The real-mouse hover in Step 3 landed on a pangu point while aiming at an hres one.
2. **The relationship is clear for persistence vs the rest, but not within the forecast sources.** The eye sees "bigger wind error, bigger regret" mainly as the gap between the forecast cluster and the persistence cloud (pooled Spearman ρ 0.89 over all 120 points). Within the forecast sources the data has a real monotone relationship (Spearman ρ hres 0.80, graphcast 0.81, pangu 0.59; pooled 0.76), but at this scale it is invisible, because it lives inside the 252 × 57 px cluster. Within persistence the relationship is weak (ρ 0.41): the top regrets (7037 and 8809 kg) are at 31–40 m/s, while the largest wind errors (68–73 m/s) have regrets of 230 to 2776 kg. Log axes (regret has 19 zero values among the forecast sources, so it would need `symlog`-style handling or an offset), a persistence-off default, or an inset or separate panel would fix this. That is a design choice for the lead or builder.
3. **Sources are distinguishable by colour, but only where they don't overlap.** The four colours are Plotly's defaults (`#636efa`, `#EF553B`, `#00cc96`, `#ab63fa`), all 6 px circles at opacity 1. Persistence (purple) stands apart, but only because of where it is. In the corner cluster the later traces (pangu green on top) hide earlier ones (hres blue). With no transparency or symbol differences, blue (hres) and purple (persistence) are also close in hue.
4. **This figure is inconsistent with the lead-time figure in the same report.** `build_lead_regret` uses `SOURCE_LABELS` (`IFS HRES`, `GraphCast`, `Pangu-Weather`, `Persistence baseline`) and its own palette (`#1f77b4`, `#d62728`, `#2ca02c`, `#9467bd`). `build_wind_error` shows raw IDs (`hres`, `graphcast`, `pangu`, `persistence`) in the legend and hover, with Plotly's default palette. So the same source has a different name and colour in two adjacent figures.
5. **Minor:** the figure has no title (`layout.title` is empty). Lead time is only in the hover, so the plot can't tell a reader whether large errors are all long-lead points.

## Failures reported to the lead

No checked step failed. Step 3 needed the documented `Plotly.Fx.hover` fallback, because `browser_hover` was intercepted by Plotly's drag layer. Step 5 has reader-view problems (items 1 to 4), which I sent to the lead as usability findings, not check failures.

## Teardown

JupyterLab (8888) and the static server (8765) were stopped by PID. Afterwards both `curl` checks exit 7 and `lsof` shows nothing listening on either port. The browser was closed.
