# B5 QA: regret vs lead time readability (`build_lead_regret`)

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `2e762f9` (figure last changed in `8d6fced`, B5) · Browser: `playwright` MCP (Chrome), viewport 1200 × 807

This re-runs T23's steps on the B5 figure.

- **SNC:** `tests/fixture_results/regret.parquet`.
- **SBC, legend, axes and reader view:** the full results that ship, `data/results/regret.parquet` (2,520 rows).

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_lead_regret` (fixture) | **PASS** |
| 2 | SBC on `qa/B5/scratch/fig.html` (full results), *F* = `fig-lead-regret` | **PASS** |
| 3a | Legend click IFS HRES: opacity 0.5; line and band hidden in both top-row panels | **PASS** |
| 3b | Legend click Persistence baseline: opacity 0.5; line and band hidden in both bottom-row panels | **PASS** |
| 4 | Axis titles include `h` and `kg`; x tick labels exactly 12, 24, 48, 72, 120 | **PASS** |
| 5 | A legend entry reads "shaded: 90% CI" | **PASS** |
| 6 | Reader view: forecast sources distinguishable in both directions; persistence on its own row | **Partly met**: persistence on its own row ✔; sources distinguishable in both directions only at 120 h on the full-window page, and probably not westbound in the 360 px notebook render. Not pass/fail |

The *Plotly interactions* fallback was **not** needed. `browser_click` on each `.legendtoggle`, picked by its legend text, went through as a real mouse click.

## Step 1: SNC (fixture)

- I wrote `qa/B5/scratch/check.ipynb` with nbformat (`scratch/make_nb.py`).
  - Cell 1 calls `regret.offline.install_if_requested()`, then `os.chdir(<repo root>)`.
  - Cell 2 reads the fixture parquet, calls `build_lead_regret(df)` and `fig.show()`, and prints each trace's (name, legendgroup, xaxis, yaxis, showlegend).
- JupyterLab was not running (`api/status` curl exit 7). I started it with the exact *Shared runtime resources* command.
- JupyterLab's restored workspace reopened the T19, T23 and T25 scratch notebooks. I closed them with **Discard**, so their files were unchanged, and only the B5 notebook was open for the counts.
- I chose Run → Run All Cells, then polled until there was a plot and the status bar read Idle.
- `browser_evaluate` results:
  - `.jp-OutputArea .js-plotly-plot`: **1** ✔
  - `[data-mime-type="application/vnd.jupyter.stderr"]`: **0** ✔
  - status bar: `Python 3 (ipykernel) | Idle` ✔
  - prompts: `[1]`, `[2]`
  - stdout: `n_traces 17`, which is 4 sources × 2 directions × (band + line), plus the CI key trace.
- JupyterLab's console logged 2 × "A kernel is required to send debug messages" while I closed the restored tabs. That is debugger-panel noise from JupyterLab itself, and SNC does not check the console.
- Screenshot: `qa/B5/notebook.png`.

## Step 2: SBC (full results)

- I built `qa/B5/scratch/fig.html` with `scratch/make_fig.py`: `build_lead_regret(pd.read_parquet('data/results/regret.parquet'))`, then `fig.write_html(path, include_plotlyjs=True, div_id=FIG_ID)`. I ran it with `REGRET_BLOCK_NETWORK=1`.
- The static server was not running (exit 7), so I started it with `uv run python -m http.server 8765 --bind 127.0.0.1`.
- `#fig-lead-regret .main-svg`: **3** ✔
- Console errors: **1**, the allowed `/favicon.ico` 404 ✔
- Network: only `GET http://127.0.0.1:8765/qa/B5/scratch/fig.html → 200` ✔
- Screenshot `qa/B5/chrome.png`, full page, taken before any click.

Layout from `gd._fullLayout`:

- It is a 2 × 2 grid: `x`/`y` and `x2`/`y2` on the top row, `x3`/`y3` and `x4`/`y4` on the bottom.
- The column titles read Eastbound and Westbound. The row titles read "Forecast sources" and "Persistence baseline".
- Rendered traces per panel: `xy` 7, `x2y2` 6, `x3y3` 2, `x4y4` 2. The extra trace in `xy` is the CI key.

