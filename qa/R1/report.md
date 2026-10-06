# R1 QA: re-check of the notebook and report after B10–B13

Date: 2026-10-01 · Branch `grilltest` · HEAD `70ebf3f` (B10 `a87f347`, B11 `224f03d`, B12 `e6e2db8`, B13 `ed0b23b`). The working tree was clean at the start.

- Browser: `playwright` MCP (Chrome).
- Data: fixture config (`REGRET_CONFIG=fixture`, `REGRET_BLOCK_NETWORK=1`).
- Step 0: `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture uv run regret report` exited 0 and rewrote `reports/report-fixture.html` at 23:14:04. Its only output was the usual ipykernel TCP warning.
- Servers: neither was running (both `curl` checks exited 7). I started both with the exact *Shared runtime resources* commands. At the end I stopped them: `lsof` shows nothing listening on 8888 or 8765, and both `curl` checks exit 7 again.
- **Concurrent edit:** `src/regret/figures/wind_error.py` and `tests/test_fig_wind_error.py` were modified in the working tree at 23:18:04, after the report was regenerated. This is the lead's B11b (commit `e6bbf6a`, made during this run). Every result below is for the committed code at `70ebf3f`. I didn't touch those files.

## Summary

| # | Check | Result |
|---|---|---|
| 1a | JupyterLab Run All on the scratch copy: 0 stderr outputs | **PASS**: 0 stderr, 0 `application/vnd.jupyter.error` |
| 1b | Exactly 5 `.jp-OutputArea .js-plotly-plot` | **PASS**: `fig-headline` 1067×2170, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error` and `fig-sanity` all 748 wide |
| 1c | `elapsed_s` < 120 | **PASS**: `elapsed_s=3.7` (Run All to Idle took 4.0 s) |
| 1d | Sanity plot areas ≥ ~180 px tall | **PASS**: 4 × 260 px tall (281 px wide) |
| 1e | Overlap sweep, all 5 figures in the notebook | **PASS**: 0 intersections in each |
| 2a | SBC: `.main-svg` for all 5 IDs | **PASS**: 3 each |
| 2b | SBC: 0 console errors except favicon | **PASS**: 0 errors and 0 warnings (no favicon 404 this run) |
| 2c | SBC: no requests outside 127.0.0.1:8765 or `data:` | **PASS**: 1 request (`report-fixture.html`); `performance` resources are empty and `PlotlyGeoAssets.topojson` is present |
| 2d | "Assumptions and limitations" with 8 bullets | **PASS**: `H3`, then a `UL` with 8 `LI` |
| 2e | `document.title` is "Forecast Regret" | **PASS** |
| 3a | Fits container, all five figures at 1,200 px | **PASS**: all `.main-svg` ≤ 1,154 px `clientWidth`, and `scrollWidth == clientWidth` |
| 3b | Overlap sweep at 1,200 px and 768 px | **PASS**: 0 intersections in every figure at both widths |
| 4a | Headline at 1,200 px: all columns in both bands, all rows, nothing clipped | **PASS** |
| 4b | Headline at 768 px: overflows, but the scroll-sideways caption is present | **PASS** |
| 4c | Fixture scatter: median lines for every source; the legend lists all of them | **FAIL**: only IFS HRES has a line. GraphCast and Pangu-Weather each have a single median point. The legend part passes (4 entries). |
| 4d | Map title reads "JFK→LHR, 2020-02-09 00:00 UTC", no overlap | **PASS** |
| 4e | Gap-count ticks are integers | **PASS**: ticks `0`, `1` (`dtick = 1`) |
| 4f | Limitations bullet 4 matches SPEC §7 | **PASS**: verbatim |
| 5a | Order as in SPEC §5.2 | **PASS** |
| 5b | Captions match figures | **FAIL** (section 4 only), same cause as 4c. Sections 1, 2, 3 and 5 match. |
| 5c | No CONTEXT.md avoided words | **PASS**: the only hits are "error" (Wind error, a defined term) and "model" (SPEC §7's own wording), as in T29 |
| 6 | `git status --porcelain -- notebooks/` empty | **PASS**: empty output |

## Failure for the lead (sent by SendMessage at the time)

**Steps 4c and 5b: on the fixture scatter, only one of three forecast sources gets a median line.**

- **Expected (B11):** the fixture scatter draws a median line for every forecast source. The caption ("lines are each source's binned median") and the in-figure note ("Lines: binned median of each source (2 common wind-error bins)") are both true.
- **Actual:** the same in `report-fixture.html` at 1,200 px and in the JupyterLab run.

  | Trace | Points (x, y) | `.js-line` `d` | Drawn as |
  |---|---|---|---|
  | IFS HRES (median) | (2.01, 0.1), (6.61, 51.9) | `M45.99,330.05L132.16,300.56` | a line ✔ |
  | GraphCast (median) | (2.70, 0.7) | `M58.93,329.67`, a move with no segment | a single marker |
  | Pangu-Weather (median) | (4.75, 33.2) | `M97.33,311.21` | a single marker |

  - The legend shows all 4 entries: IFS HRES (median), GraphCast (median), Pangu-Weather (median) and Persistence baseline. So B11's legend fix holds.
  - Screenshot: `wind-1200.png`, where the green and purple medians are single dots.
- **Likely cause (from reading the code; not tested):** `wind_error.py` makes 2 pooled-quantile bins, but at line 121 it draws a source's bin only if `len(g) >= _MIN_BIN_POINTS` (15). GraphCast's and Pangu-Weather's 30 plans don't split 15/15 across the pooled bins, so one bin is dropped for each.

## Step 1: JupyterLab run-all (scratch copy)

- **Setup:**
  - I copied `notebooks/regret_report.ipynb` to `qa/R1/scratch/regret_report.ipynb`.
  - I opened it in a fresh workspace (`/lab/workspaces/r1/tree/qa/R1/scratch/regret_report.ipynb?reset`) so nothing earlier was restored. After load, exactly one document tab was open, with path `qa/R1/scratch/regret_report.ipynb`.
- **Run:**
  - I chose Run → Run All Cells through the real menu, then polled until there was no `[*]` prompt, `elapsed_s=` was present, and the status bar said Idle.
  - Execution counts were `[1]`–`[7]`, and the status read `Python 3 (ipykernel) | Idle`.
- **Outputs:**
  - MIME types were only `text/html` and `application/vnd.jupyter.stdout`.
  - Output area: 768 px.
- **Sanity panels** (`_fullLayout.yaxisN._length`): `yaxis`, `yaxis2`, `yaxis3` and `yaxis4` are each 260 px tall and 281 px wide.
- **Overlap sweep** (`scratch/overlap.js`, copied from T29; for R1 I pasted its body into `browser_evaluate`):

  | Figure | Elements swept | Intersections |
  |---|---|---|
  | fig-headline | 2 annotations (band titles "Fuel" and "Time and CO₂") | 0 |
  | fig-showcase-map | 2 titles, 1 annotation, legend + 5 items, dropdown, slider, colour bar + 6 ticks | 0 |
  | fig-lead-regret | 4 titles, 5 annotations, legend + 4 items, 20 ticks | 0 |
  | fig-wind-error | 5 titles, 4 annotations, legend + 4 items, 23 ticks | 0 |
  | fig-sanity | 6 titles, 7 annotations, 30 ticks (T29 had 34; the gap-count axis now has 2 integer ticks) | 0 |

- **Headline band titles vs tables.** The sweep doesn't compare annotations with table cells, so I checked by hand. "Fuel" ends 4 px above the first table's top, and "Time and CO₂" ends 4 px above the second's. Neither overlaps.
- **Headline in JupyterLab.** At JupyterLab's 768 px output area, the table (1,067 px) overflows: `scrollWidth` 1,087 vs `clientWidth` 768. This is the narrow-screen case the lead accepted with the B13 caption. The caption ("…On a narrow screen, scroll the table sideways to see every column.") is present in the notebook too.
- **Polish items in the notebook:**
  - gap-count ticks are `0` and `1`;
  - the map title includes "JFK→LHR, 2020-02-09 00:00 UTC";
  - the wind note says "2 common wind-error bins", and the same single-point medians appear.
- Screenshot: `notebook.png`, showing the copy open, Idle, and the Fuel band at the top.
- **Autosave:** the copy was the only document open. Afterwards, `git status --porcelain -- notebooks/` printed nothing.

## Step 2: SBC on `reports/report-fixture.html` (1,200 × 900)

| Check | Result |
|---|---|
| `#<id> .main-svg` | 3 each for all 5 IDs ✔ |
| Console | 0 errors, 0 warnings ✔ |
| Network (`static: true`) | `GET /reports/report-fixture.html → 200` only ✔ |
| `document.title` | "Forecast Regret" ✔ |
| Limitations | `H3` "Assumptions and limitations" → `UL` with 8 `LI` ✔ |
| No horizontal page scroll | `scrollWidth` 1200 = `innerWidth` ✔ |
| Screenshot | `chrome.png` (full page) |

