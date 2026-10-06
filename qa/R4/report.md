# R4 QA: re-check B16

Date: 2026-10-02 · Branch `grilltest` · HEAD `aed6a23` (B16 = `e8cca04`). The working tree was clean at the start.

## Setup

- **Browser:** `playwright` MCP (Chrome). Viewport 1200×900 and 768×900. I reloaded the page after every resize.
- **Servers:** neither was running at the start: both `curl` checks exited 7, and `lsof` found nothing on 8765 or 8888.
  - Static server on the repo root: uv PID 14160, listener PID 14162.
  - **JupyterLab was not started.** No R4 step uses it.
- **Scripts** (`qa/R4/scratch/`, gitignored):
  - `sweep.js` and `measure.js` are R3's `sweep_r3.js` and `measure_compact.js`, copied unchanged;
  - `cinote.js` is new and does the CI-note check;
  - `all.js` runs all three for one report and width, and saves the element screenshots;
  - `avoid.py` does the wording scan.
- **Hover:** a real `page.mouse.move` through `browser_run_code_unsafe`, after `scrollIntoView`. This is a superset of "one lead per panel": the mouse visits every (panel, lead) at the panel's vertical middle, and then every marker.
  - A label passes only if all of these hold:
    - its title is the lead;
    - it lists exactly that panel's sources;
    - every item matches `Name: mean [lo, hi] kg`;
    - the numbers equal the trace data to ±0.05.

## Verdict: PASS. One method note (M1) for the lead to accept.

| # | Step | Result |
|---|---|---|
| 1a | Regenerate both reports | **PASS**: fixture exit 0 in 5.0 s and full exit 0 in 5.4 s. The only output is the ipykernel TCP warning. `notebooks/` is clean afterwards |
| 1b | CI note visible on `fig-neuralgcm` and `fig-ensemble`, both reports, 1,200 and 768 px | **PASS** on the box (inside `.main-svg` in all 8 cases) and on paint order. **M1:** a plain `elementFromPoint` returns the Plotly `svg-container` `<div>` for **both** figures, because Plotly sets `pointer-events: none` on all its SVG |
| 1c | Wording: section 7 says "of the 4 forecast sources other than the persistence baseline"; no `_Avoid_` term in sections 6–8 | **PASS**: the phrase appears 2× in each report; "forecast models" appears 0×; **0** hits for all 36 `_Avoid_` terms plus the `penal` stem |
| 1d | *Fits container* and overlap sweep, both add-on figures | **PASS**: 0 hits in all 8 runs, with the CI note included in the sweep; the svg is ≤ the client width every time; no page h-scroll |
| 1e | Hover reaches every source | **PASS**: `fig-neuralgcm` 20/20 (panel, lead) and 50/50 markers; `fig-ensemble` 5/5 and 20/20. Same in all 4 runs |
| 2 | SBC, both reports, all 8 figure IDs | **PASS**: each figure has 3 `.main-svg`. Console: fixture has only the `/favicon.ico` 404 (allowed), full has 0. Network shows only the page |
| 3 | `time REGRET_BLOCK_NETWORK=1 uv run pytest` in the working tree | **PASS**: **351 passed in 81.35 s**; `time` 82.44 s total, against a limit of 180 s |
| 4 | Guards | **PASS**: the core hash diff is empty (rc 0); the core-figure JSON hash matches; `git status --porcelain -- notebooks/` is empty |
| 5 | Servers stopped by PID; browser closed | **PASS** |

## Step 1b: CI note (`cinote.js`)

For each figure, the script finds the `.annotation` matching `/Shaded bands|90% CI/` and scrolls it to the centre of the viewport. It then measures the annotation's box against its `.main-svg`, and runs `elementFromPoint` at the box's centre.

| report, width | `fig-neuralgcm` note box (top–bottom) / svg height | inside | `fig-ensemble` note box / svg height | inside |
|---|---|---|---|---|
| fixture, 1,200 | 870.5–888.5 / 900 | ✔ | 447.5–465.5 / 520 | ✔ |
| fixture, 768 | 870.5–888.5 / 900 | ✔ | 447.5–465.5 / 520 | ✔ |
| full, 1,200 | 870.5–888.5 / 900 | ✔ | 447.5–465.5 / 520 | ✔ |
| full, 768 | 870.5–888.5 / 900 | ✔ | 447.5–465.5 / 520 | ✔ |

