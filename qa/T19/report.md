# T19 QA: headline table (`build_headline`)

Date: 2026-10-01 · Branch `grilltest` · Tested on HEAD `d9b2f1f` (code under test unchanged since; PLAN.md T19 check reworded in `ac8a02d` mid-run) · Browser: `playwright` MCP (Chrome)
Data: `tests/fixture_results/regret.parquet` (126 rows: 6 flights × 4 sources × 5 leads + 6 truth-optimised rows)

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SNC for `build_headline` | **PASS** |
| 2 | SBC on `qa/T19/scratch/fig.html`, *F* = `fig-headline` | **PASS** |
| 3 | Table data rows == printed `n_groups` | **PASS** under the revised check (`ac8a02d`): 20 == 20 forecast source × lead pairs. It failed under the original wording (20 ≠ 21); see below |
| 4 | Visual review | Usable, with readability problems (see below). Not pass/fail |

The *Plotly interactions* fallback was not needed: the only clicks were on JupyterLab menus, and no click or hover on Plotly elements was required.

## Step 1: SNC

- `qa/T19/scratch/check.ipynb` (scratch, gitignored) was written with nbformat. Cell 1: `regret.offline.install_if_requested()`. Cell 2: `os.chdir(<absolute repo root>)` (absolute, so a re-run is idempotent), `pd.read_parquet`, `build_headline(df)`, `fig.show()`, prints `n_groups` and `n_forecast_groups`, then `fig.write_html('qa/T19/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)`.
- JupyterLab was not running (`api/status` curl exit 7). I started it with the exact *Shared runtime resources* command (`REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture`, port 8888, token `regret-dev`).
- I opened `http://127.0.0.1:8888/lab/tree/qa/T19/scratch/check.ipynb?token=regret-dev` and ran Run → Run All Cells.
- `browser_evaluate`:
  - `.jp-OutputArea .js-plotly-plot` count = **1** (≥1 ✔)
  - `[data-mime-type="application/vnd.jupyter.stderr"]` count = **0** ✔
  - status bar text = `Python 3 (ipykernel) | Idle …` (contains `Idle` ✔)
  - stdout output: `n_groups=21`, `n_forecast_groups=20`
- Screenshot: `qa/T19/notebook.png`.

## Step 2: SBC

- The static server was not running (curl exit 7). I started it with `uv run python -m http.server 8765 --bind 127.0.0.1` from the repo root.
- Navigated to `http://127.0.0.1:8765/qa/T19/scratch/fig.html`.
- `document.querySelectorAll('#fig-headline .main-svg').length` = **3** (≥1 ✔)
- `browser_console_messages` (level error): **0** messages ✔ (no favicon 404 either)
- `browser_network_requests` (including static): only `GET http://127.0.0.1:8765/qa/T19/scratch/fig.html → 200` ✔
- Screenshot: `qa/T19/chrome.png` (full page).

## Step 3: Row count (PASS under revised check)

- `browser_evaluate` on `#fig-headline`, first `.y-column`: block `cells1` has **20** `.column-cell`s, block `cells2` has 0, and the `header` block has 1 (`Forecast source`). Data rows = **20**.
- Cross-check: `document.getElementById('fig-headline').data[0].cells.values[0].length` = **20**. All 20 rows are in the DOM, so the scroll blocks do not cause an undercount.
- **Expected** (check as worded): data rows == `n_groups` = distinct `source × lead_h` pairs in the fixture results = **21**.
- **Actual:** 20.
- **Cause:** the difference is the truth-optimised row (`source="truth"`, `lead_h=0`). CONTRACTS §2 (`stats.aggregate`: "forecast-plan rows only") and §6 (headline is a `go.Table` from `stats.aggregate(df)`) say the table must exclude it. The table therefore matches the contract. The number of forecast-only pairs (`n_forecast_groups`) is **20 = rows ✔**. The check's wording should say "distinct forecast source × lead pairs (`is_truth_optimised == False`)". The lead was told about this mid-run. This is not a builder bug.
- **Resolution:** while this run was in progress the lead reworded the check in `ac8a02d` to "distinct forecast source × lead pairs … truth-optimised rows excluded, as in `stats.aggregate`". `check.ipynb` printed that value as `n_forecast_groups=20` (the notebook was written before the rewording; the extra `n_groups=21` print is the old, literal definition). 20 table rows == 20 → **PASS**.

Table contents look right: sources in order of first appearance (IFS HRES, GraphCast, Pangu-Weather, Persistence baseline), each with leads 12, 24, 48, 72, 120. There is no truth/lead-0 row. The 15 columns are the 15 header values. Labels use the CONTEXT.md terms (forecast source, lead time, regret, zero-regret share, persistence baseline) with no `_Avoid_` words.

## Step 4: Visual review

The values are sensible. Regret grows with lead time for every source; the only exception is persistence 48 h > 72 h, which is plausible at n = 6. The persistence baseline is far worse than the three forecast sources (e.g. 120 h: 3820 kg vs 84 to 256 kg). Zero-regret shares are multiples of 1/6 (0%, 33%, 50%, 67%), which matches n = 6 per group. CO₂ ≈ 3.16 × fuel (e.g. 2.1 kg → 6.7 kg).

Readability problems, from most to least severe:

1. **Rows hidden below the fold (standalone page).** The figure has no explicit height. In `chrome.png` only 9 of 20 rows are visible (up to GraphCast 72 h). The rest, including all Pangu-Weather and Persistence baseline rows, are reachable only by scrolling inside the Plotly table, and nothing on the page hints at that. In a report, a reader could miss most of the headline result.
2. **Notebook rendering is cramped (`notebook.png`).** In JupyterLab's output width, the 15 columns squeeze together. Header text is clipped or runs into the next column ("Forecas source", "regret:mediarp90", "ero-regr are"), and only about 1.5 data rows show in the table viewport.
3. **CI cells wrap across 2 to 3 lines.** Cells like `29.4 [6.9, 53]` and `0.02 [0, 0.06]` break mid-bracket in narrow columns, which makes the table tall and hard to scan.
4. **Inconsistent precision.** `_num` strips trailing zeros, so precision varies within a cell and a column (`29.4 [6.9, 53]`, `1628.5 [843.6, 2520]`, `0.1` next to `0.12`). The columns do not align on the decimal point.
5. **Rounded-to-zero means look like zero regret.** IFS HRES 12 h shows Fuel (%) mean `0 [0, 0.01]`, but its fuel regret mean is 2.1 kg and the zero-regret share is 33%. A reader could take `0` to mean no regret.
6. **Minor:** in the header, the `₂` of `CO₂` renders as a very small subscript, almost invisible at this size.

## Bugs reported to the lead

- **Check wording (step 3), resolved by the lead in `ac8a02d`:** the original wording gave `n_groups` = 21 (it counted the truth-optimised row), but the table has 20 rows. The table is correct per CONTRACTS, and the step passes under the revised wording.
- **Usability (step 4, items 1 and 2):** 11 of 20 rows hidden without scrolling inside the table on the standalone page, and clipped or overlapping headers in the notebook. Items 3 to 6 are polish. Note: the report notebook (T28b) renders via `fig.to_html(..., include_plotlyjs=False)`, not `fig.show()`, so item 2 may look different there. Item 1 holds for `build_headline`'s output as returned (no layout height).

## Teardown

JupyterLab (8888) and the static server (8765) were stopped, and the browser was closed.