## Step 3: Legend clicks

There are 5 legend items: IFS HRES, GraphCast, Pangu-Weather, Persistence baseline and "shaded: 90% CI", all at opacity `1` to start.

**a. IFS HRES**

I clicked its `.legendtoggle` and waited 700 ms.

- Legend opacity: IFS HRES **`0.5`**; the others stayed at `1` ✔
- `gd.data` with `visible: 'legendonly'`: exactly 4 traces, `IFS HRES 90% CI` and `IFS HRES` on `x` and on `x2` ✔
- Rendered traces went from 7 to **5** on `xy` and from 6 to **4** on `x2y2`. The bottom row stayed at 2 and 2 ✔
- Screenshot: `qa/B5/legend-click-hres.png`. The top-row y-range autoscaled from 521 to 298 kg once HRES was hidden.

I clicked IFS HRES again to restore it. All opacities returned to 1 and 0 traces were `legendonly`.

**b. Persistence baseline**

- Legend opacity: Persistence baseline **`0.5`**; the others stayed at `1` ✔
- `legendonly`: exactly 4 traces, the band and line on `x3` and on `x4` ✔
- Rendered traces: `x3y3` went from 2 to **0** and `x4y4` from 2 to **0**. The top row was unchanged at 7 and 6 ✔
- Screenshot: `qa/B5/legend-click-persistence.png`.

## Step 4: Axes

The titles are `#fig-lead-regret text[class$="title"]`. In the 2 × 2 grid the x title sits only on the bottom row and the y title only on the left column. The classes are therefore `x3title`, `x4title`, `ytitle` and `y3title`, not T23's `.xtitle` and `.x2title`. That is a selector change, not a failure.

| Element | Text | Unit |
|---|---|---|
| `.x3title` | `lead time (h)` | ✔ |
| `.x4title` | `lead time (h)` | ✔ |
| `.ytitle` | `mean fuel regret (kg)` | ✔ |
| `.y3title` | `mean fuel regret (kg)` | ✔ |

X tick labels, read as text from the rendered `.x3tick` and `.x4tick` elements:

- `x3` and `x4` (bottom row): exactly `12, 24, 48, 72, 120` ✔
- `x` and `x2` (top row): none rendered (`showticklabels: false`, from `shared_xaxes`). Their `tickvals` are `[12,24,48,72,120]` and the vertical gridlines sit at those leads. Expected.

All 8 axes have `type: "linear"` ✔. `yaxis2` matches `y`, and `yaxis4` matches `y3`, so each row shares one y-axis.

## Step 5: CI label

- The legend item text **"shaded: 90% CI"** is present, with a grey square swatch ✔.

## Step 6: Reader view (full results)

**The y-ranges:**

- The **top row** runs from −31.6 to 521.2 kg. Its maximum is set by westbound IFS HRES's upper CI at 120 h (493.6 kg). The forecast sources alone set the range, and persistence no longer squashes them ✔.
- The **bottom row** runs from 248 to 1,967 kg, set by the persistence baseline's westbound upper CI (1,881 kg).
- Persistence is clearly shown on its own row, labelled "Persistence baseline" in both the row title and the legend ✔.

**Separation.** Each top-row panel's plot area is 276 px tall, about 0.50 px per kg. The table gives the smallest vertical gap between any two of the three forecast sources' mean markers, from `yaxis.l2p(mean)`:

| Lead (h) | Eastbound min gap | Westbound min gap |
|---|---|---|
| 12 | 0.0 px | 0.3 px |
| 24 | 0.4 px | 1.0 px |
| 48 | 0.3 px | 1.3 px |
| 72 | 0.3 px (HRES 9 px apart from the pair) | 3.4 px |
| 120 | **21.1 px** | **9.3 px** |

Gaps at 120 h, in px from the top of the plot:

- **Eastbound:** IFS HRES 147, Pangu-Weather 182, GraphCast 203. That is 226, 157 and 115 kg. All three are clearly separated ✔.
- **Westbound:** IFS HRES 79, GraphCast 158, Pangu-Weather 167. That is 362, 205 and 187 kg. HRES stands well clear, and GraphCast and Pangu-Weather are 9 px apart. Their markers (about 6 px) don't overlap, but their CI bands overlap completely.