- Horizontally, the note is inside the svg too: for example, `fig-neuralgcm` at 1,200 px spans 481.5–702.5 of 1134.
- In R3 the note sat at 907–925 px in the same 900 px svg. **F5 is resolved.**
- The texts are:
  - `fig-neuralgcm`: "Shaded bands: 90% CI of the mean";
  - `fig-ensemble`: "Shaded bands: 90% CI of the mean. Regret is floored at 0 against the NeuralGCM add-on hindsight plan."
- At 768 px the wrapped legend ends above the note. The overlap sweep finds 0 legend–annotation hits, and `neuralgcm-*-768.png` shows the gap.

### M1: `elementFromPoint` cannot return a Plotly annotation (method note, not a defect)

- **Expected (the check as written):** `elementFromPoint` at the note's centre returns the annotation text.
- **Actual:** it returns `DIV.user-select-none.svg-container` for **both** figures, in both reports, at both widths.
  - This includes `fig-ensemble`, whose note R3 judged visible. So the result does not depend on where the note is.
  - **Cause:** Plotly sets computed `pointer-events: none` on every level from `text.annotation-text` up to `svg.main-svg`:
    - `text.annotation-text`, `g.cursor-pointer`, `g.annotation-text-g`, `g.annotation`, `g.infolayer`, `svg.main-svg`.
  - Hit-testing therefore skips them. In R3's F5 the hit was the next `<p>`, which is outside the figure; here it is the figure's own container, which shows the point lies on the figure.
- **Paint-order check I used instead:**
  - The script injected a page-only stylesheet setting `pointer-events: all` on `#<id> .main-svg *`, ran `elementsFromPoint` at the note's centre, and removed the stylesheet again. Nothing in the repo changed.
  - The stack is `svg.main-svg` (the transparent hover-layer svg), then `text.annotation-text`, then `rect.bg`.
  - The topmost painted element (skipping the transparent `svg`/`g` containers) is the annotation text in all 8 cases.
- The element screenshots show the note drawn: `neuralgcm-{fixture,full}-{1200,768}.png` and `ensemble-*`.
- **For the lead:** accept the paint-order check as the check's intent, or reword the check. I am not marking this a failure.

## Step 1c: wording (`avoid.py`, output in `scratch/avoid.txt`)