## Step 3: Fits container and overlap sweep

- **Fits container:** the container is `.jp-OutputArea-output`, with `overflow-x: auto`. I took the widest of each figure's three `.main-svg`.

  | Figure | 1,200 px: svg / client / scroll | 768 px: svg / client / scroll |
  |---|---|---|
  | fig-headline | 1067 / 1154 / 1154 ✔ | 1067 / 722 / 1087 (overflows; accepted with the caption cue) |
  | fig-showcase-map | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
  | fig-lead-regret | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
  | fig-wind-error | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |
  | fig-sanity | 1134 / 1154 / 1154 ✔ | 702 / 722 / 722 ✔ |

  The 768 px headline row doubles as the positive control: the same check fails where a figure really is wider than its container.
- **Overlap sweep:** run after a fresh load at each width. It found 0 intersections in every figure at 1,200 px and at 768 px. The element counts are identical to the notebook table above. There's no horizontal page overflow at either width.

## Step 4: the fixes

- **B10, headline at 1,200 px: PASS.**

  | Band | Columns | Rows |
  |---|---|---|
  | Fuel | 8: source, lead, then Fuel (kg) and Fuel (%), each as mean (90% CI), median and p90 | 20 |
  | Time and CO₂ | 9: source, lead, then Time (min) and CO₂ (kg), each as mean (90% CI), median and p90, then Zero-regret share | 20 |

  - That covers all 15 metric columns from T29, including zero-regret share.
  - Cell texts: 357 = 17 headers + 20 × 17 cells.
  - 0 cell texts extend past the output container. 0 cell texts overflow their own cell rect.
  - The tables' internal scrollbars are 0 px wide.
  - Screenshot: `headline-1200.png`.