**Pairwise detail.** The min-gap column shows only the closest pair. Eastbound, IFS HRES separates from the other two from 48 h: it is 5 px away at 48 h and 9 px at 72 h. GraphCast and Pangu-Weather coincide there, within 0.4 px. Westbound, all three stay within 3.4 px up to 72 h.

**Answer, full-window page (807 px):**

- **12–24 h:** the three sources are **not** distinguishable in either direction (gaps ≤ 1 px).
- **48–72 h:**
  - Eastbound, IFS HRES separates (5–9 px), but GraphCast and Pangu-Weather lie on top of each other.
  - Westbound, the three are not distinguishable at 48 h, and only marginally at 72 h (3.4 px, less than one marker width).
- **120 h:** all three are distinguishable in **both** directions.
  - Eastbound: HRES > Pangu-Weather > GraphCast, with gaps of 21 px or more.
  - Westbound: HRES > GraphCast > Pangu-Weather. HRES is 78 px clear, but GraphCast and Pangu-Weather are only 9 px apart and their CI bands overlap completely.

So B5 fixed T23's main problem: persistence no longer squashes the forecast sources, and the growth with lead time is plain. But the sources are distinguishable in both directions only at the longest lead. Whether that meets B5's criterion is the lead's call.

**Estimate for the notebook platform (not measured).**

- The measured row height fits rows ≈ (figure height − 180) × 0.44 px: (807 − 180) × 0.44 = 275.9, against a measured `yaxis._length` of 275.88.
- At the notebook's 360 px, that gives rows of about 79 px, about 0.14 px per kg.
- At 120 h, the westbound gap between GraphCast and Pangu-Weather would then be about 2.7 px, smaller than the roughly 6 px markers, and the eastbound minimum gap about 6 px.
- So in JupyterLab, westbound GraphCast and Pangu-Weather are probably indistinguishable even at 120 h. `qa/B5/notebook.png` is the fixture render, which is consistent with this: the top-row lines are compressed into about 80 px.

Remaining problems, most severe first:

1. **The figure sets no `height`, so in JupyterLab it renders 360 px tall** (`qa/B5/notebook.png`).
   - Each row is then only about 79 px, which undoes much of B5's gain on the notebook platform (see the estimate above).
   - The two left y titles ("mean fuel regret (kg)") overlap each other.
   - The right-hand row titles "Forecast sources" and "Persistence baseline" run into each other and sit against the legend.
   - None of this occurs on the full-window `fig.html` (807 px).
   - Bug-fix candidate: set an explicit figure height.
2. **The lines overlap at short leads.** This is the data, not the scale:
   - At 12–24 h, the three means differ by under 6 kg in both directions, inside their CIs.
   - Westbound, the three stay within 3.4 px up to 72 h.
   - Eastbound, GraphCast and Pangu-Weather coincide up to 72 h.
   - Where lines overlap, only the last-drawn colour (green, Pangu-Weather) shows.
   - Fixing this would take a dash or marker symbol per source, or an inset or zoom for 12–72 h. That is a design choice.
3. **The shared row y-axis wastes eastbound space.** The eastbound data reach only 273 kg (upper CI), but the axis runs to 521 kg because of westbound. The eastbound lines use about the bottom 55% of the panel. This is a trade-off for comparing the two directions.
4. **Minor:** clicking the "shaded: 90% CI" legend entry does nothing visible. It greys out, but all 8 CI bands stay drawn, because it is a dummy trace with no `legendgroup`.
5. **Minor:** the legend title "forecast source" now also covers "Persistence baseline" and the CI key.
6. **Minor:** the CI key's swatch is neutral grey, while the bands themselves are tinted per source.

## Failures reported to the lead

No checked step (1 to 5) failed. Step 6 findings 1 to 6 are reader-view and usability findings, sent to the lead.

## Teardown

- JupyterLab (8888) and the static server (8765) were stopped by PID (`qa/B5/scratch/*.pid`).
- Afterwards both `curl` checks exit 7, and `lsof` shows nothing listening on either port.
- The browser was closed.
