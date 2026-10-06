# T23 QA: regret vs lead time (`build_lead_regret`)

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `c4e9f90` (figure last changed in `eecf266`, T22) · Browser: `playwright` MCP (Chrome)
Data: `tests/fixture_results/regret.parquet`. Sources from `stats.aggregate`: `hres`, `graphcast`, `pangu`, `persistence`. Leads: 12, 24, 48, 72 and 120 h.

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_lead_regret` | **PASS** |
| 2 | SBC on `qa/T23/scratch/fig.html`, *F* = `fig-lead-regret` | **PASS** |
| 3 | Legend click: item opacity 0.5; line and CI band hidden in both subplots | **PASS** |
| 4 | Axis titles (`.xtitle`, `.ytitle`) include units `h` and `kg` | **PASS** |
| 5 | Reader view | Usable, with readability problems (see below). Not pass/fail |

The *Plotly interactions* fallback was **not** needed. `browser_click` on the legend toggle (`.legendtoggle`, found with `browser_find`) went through as a real Playwright mouse click and was not intercepted.

## Step 1: SNC

- I wrote `qa/T23/scratch/check.ipynb` (scratch, gitignored) with nbformat (`scratch/make_nb.py`).
  - Cell 1: `regret.offline.install_if_requested()`, then `os.chdir(<absolute repo root>)`.
  - Cell 2: `pd.read_parquet`, `build_lead_regret(df)` and `fig.show()`. It prints the source list, the trace count and each trace's (name, legendgroup, xaxis, showlegend), then runs `fig.write_html('qa/T23/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)`.
- JupyterLab was not running (`api/status` curl exit 7), so I started it with the exact *Shared runtime resources* command (`REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture`, port 8888, token `regret-dev`).
- I opened `http://127.0.0.1:8888/lab/tree/qa/T23/scratch/check.ipynb?token=regret-dev` and chose Run → Run All Cells. Then I polled until a plot existed and the status bar said Idle.
- `browser_evaluate` results:
  - `.jp-OutputArea .js-plotly-plot` count: **1** (≥1 ✔)
  - `[data-mime-type="application/vnd.jupyter.stderr"]` count: **0** ✔
  - status bar: `Python 3 (ipykernel) | Idle …` ✔
  - stdout: `sources ['hres', 'graphcast', 'pangu', 'persistence']`, `n_traces 16`. Each source has 4 traces with `legendgroup=<source>`: a band and a line on `x`, and a band and a line on `x2`. Only the line on `x` has `showlegend=True`.
- Note: JupyterLab's restored workspace also reopened `qa/T19/scratch/check.ipynb` in a second tab. That notebook was not run (prompts `[ ]`), so it added nothing to the counts above.
- Screenshot `qa/T23/notebook.png` was taken after I dismissed the "Jupyter news" popup and scrolled the plot into view.

## Step 2: SBC

- The static server was not running (curl exit 7), so I started it with `uv run python -m http.server 8765 --bind 127.0.0.1`.
- I navigated to `http://127.0.0.1:8765/qa/T23/scratch/fig.html`.
- `document.querySelectorAll('#fig-lead-regret .main-svg').length`: **3** (≥1 ✔)
- `browser_console_messages` (error): **0** messages ✔. There was no favicon 404 either.
- `browser_network_requests` (static included): only `GET http://127.0.0.1:8765/qa/T23/scratch/fig.html → 200` ✔
- Screenshot `qa/T23/chrome.png` (full page) was taken before any interaction.

## Step 3: Legend click

- Before the click there were 4 legend items (`#fig-lead-regret .legend .traces`): IFS HRES, GraphCast, Pangu-Weather and Persistence baseline, all with opacity `1`. Each subplot (`.subplot.xy` and `.subplot.x2y2`) had **8** `.scatterlayer .trace` elements. There is one legend item per source, and the CI bands have no legend items.
- I clicked the IFS HRES `.legendtoggle` with `browser_click` (`page.locator('.legendtoggle').first().click()`). I waited 700 ms for Plotly's double-click delay, then ran `browser_evaluate`:
  - Legend item opacity: IFS HRES **`0.5`** ✔. The other three stayed at `1`.
  - `gd.data` with `legendgroup === 'hres'`: 4 traces, all `visible: 'legendonly'`. These are `IFS HRES 90% CI` (x), `IFS HRES` (x), `IFS HRES 90% CI` (x2) and `IFS HRES` (x2) ✔. All 12 other traces stayed `visible: true`.
  - Rendered traces: `.subplot.xy` went from 8 to **6**, and `.subplot.x2y2` from 8 to **6**. The line and band of the source were each removed from **both** subplots ✔.
- Screenshot after the click: `qa/T23/legend-click.png`. IFS HRES is greyed out in the legend, and the blue line and band are gone from both panels.

## Step 4: Axis titles

`browser_evaluate` on `#fig-lead-regret text[class$="title"]`:

| Element | Text | Unit |
|---|---|---|
| `.xtitle` | `lead time (h)` | `(h)` ✔ |
| `.x2title` | `lead time (h)` | `(h)` ✔ |
| `.ytitle` | `mean fuel regret (kg)` | `(kg)` ✔ |

Because of `shared_yaxes=True`, the westbound subplot has no y title of its own. That is expected and not a failure. The labels use the CONTEXT.md terms (lead time, fuel regret, forecast source, persistence baseline).

## Step 5: Reader view

Both subplots are labelled (Eastbound and Westbound), share a y-axis and have clear titles. The legend is titled "forecast source" and uses the same colour for each source in both panels. These problems are ordered from most to least severe:

1. **The three forecast sources are squashed flat near zero.** Both panels share a linear y-axis that runs from about −515 to 8677 kg, set by the persistence baseline. Westbound persistence reaches 5665 kg at 120 h, and its CI goes above 8000 kg. Meanwhile IFS HRES, GraphCast and Pangu-Weather stay between 0 and 482 kg eastbound and between 0 and 91 kg westbound. In the westbound panel the three lines overlap almost completely along the zero gridline, and their CI bands are invisible. Eastbound, only the 72 to 120 h divergence can be made out. The figure's main question, how regret grows with lead time for each forecast source, can only be answered by hiding persistence through the legend or by zooming. A log y-axis, an independent y per panel, or persistence on its own axis would fix this. That is a design choice for the lead or builder.
2. **The persistence CI band dominates.** Its band (alpha 0.2) covers a large share of the westbound panel and is visible but heavy. The forecast sources' bands, also alpha 0.2, are visible only eastbound at 72 to 120 h. With these scales the bands are either overwhelming or invisible, not "visible but not overwhelming".
3. **Nothing on the figure says what the shaded band is.** The bands have `showlegend=False` and `hoverinfo="skip"`, so the "90% CI" name in the trace data is never shown to a reader. There is no legend entry, no annotation and no hover text for it.
4. **The x ticks don't mark the leads.** The ticks are only `50` and `100` (`dtick=None`), while the data sits at 12, 24, 48, 72 and 120 h. Markers fall between ticks, so a reader can't easily tell which lead each point is.
5. **Minor:** the westbound panel shows no y tick labels (shared axis). That is fine side by side, but a reader comparing values in the right panel has to look across to the left axis.

## Failures reported to the lead

No checked step failed. Step 5 has reader-view problems (items 1 to 4), which I sent to the lead as usability findings, not check failures.

## Teardown

JupyterLab (8888) and the static server (8765) were stopped by PID. Afterwards both `curl` checks exit 7 and `lsof` shows nothing listening. The browser was closed.