- **What I scanned:** the text from the section 6 heading up to the section 9 heading, in document order.
  - HTML blocks are read with `innerText`, and each figure's `.main-svg text` with `textContent`.
  - `<script>` JSON is excluded.
  - Section 9 (SPEC §7's limitation wording) is out of scope.
- **Section 7, fixture, verbatim:**
  > On 6 flights, NeuralGCM's mean fuel regret at the shortest leads (12-24 h) is 21 kg, rank 2 of the 4 forecast sources other than the persistence baseline, 3 kg above Pangu-Weather (18 kg); at the longest lead (120 h) is 130 kg, rank 3 of the 4 forecast sources other than the persistence baseline, 49 kg above GraphCast (81 kg). …
- **Section 7, full, verbatim:**
  > On 110 flights, NeuralGCM's mean fuel regret at the shortest leads (12-24 h) is 40 kg, rank 2 of the 4 forecast sources other than the persistence baseline, 1 kg above GraphCast (39 kg); at the longest lead (120 h) is 182 kg, rank 3 of the 4 forecast sources other than the persistence baseline, 29 kg above GraphCast (153 kg). …
- **Counts, per report:**
  - the exact phrase: **2**;
  - "forecast models": **0**;
  - the numbers are unchanged from R3.
- **Terms checked:** all 36 terms from the 16 `_Avoid_` lines in CONTEXT.md, word-bounded with an optional plural, plus the stem `penal`. **0 hits** in sections 6–8 of either report.
  - Positive control: the same regex finds "models" in R3's old phrase.
- **W1 is resolved.**

## Steps 1d and 1e: *Fits container*, overlap sweep and hover

| report, width | `fig-neuralgcm` svg / client / scroll | hits | hover | `fig-ensemble` svg / client / scroll | hits | hover |
|---|---|---|---|---|---|---|
| fixture, 1,200 | 1134 / 1154 / 1154 | 0 | 20/20, 50/50 | 1134 / 1154 / 1154 | 0 | 5/5, 20/20 |
| fixture, 768 | 702 / 722 / 722 | 0 | 20/20, 50/50 | 702 / 722 / 722 | 0 | 5/5, 20/20 |
| full, 1,200 | 1134 / 1154 / 1154 | 0 | 20/20, 50/50 | 1134 / 1154 / 1154 | 0 | 5/5, 20/20 |
| full, 768 | 702 / 722 / 722 | 0 | 20/20, 50/50 | 702 / 722 / 722 | 0 | 5/5, 20/20 |

- **Sweep coverage, with 0 elements dropped:**
  - `fig-neuralgcm`: 5 titles, **5 annotations (the CI note is one)**, the legend and its 5 items, and 22 tick labels (24 on the full data);
  - `fig-ensemble`: 3 titles, 1 annotation (the CI note), the legend and its 4 items, and 10 tick labels.
- `scrollWidth` equals `innerWidth` at both widths.
- **Hover sample labels** (`fig-neuralgcm`, east 12 h):
  - fixture: "IFS HRES: 13.3 [3.0, 23.7] kg · GraphCast: 13.7 [5.9, 21.5] kg · Pangu-Weather: 11.4 [3.0, 19.8] kg · NeuralGCM: 22.0 [8.8, 35.1] kg";
  - full: "IFS HRES: 13.5 [8.9, 19.1] kg · GraphCast: 14.4 [10.2, 19.6] kg · Pangu-Weather: 13.9 [9.5, 19.0] kg · NeuralGCM: 14.4 [9.8, 19.6] kg".
- **Unchanged from R3:**
  - the y scales (fixture row 1 is 0…699 kg at 0.489 px/kg; nothing is clipped);
  - the CI pairing (every check is OK);
  - the 4 fixture close pairs whose CIs don't overlap, all 7.0–8.4 px apart.

## Step 2: SBC

| | fixture | full |
|---|---|---|
| `.main-svg` count for each of the 8 IDs (`fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity`, `fig-geostrophic`, `fig-neuralgcm`, `fig-ensemble`) | 3 each | 3 each |
| console errors | 1: `/favicon.ico` 404 (allowed) | 0 |
| network | only `/reports/report-fixture.html` | only `/reports/report.html` |
| screenshot | `chrome-fixture.png` | `chrome-full.png` |

- Both were read straight after the first load, before any hover.
- `scratch/http.log` confirms that only the two reports, `/` (the `curl` check) and `/favicon.ico` were requested.

## Step 3: full suite

- `time REGRET_BLOCK_NETWORK=1 uv run pytest -q -rs`, in the working tree with no server on 8765 or 8888:
  - **351 passed, 440 warnings in 81.35 s**;
  - `time`: 82.44 s total (96.12 s user, 20.04 s system);
  - log in `scratch/pytest.log`.
- **Test count:** R3's clone had 349 passed and 1 skipped. Here:
  - the geostrophic test runs, because the working tree has real results;
  - B16 added 1 test.

## Step 4: guards (run after the suite)

- `sh qa/baseline/core-hashes.sh | diff - qa/baseline/core-hashes.txt`: empty, rc 0.
- `sha256(build_lead_regret(pd.read_parquet("data/results/regret.parquet")).to_json().encode())` gives `cb575f4c3fa5aa58837f1886733f8462914a85936bd8d69482b70047c09c7f45`. That equals `qa/baseline/lead-regret-fig.sha256` (stripped) ✔.
- `git status --porcelain -- notebooks/`: empty.

## Step 5: end state

- **Static server:** stopped by PID (14162, then 14160), before the suite. Afterwards:
  - `ps -p` finds neither PID;
  - `lsof` on 8765/8888 exits 1;
  - `pgrep -fl 'ipykernel|jupyter-lab|http.server'` finds nothing, and it still finds nothing after the suite.
- **Browser:** closed.
- **Working tree:** only `?? qa/R4/` before the commit.

## Files

- `report.md` (this file).
- Screenshots:
  - `chrome-fixture.png`, `chrome-full.png` (SBC);
  - `neuralgcm-fixture-1200.png`, `neuralgcm-fixture-768.png`, `neuralgcm-full-1200.png`, `neuralgcm-full-768.png`;
  - `ensemble-fixture-1200.png`, `ensemble-fixture-768.png`, `ensemble-full-1200.png`, `ensemble-full-768.png`.
- Scratch (gitignored):
  - scripts: `cinote.js`, `sweep.js`, `measure.js`, `all.js`, `avoid.py`;
  - outputs: `avoid.txt`, `s68-fixture.json`, `s68-full.json`;
  - logs: `report-fixture.log`, `report-full.log`, `pytest.log`, `http.log`, `http.uvpid`.
