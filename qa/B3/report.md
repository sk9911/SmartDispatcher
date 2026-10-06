# B3 QA: headline table readability (browser re-check)

Date: 2026-10-01 · Branch `grilltest` · HEAD `74b21b3` (the fix) · Browser: `playwright` MCP (Chrome), viewport 1700×900
Page: `qa/T19/scratch/fig.html`. It was written 13:58:31, before the 74b21b3 commit at 13:58:35, from the working tree that became 74b21b3. `headline.py` has no diff against 74b21b3. The file contains `height: 638`, `width: 1616` and `columnwidth: [160,80,158,78,78,158,78,78,158,78,78,158,78,78,100]`, so it is the fixed build.

## Summary

| Step | Check | Result |
|---|---|---|
| 1 | SBC, *F* = `fig-headline` | **PASS** |
| 2a | All 20 data rows within the visible table area, no internal scroll | **FAIL**: 11 of 20 rows fit; rows grow to 48.4 px because CI cells wrap |
| 2b | No header text clipped | **FAIL** (minor): "Time (min)" overflows its 78 px column by 2.8 px in the median and p90 headers, and the screenshot shows "Time (min" |
| 2c | Each mean (90% CI) cell on one line | **FAIL**: 35 of 80 CI cells wrap to 2 lines, including all 20 in Fuel (%) |
| 2d | Fixed decimals; Fuel (%) never shows 0 for non-zero regret | **PASS** |
| 3 | Reader view | Not readable at once: the Pangu-Weather 24 h row is cut off and the remaining 8 rows are hidden |

The *Plotly interactions* fallback was not needed: there were no clicks or hovers on Plotly elements. JupyterLab was not needed and was not started.

## Step 1: SBC

- The static server was not running (curl exit 7). I started it with `uv run python -m http.server 8765 --bind 127.0.0.1` from the repo root, and stopped it afterwards.
- I resized the viewport to 1700×900 and navigated to `http://127.0.0.1:8765/qa/T19/scratch/fig.html`.
- `document.querySelectorAll('#fig-headline .main-svg').length` = **3** ✔. The rendered `_fullLayout` has height **638** and width **1616**, as intended.
- Console errors: 1, the allowed `404 /favicon.ico` ✔
- Network: only `GET http://127.0.0.1:8765/qa/T19/scratch/fig.html → 200` ✔
- Full-page screenshot: `qa/B3/chrome.png`.

## Step 2: `browser_evaluate` checks

The scripts walk each `#fig-headline .y-column` (15 columns, 20 data cells each in block `cells1`; `cells2` is empty) and measure `getBoundingClientRect()` of each cell's `rect` and `.cell-text`, counting `tspan.line` elements per cell.

### 2a. Rows visible: FAIL

- **Expected:** all 20 rows lie inside the table's scroll area (`.scrollbar-kit`, y = 70 → 636), so no internal scroll is needed. The last row should be "Persistence baseline" with lead 120.
- **Actual:**
  - Every data row renders **48.4 px** tall, not the 28 px `ROW_H`.
  - The rows total 20 × 48.4 = 968 px against a 566 px scroll area.
  - The last row (Persistence baseline, 120) spans y = 989.6 → 1038, which is 402 px below the scroll area's bottom (636) and the figure's bottom (646).
  - Only **11 rows** are fully visible: IFS HRES ×5, GraphCast ×5 and Pangu-Weather 12. Pangu-Weather 24 is cut off, and Pangu-Weather 48–120 and all Persistence baseline rows are hidden.
  - A Plotly scrollbar glyph is drawn (height 322.9 of 566 px).
- **Cause (observed):** this follows from 2c. Plotly sets every row's height by its tallest cell, and every row has at least one 2-line CI cell (the Fuel (%) column wraps in all 20 rows). The 638 px height is right for 28 px rows: 52 + 20 × 28 = 612 px fits the 618 px domain. It does not cover wrapped rows.

### 2b. Header clipping: FAIL (minor)

- All 15 headers have at most 2 lines and text height ≤ 32.5 px, within the 52 px header.
- Rendered text matches `header.values` with `<br>` removed.
- No header is truncated, except as follows. The first line's right edge lies past its column's right edge in two headers:

  | Column | Header | Overflow |
  |---|---|---|
  | 9 | "Time (min)" / "median" | +2.8 px |
  | 10 | "Time (min)" / "p90" | +2.8 px |

  The column clip hides the overflow, so the screenshot reads "Time (min" with no closing parenthesis.
- **Expected:** no header text extends past its column.
- **Actual:** "Time (min)" needs 72.8 px of text plus the left cell padding; the column is 78 px.
- "Lead time (h)" (89.1 px) wraps onto 2 lines inside its 80 px column. That is not clipping and reads fine.