- **B13, headline at 768 px: PASS** (the cue the lead chose).
  - Only 5 of 8 and 5 of 9 columns are fully visible.
  - The caption "On a narrow screen, scroll the table sideways to see every column." sits **above** the table: caption top 250 px, table top 317 px. It is visible in the first viewport after the section heading (`headline-768.png`).
  - The container's own sideways scrollbar is at the bottom of the 2,170 px-tall figure, so it can't be seen near the top of the table. The caption is the only cue there.
- **B11, fixture scatter: FAIL** (see above). Its legend lists all sources ✔.
- **B12 polish:**
  - **Map title: PASS.** `layout.title.text` = "Plans for JFK→LHR, 2020-02-09 00:00 UTC over the 250 hPa wind at departure". It spans x 23–706 within the 1,134 px figure and has 0 overlaps (`map-1200.png`).
  - **Gap-count ticks: PASS.** `yaxis3` has `dtick = 1` and ticks `0` and `1`, in both the report and the notebook (`sanity-1200.png`).
  - **Bullet 4: PASS.** "Winds at 1.5° under-resolve the jet core; ERA5 is treated as truth but is itself a model." That is identical to SPEC §7.
  - **Page title: PASS** (2e).
  - The headline header now says "CO₂ (kg)", fixing T29's minor note.

## Step 5: reader view (1,200 px)

**Order (5a ✔):**

1. H1 Forecast Regret
2. 1. Headline: what forecast error costs
3. 2. Showcase flight: JFK→LHR, 2020-02-09
4. 3. Regret vs lead time
5. 4. Wind error vs fuel regret
6. 5. Sanity panel
7. 6. Method, assumptions and limitations, with the H3 Assumptions and limitations

This matches SPEC §5.2 items 1–6.

**Captions (5b):**

- **Headline: matches.** It covers fuel, time and CO₂ as mean (90% CI), median and p90, by source and lead, with directions pooled. It also has the new scroll line.
- **Showcase map: matches.**
  - The hindsight band (dotted orange, "= Pangu-Weather, 24 h") lies under the forecast plans.
  - The dropdown is set to 24 h, and the slider's background reads ERA5.
  - The plans follow the darkest jet band, and the persistence plan (dashed) arcs north of it.