### 2c. Mean (90% CI) on one line: FAIL

- **Expected:** 1 text line per mean (90% CI) cell.
- **Actual:** 35 of 80 CI cells render as 2 `tspan.line`s (text height 32.4 px). They break after the comma inside the bracket, e.g. `0.005 [0.001,` / `0.009]`.

  | Column | Wrapped cells |
  |---|---|
  | Fuel (kg) | 5/20 (Persistence baseline rows) |
  | Fuel (%) | **20/20** |
  | Time (min) | 2/20 (Persistence baseline 72 h and 120 h) |
  | CO2 (kg) | 8/20 |

- Single-line text widths, measured with `getComputedTextLength()` in the cell font (Open Sans 13 px). Each CI column is 158 px.

  | Column | Widest | Narrowest |
  |---|---|---|
  | Fuel (kg) | 163.8 (`1953.1 [1153.9, 3069.2]`) | 89.5 |
  | Fuel (%) | 147.3 (`8.700 [4.947, 12.853]`) | 139.0 |
  | Time (min) | 139.0 (`17.80 [10.41, 28.31]`) | 114.3 |
  | CO2 (kg) | **180.4** (`12071.9 [6083.4, 18755.4]`) | 97.7 |

- Every cell of 139 px or more wrapped, so the usable width inside a 158 px column (after Plotly's cell padding) is under 139 px. To fit on one line, the widest CI text needs about 180 px plus padding on both sides. The column needs to be roughly 200 px or more, more if the full-config numbers are larger. The fixture CO2 values are already 5 digits.

### 2d. Decimals and Fuel (%): PASS

Decimals were read from the rendered DOM text. Every column uses one fixed count:

| Columns | Decimals |
|---|---|
| Lead | 0 |
| Fuel (kg), all 3 | 1 |
| Fuel (%), all 3 | 3 |
| Time (min), all 3 | 2 |
| CO2 (kg), all 3 | 1 |
| Zero-regret share | 0 (%) |

- Values ending in `.0` appear, e.g. `29.4 [6.9, 53.0]` (IFS HRES 48 h), `7.4 [0.0, 21.5]` and `64.8 [23.0, 115.5]`.
- Fuel (%) has no bare `0`.
- Fuel (%) shows `0.000` in no cell where the matching Fuel (kg) value (mean, CI bound, median, p90) is greater than 0.
- IFS HRES 12 h now reads `0.005 [0.001, 0.009]`; it was `0 [0, 0.01]`.

## Step 3: Reader view (`qa/B3/chrome.png`)

The fix is a clear improvement over T19:
- the width fits 1616 px with no horizontal clipping;
- the two-line headers read well;
- precision is consistent and Fuel (%) is meaningful.

The table still cannot be read at once:

1. **Rows hidden (severe).** The view stops at Pangu-Weather 24 h, and that row's Fuel (%) cell is cut mid-line (`0.017 [0.007,` / `0.027]` partly hidden). The persistence-baseline rows, the headline comparison, are not visible without scrolling inside the table. Nothing on the page signals that, apart from a thin scrollbar.
2. **Wrapped CI cells.** Every row is double height with mostly empty space, because Fuel (%) wraps in every row. Wrapped brackets such as `807.7 [110.5,` / `1509.6]` are harder to scan.
3. **"Time (min" header** is missing its closing parenthesis in two columns.
4. **Minor:** "CO2" is now plain text (previously the subscript ₂ was barely visible). This is readable and fine.

## Bugs reported to the lead

1. **Step 2c/2a.** The CI columns (158 px) are too narrow for their text:
   - Expected: each CI cell on one line, and all 20 rows visible in the 638 px figure.
   - Actual: 35/80 CI cells wrap, every row grows to 48.4 px, only 11/20 rows are visible, and the last row's bottom is at 1038 px against a 636 px scroll area.
   - Note: the unit test's height formula assumes 28 px rows, so it passes while the rendered table does not.
2. **Step 2b.** "Time (min)" overflows its 78 px median and p90 columns by 2.8 px and renders as "Time (min".

## Teardown

The static server (8765) was stopped (curl exit 7 afterwards). JupyterLab was never started (8888 down). The browser was closed. The scripts' raw outputs are in `qa/B3/scratch/` (gitignored).

---

## Attempt 2 (181f863)

Date: 2026-10-01 · Branch `grilltest` · HEAD `181f863` (second fix) · Browser: `playwright` MCP (Chrome), viewport 1800×1150
Page: `qa/T19/scratch/fig.html`. It was written 14:03:58, before the 181f863 commit at 14:04:13. `src/regret/figures/headline.py` has no diff against 181f863. The file contains `height: 1063`, `width: 1739`, a cells height of `49`, a header height of `57` and `columnwidth: [175,90,152,92,92,152,92,92,152,92,92,152,92,92,110]`, so it is the attempt-2 build.

### Summary

| Step | Check | Result |
|---|---|---|
| 1 | SBC, *F* = `fig-headline` | **PASS** |
| 2a | All 20 data rows within the visible table area, no internal scrollbar drawn, last row fully visible | **PASS** |
| 2b | No header text overflows its column | **PASS** |
| 2c | Each mean (90% CI) cell is exactly 2 lines (mean, then bracket), no other cell wraps, all rows the same height | **PASS** against the lead's criterion (see the note on PLAN.md below) |
| 2d | Fixed decimals; no bare 0 in Fuel (%) for non-zero regret | **PASS** |
| 3 | Reader view | **Readable at once.** All 20 rows are visible, including every Persistence baseline row next to the model rows. There is one minor non-blocking note (modebar). |

**Note on PLAN.md (for the lead).**
- The B3 check line in PLAN.md still says "column widths set so each mean (90% CI) cell fits **on one line**".
- Attempt 2 deliberately renders each CI cell on **two** lines, and step 2c of this re-run tests for two.
- "## Plan changes" has no entry recording that revision. The only B3 entry is "B3 added".
- The written check therefore does not match what was tested. The lead needs to amend the check and log the change before marking B3 [done].

Interactions: the wheel event in 2a was dispatched with `browser_evaluate` (`WheelEvent`), not a real mouse scroll. No clicks or hovers on Plotly elements were needed. JupyterLab was not needed and was not started.

### Step 1: SBC

- The static server was not running (curl exit 7). I started it with `uv run python -m http.server 8765 --bind 127.0.0.1` from the repo root and stopped it afterwards.
- I resized the viewport to 1800×1150 and navigated to `http://127.0.0.1:8765/qa/T19/scratch/fig.html`.
- `document.querySelectorAll('#fig-headline .main-svg').length` = **3** ✔. `_fullLayout` has height **1063** and width **1739**. The page measures 1800×1158, so the figure (y 8 → 1071) fits the viewport with no horizontal page scroll.
- Console errors: 1, the allowed `404 /favicon.ico` ✔
- Network: only `GET http://127.0.0.1:8765/qa/T19/scratch/fig.html → 200` ✔
- Full-page screenshot: `qa/B3/chrome-attempt2.png`.

### Step 2: `browser_evaluate` checks

Same method as attempt 1:
- The scripts walk each `#fig-headline .y-column` (15 columns, 20 data cells each in block `cells1`, plus the `header` block).
- For each cell they measure `getBoundingClientRect()` of the `rect`, the `.cell-text` and each `tspan.line`.
- Raw outputs are `qa/B3/scratch/attempt2-cells.json` and `attempt2-lines.json`, analysed by `analyze2.py`, `an2.py` and `an3.py` (gitignored).

#### 2a. Rows visible: PASS

| Element | Measured | Expected | OK |
|---|---|---|---|
| Header | y 18 → 75 (57 px) in all 15 columns | 57 px | ✔ |
| Scroll area (`.scrollbar-kit`) | y 75 → 1061 (986 px) | holds 20 × 49 = 980 px | ✔ |
| Row heights | every one of the 300 data cells is 49.0 px (one distinct height) | 49 px | ✔ |
| Row tops (col 0) | 75, 124, … , 1006 (step 49) | — | ✔ |
| Last row (`Persistence baseline`, `120`) | y 1006 → 1055, 6 px inside the area's bottom (1061) and above the figure bottom (1071) | fully visible | ✔ |
| Cells outside the scroll area | 0 of 300 | 0 | ✔ |
| Cell text outside its cell rect (vertically) | 0 of 300 | 0 | ✔ |
| Scrollbar | `.scrollbar-glyph` exists but has `stroke-opacity="0"`, so it is not drawn. None is visible in the screenshot. | no visible scrollbar | ✔ |
| Wheel event (`deltaY: 400`) on a column | first row's top stays at 75, so the table does not scroll | no scroll | ✔ |

The last row reads: `Persistence baseline | 120 | 3820.2 [1925.1, 5935.3] | 2698.1 | 7920.9 | 8.700 [4.947, 12.853] | 7.978 | 16.194 | 35.09 [17.44, 54.93] | 24.02 | 73.57 | 12071.9 [6083.4, 18755.4] | 8526.1 | 25029.9 | 0%`.

#### 2b. Header overflow: PASS

- All 15 headers fit within their columns.
- Every header line starts 8 px inside the left edge.
- The smallest right-hand gap is **11.2 px**: "Time (min)", 72.8 px of text, in the 92 px median and p90 columns. In attempt 1 the same text overflowed by 2.8 px; it now renders "Time (min)" in full.
- Other tight lines:

  | Header line | Text width | Column | Right gap |
  |---|---|---|---|
  | "Lead time" | 64.5 | 90 | 17.5 |
  | "Fuel (kg)" | 59.2 | 92 | 24.8 |
  | "Zero-regret" | 75.4 | 110 | 26.6 |
  | "mean (90% CI)" | 102.4 | 152 | 41.6 |

- Every header except "Forecast source" renders as exactly 2 lines, matching the `<br>` in `header.values`. No line is broken by Plotly.
- All header text lies inside the 57 px header: bottom gap ≥ 16.5 px.

#### 2c. Line structure: PASS (lead's criterion)

- For every CI cell (columns 2, 5, 8 and 11; 80 cells):
  - `tspan.line` count = **2**;
  - line 1 matches `^-?\d+(\.\d+)?$` (the mean);
  - line 2 matches `^\[-?\d+(\.\d+)?, -?\d+(\.\d+)?\]$` (the bracket).
  - Failures: **0 / 80**. Example: `2.1` / `[0.5, 4.1]`. The widest is `12071.9` / `[6083.4, 18755.4]`, and it does not break inside the bracket.
- Every other data cell (220 cells) renders as **1** line. Failures: 0 / 220.
- All 300 data cells are 49.0 px tall, so all rows are the same height.
- No cell line's text extends past its cell rect, horizontally or vertically. Overflow count: 0 across all header and data lines.

#### 2d. Decimals and Fuel (%): PASS

Decimals were read from the rendered text. Each column uses one count:

| Columns | Decimals |
|---|---|
| Lead | 0 |
| Fuel (kg), all 3 | 1 |
| Fuel (%), all 3 | 3 |
| Time (min), all 3 | 2 |
| CO2 (kg), all 3 | 1 |
| Zero-regret share | 0 (%) |

- Trailing zeros are kept, e.g. `0.0`, `53.0`, `0.000`, `0.20`, `2520.0`.
- Fuel (%) has no bare `0`.
- For each row, every Fuel (%) mean, CI bound, median and p90 was compared with the matching Fuel (kg) value. None shows `0.000` where the kg value is greater than 0. The `0.000` cells, e.g. IFS HRES 24 h median and GraphCast 12 h CI low, all match a `0.0` kg value.

### Step 3: Reader view (`qa/B3/chrome-attempt2.png`)

- **The whole table is readable at once.**
  - All 20 rows and 15 columns are on screen in a 1800×1150 window.
  - There is no internal scrolling.
  - All four Persistence baseline rows sit directly under the three models' rows, so the persistence-vs-model comparison is visible without scrolling. For example, Fuel (kg) mean at 120 h: 255.6 / 84.1 / 144.2 for the models against 3820.2 for persistence.
- The two-line CI cells (mean above, bracket below) scan cleanly, and the bracket never splits.
- Headers are complete and read well. "Time (min)" is no longer clipped.
- Minor, cosmetic:
  - In each row the single-line cells sit at the top of the 49 px row, while the CI cells' first line starts about 2 px lower, so the CI means sit slightly lower than the medians beside them.
  - Most rows have empty space under the single-line cells.
  - Neither affects reading.
- **Minor, non-blocking:**
  - Plotly's modebar (camera, link and logo icons) is drawn at x 1657–1745, y 10–32.5.
  - That is over the top-right of the header, on top of the "Zero-regret share" header text. It is visible in the screenshot.
  - `displayModeBar` is `'hover'`, so a reader sees it whenever the pointer is over the figure. The header stays legible apart from the icons' overlap.

### Bugs reported to the lead

No blocking failures. Two notes:
1. **PLAN.md check text is out of date.**
   - Expected: the B3 check matches what is tested.
   - Actual: PLAN.md still requires each CI cell "on one line", while attempt 2 (and this re-run's 2c) uses two lines. No Plan-changes entry records the revision.
2. **Modebar overlaps the Zero-regret header (cosmetic).**
   - Expected: no chrome over the header text.
   - Actual: the modebar is drawn at x 1657–1745, y 10–32.5 over the "Zero-regret share" header when the figure is hovered or rendered for the screenshot.

### Teardown

- The static server (8765) was stopped by killing its listener; curl exits 7 afterwards.
- JupyterLab was never started (8888 down).
- The browser was closed.
- Scratch outputs are in `qa/B3/scratch/` (gitignored).