- **Lead time: matches** (unchanged since T29; 0 overlaps).
- **Wind error: does not match on the fixture.** "lines are each source's binned median" holds only for IFS HRES (failure above). The pinned-plan annotation is still correct ("1 plan above 580 kg shown at top edge (max 903 kg)").
- **Sanity: matches.**
  - Replay time by direction, fuel-flow range with the "max equal for all plans: same initial mass" note, and gap count and gap size, with "0 gaps" and `n=1` labels.

**Avoided words (5c ✔):**

- I grepped 36 CONTEXT.md `_Avoid_` terms, whole word and case-insensitive, over three sources:
  - `document.body.innerText`;
  - every `svg text`;
  - each figure's `data` and `layout` JSON, with `x`, `y`, `z`, `lat`, `lon` and `customdata` stripped.
- This covers the new caption, the band titles and the map title.
- Hits:
  - **"error":** in "Wind error…", "wind error (m/s)", "wind-error bins", "forecast's error", and "what forecast error costs". These are the defined **Wind error** term, or forecast inaccuracy, never regret. OK, as in T29.
  - **"model":** in "ERA5 is treated as truth but is itself a model", which is SPEC §7's wording. OK.
- No other term matched.

## Step 6: end state

- `git status --porcelain -- notebooks/` printed nothing (empty).
- Both servers are stopped; `lsof` exits 1 and both `curl` checks exit 7. The browser is closed.

## Files

- `report.md` (this file).
- Screenshots:
  - notebook: `notebook.png`;
  - report pages: `chrome.png` (SBC, full page, 1,200 px), `chrome-768.png` (full page, 768 px);
  - figures: `headline-1200.png`, `headline-768.png`, `map-1200.png`, `wind-1200.png`, `sanity-1200.png`.
- Scratch (gitignored): `regret_report.ipynb` (scratch copy), `overlap.js`, `sweep_run.js`, `nb-overlap.json`, `jupyter.log`, `http.log`, and PID files.

## Re-check after B11b (0eeca07)

HEAD `c2ad59b` (B11b = `0eeca07`), with a clean working tree.

- I regenerated the report with `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture uv run regret report`. It exited 0, and `reports/report-fixture.html` was rewritten at 23:20:29.
- The static server was not running, so I started it the same way as before and stopped it afterwards.
- I loaded the page fresh at a 1,200 × 900 viewport.
- JupyterLab was not needed for this re-check.

| Check | Result |
|---|---|
| Every forecast source's median line has a drawn segment | **PASS** (see the table below) |
| The legend lists all sources | **PASS**: IFS HRES (median), GraphCast (median), Pangu-Weather (median), Persistence baseline |
| The in-figure note describes what's drawn | **PASS**: "Lines: binned median of each source (2 common wind-error bins; a bin with fewer than 7 plans of a source is left out); faint points: single plans". Two bins are drawn for every source. |
| The section 4 caption matches | **PASS**: "lines are each source's binned median" is now true for all three sources |
| Fits container, `fig-wind-error` at 1,200 px | **PASS**: `.main-svg` 1,134 ≤ `clientWidth` 1,154, and `scrollWidth` = 1,154. The longer note spans x 189–993 inside the figure's 23–1,157, so it isn't clipped. |
| Overlap sweep, `fig-wind-error` at 1,200 px | **PASS**: 0 intersections over 5 titles, 4 annotations, the legend plus 4 items, and 23 ticks. The other four figures are also 0. |
| Console | 1 error, the `/favicon.ico` 404 (allowed) |

Median lines:

| Trace | Points (x, y) | `.js-line` `d` |
|---|---|---|
| IFS HRES (median) | (2.01, 0.1), (6.61, 51.9) | `M45.99,330.05L132.16,300.56` |
| GraphCast (median) | (2.70, 0.7), (5.06, 31.6) | `M58.93,329.67L103.04,312.13` |
| Pangu-Weather (median) | (2.55, 8.3), (4.75, 33.2) | `M56.15,325.36L97.33,311.21` |

Each source has 2 points and an `L` segment.

Screenshot: `wind-1200-b11b.png`. It shows three visible median lines (blue, green and purple) in the forecast panel.

So steps 4c and 5b now **PASS**, and every R1 item passes.

End state:

- `git status --porcelain -- notebooks/` is empty.
- Nothing listens on 8765 or 8888, and the `curl` check exits 7.
- The browser is closed.
