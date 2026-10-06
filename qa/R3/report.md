# R3 QA: the add-on figures and summaries after B15

Date: 2026-10-02 · Branch `grilltest` · HEAD `1e82a93` (B15 = `846d3d9`). The working tree was clean at the start.

## Setup

- **Browser:** `playwright` MCP (Chrome).
- **Servers:** neither was running at the start (both `curl` checks exited 7, and `lsof` found nothing on 8765 or 8888).
  - Static server on the working tree: uv PID 7572, listener PID 7574. I stopped it before serving the clone.
  - Static server on the clone: uv PID 9351, listener PID 9353. A `curl` through 8765 returned 5,965,022 bytes, the size of the clone's `reports/report.html`, which confirms it was serving the clone. I stopped it before the timed suite.
  - **JupyterLab was not started.** No R3 step uses it.
- **Hover method:** a real `page.mouse.move` through `browser_run_code_unsafe` (`scratch/measure.js`, `scratch/measure_compact.js`), after `scrollIntoView`.
  - In x-unified mode the label is `.hoverlayer .legend`: its title is the lead and its items are `.legendtext`. I found this with one manual hover first.
  - **Per (panel, lead):** the mouse goes to the lead's x, at the vertical middle of the panel. The label must meet all of these:
    - its title equals the lead;
    - it lists exactly that panel's line traces;
    - no CI-band entries;
    - every item matches `Name: mean [lo, hi] kg`;
    - mean, lo and hi equal that panel's trace data to ±0.05. Names repeat across panels, so this checks that the label belongs to the hovered panel.
  - **Per marker:** the same test with the mouse on each marker's pixel position.
- **Overlap sweep and *Fits container*:** N2's sweep (`scratch/sweep_r3.js`), limited to the two add-on figures. I reloaded the page at each width before running it.

## Verdict: FAIL on one new item (F5, the CI note is clipped); everything else passes. One wording conflict is for the lead (W1).

| # | Step | Result |
|---|---|---|
| 1a | Regenerate the fixture and full reports | **PASS**: both exit 0 (4.9 s and 5.3 s); the only output is the ipykernel TCP warning; `notebooks/` is clean afterwards |
| 1b | **F2** hover: every source at every lead in every panel, both reports, 1,200 and 768 px | **PASS**: `fig-neuralgcm` 20/20 (panel, lead) and 50/50 markers; `fig-ensemble` 5/5 and 20/20. Same in all 4 runs; **0 unreachable** |
| 1c | **F1** scale and separation | **PASS**: row 1 is 342 px tall, zero-based, linear, nothing clipped, x = the leads. Every close pair at < 9 px apart has overlapping CIs, except 4 fixture pairs that are 7.0–8.4 px apart, which is at least the 7 px marker size (details below) |
| 1d | CI pairing in the hover | **PASS**: for every line, hover `[lo, hi]` equals its band's edges; lo ≤ mean ≤ hi; the band's x equals the line's x and its colour is the line's; bands have `hoverinfo: skip` and no legend entry |
| 1e | **F3, F4** and minor items: summaries match the parquet files and the wording rules | **PASS** on the numbers, the gaps, "penal" (0) and the notes. **W1** for the lead: "forecast models" matches the _Avoid_ term "Model" |
| 1f | *Fits container* and the overlap sweep, both figures, both reports, both widths | **PASS**: 0 hits; svg ≤ client in every case |
| 1g | CI annotation visible (N2 step 4f) | **FAIL (F5)**: `fig-neuralgcm`'s "Shaded bands: 90% CI of the mean" sits at 907–925 px in a 900 px SVG, so it is clipped, in both reports at both widths |
| 2a | Clone pulled | **PASS**: `5bea60b` → **`1e82a93`** (= working-tree HEAD); `data/results/` holds only `regret.parquet` |
| 2b | Clone report: 5 figures, 3 opt-in notes, no add-on or geostrophic numbers, 0 stderr output blocks | **PASS** |
| 2c | `time REGRET_BLOCK_NETWORK=1 uv run pytest` in the clone | **PASS**: **349 passed, 1 skipped in 81.67 s**; `time` 82.77 s total |
| 3 | Guards | **PASS**: the core hash diff is empty; the core-figure JSON hash matches; `notebooks/` is clean |
| 4 | Servers stopped by PID; browser closed | **PASS** |

## Failure

**F5. Step 1g: `fig-neuralgcm`'s CI annotation is clipped off the figure (regression from B15).**
- **Expected:** the annotation "Shaded bands: 90% CI of the mean" is visible below the legend. It was visible before B15: see `qa/N2/neuralgcm-1200.png`, where it sits under the legend.
- **Actual:** the annotation is drawn but cannot be seen.
  - B15 set `height=900` and `margin.b=210`, and moved the row domains, but left the annotation at `y=-0.36` paper.
  - So its box is at **907–925 px** in a figure whose three `.main-svg` are **900 px** tall with `overflow: hidden`.
  - `elementFromPoint` at its centre returns the next `<p>`, not the annotation.
  - This happens in both reports, at 1,200 and 768 px. At 768 px the wrapped legend ends at 850 px, and the note would still start at 907 px.
- **Why the sweep missed it:** the overlap sweep and *Fits container* check only intersections and widths, not clipping at the bottom.
- **`fig-ensemble` is fine:** its note is at 448–466 px in a 520 px figure.
- **Evidence:**
  - `neuralgcm-ci-note-clipped.png`: the region below the legend, which is blank, then the summary paragraph;
  - `neuralgcm-*-1200.png` and `neuralgcm-*-768.png`: no CI note at the bottom.
- **Stop rule:** this affects only the reader view. Section 7's caption still says "shaded bands are 90% CIs", so the lead may log it as a known limitation, or add a one-line fix in `neuralgcm.py`.

## For the lead to rule on

**W1. "of the 4 forecast models" uses an avoided term.**
- CONTEXT.md, **Forecast source**: "_Avoid_: Model (ambiguous with aircraft model), provider".
- Section 7's summary says "rank 2 of the 4 forecast models (persistence baseline excluded)" twice, in both reports.
- B15's amended check line asks for exactly this phrase, so the conflict is between the plan and the vocabulary, not a B15 defect.
- A wording that follows CONTEXT.md is possible, e.g. "of the 4 forecast sources other than the persistence baseline". I am not marking this a failure.

## Step 1: fixture and full reports (working tree)

`REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture uv run regret report` and `REGRET_BLOCK_NETWORK=1 uv run regret report` both exit 0.
- `reports/report-fixture.html` is 5,770,494 bytes and `reports/report.html` is 6,007,197.
- Both reports: **0 console errors** (no favicon request this time), and the network shows only the page.
- The full report has 8 `.js-plotly-plot` and 0 stderr outputs.

### F2: hover (x unified, real mouse)

| report, width | `fig-neuralgcm` (panel, lead) | markers | `fig-ensemble` (panel, lead) | markers |
|---|---|---|---|---|
| fixture, 1,200 | 20/20 | 50/50 | 5/5 | 20/20 |
| fixture, 768 | 20/20 | 50/50 | 5/5 | 20/20 |
| full, 1,200 | 20/20 | 50/50 | 5/5 | 20/20 |
| full, 768 | 20/20 | 50/50 | 5/5 | 20/20 |

- Every label lists only the hovered panel's sources:
  - row 1: IFS HRES, GraphCast, Pangu-Weather and NeuralGCM;
  - row 2: the persistence baseline alone;
  - `fig-ensemble`: the 4 choices.
- No label has a band entry.
- **Example, fixture east 12 h** (N2's unreachable IFS HRES point): "IFS HRES: 13.3 [3.0, 23.7] kg · GraphCast: 13.7 [5.9, 21.5] kg · Pangu-Weather: 11.4 [3.0, 19.8] kg · NeuralGCM: 22.0 [8.8, 35.1] kg".
- **Example, full data at 24 h** (`fig-ensemble`): N2's unreachable mean-robust point is now listed with the other choices.
- `neuralgcm-hover-768.png` shows the label at fixture east 48 h.

### F1: scale and separation

| | fixture | full |
|---|---|---|
| `fig-neuralgcm` row 1 height | 342 px (N2: 172) | 342 px |
| row 1 y range | 0…699 kg, `tozero`, linear | 0…421 kg, `tozero`, linear |
| row 1 px/kg | **0.489** (N2: 0.23) | **0.812** (N2: 0.39) |
| row 1 largest CI upper bound | 664 (east, IFS HRES 120 h), 5% headroom | 400 (west, IFS HRES 120 h), 5% headroom |
| row 2 (persistence) | 198 px, 0…8,649 kg, 0.023 px/kg | 198 px, 0…2,024 kg, 0.098 px/kg |
| `fig-ensemble` | 270 px, 0…213 kg, 1.27 px/kg | 270 px, 0…246 kg, 1.10 px/kg |
| clipped band or line | none | none |

- The values are identical at 1,200 and 768 px, because the height is fixed.
- The x axes are linear, ticks are at 12, 24, 48, 72 and 120, and the markers sit exactly on the leads (no jitter).
- **Scale not wasted:** each row's top sits 5% above its largest CI bound.
  - The two direction panels in a row share one y axis, as in the core figure. So the panel with smaller values uses less of its height: fixture west reaches 153 of 699 kg, and full east 242 of 421 kg. This is the core figure's design, so it is not a failure.
- **Pairs closer than 9 px** (mean markers; 60 pairs on row 1, 30 in `fig-ensemble`). All are measured from the rendered pixel positions:

  | | close pairs | with CIs overlapping | with CIs not overlapping |
  |---|---|---|---|
  | fixture `fig-neuralgcm` | 41 | 37 | 4 (below) |
  | full `fig-neuralgcm` | 38 | 38 | 0 |
  | fixture `fig-ensemble` | 18 | 18 | 0 |
  | full `fig-ensemble` | 18 | 18 | 0 |

- **The 4 fixture pairs whose CIs don't overlap:**
  - east 48 h, GraphCast–NeuralGCM: 14.3 kg apart, **7.0 px**;
  - west 24 h, GraphCast against IFS HRES, Pangu-Weather and NeuralGCM: 17.1 kg apart, **8.4 px**. The other three coincide exactly with 3 westbound fixture flights.
  - The markers are 7 px wide (`size=7` in `lead_regret.py`), so each of these pairs is at least one marker width apart and the markers don't overlap. I judge them readable; the hover also lists both values with their CIs.
- **Exact ties (0 px, all with overlapping CIs):**
  - fixture west 12 h: IFS HRES = NeuralGCM;
  - fixture west 24 h: IFS HRES = Pangu-Weather = NeuralGCM;
  - fixture east 24 h: GraphCast ≈ Pangu-Weather (0.02 kg);
  - full: at least one pair within 1 kg at east 12 h.
- **N2's F1 pairs, before and after.**
  - Fixture R3 px are measured in the browser at 1,200 px.
  - Full R3 px are kg × 342 / 421.32. The axis is linear and the values agree with the measured 0.812 px/kg.
  - Full kg and CIs come from `build_neuralgcm(data/results/neuralgcm_regret.parquet)`.

  | data | direction, lead | pair | kg apart | N2 px | R3 px | CIs overlap |
  |---|---|---|---|---|---|---|
  | fixture | east 72 h | GraphCast–NeuralGCM | 10.1 | 2.3 | 4.9 | yes |
  | fixture | east 72 h | NeuralGCM–Pangu-Weather | 14.0 | 3.2 | 6.8 | yes |
  | fixture | east 72 h | GraphCast–Pangu-Weather | 24.0 | 5.5 | 11.8 | no (now separated) |
  | fixture | east 24 h | IFS HRES–NeuralGCM | 12.3 | 2.8 | 6.0 | yes |
  | fixture | east 24 h | IFS HRES–Pangu-Weather | 13.8 | 3.2 | 6.8 | yes |
  | fixture | west 48 h | IFS HRES–NeuralGCM | 11.3 | 2.6 | 5.5 | yes |
  | fixture | west 48 h | GraphCast–Pangu-Weather | 15.6 | 3.6 | 7.7 | yes |
  | fixture | west 48 h | NeuralGCM–Pangu-Weather | 28.4 | 6.5 | 13.9 | no (now separated) |
  | full | east 48 h | Pangu-Weather–IFS HRES | 13.8 | 5.4 | 11.2 | yes |
  | full | east 48 h | NeuralGCM–IFS HRES | 14.2 | 5.5 | 11.5 | yes |
  | full | east 48 h | GraphCast–IFS HRES | 15.6 | 6.1 | 12.7 | yes |
  | full | east 72 h | GraphCast–NeuralGCM | 7.2 | 2.8 | 5.8 | yes |
  | full | east 72 h | GraphCast–IFS HRES | 19.4 | 7.6 | 15.8 | yes |
  | full | west 24 h | GraphCast–NeuralGCM | 3.2 | 1.2 | 2.6 | yes |
  | full | west 24 h | GraphCast–IFS HRES | 6.6 | 2.6 | 5.4 | yes |
  | full | west 24 h | NeuralGCM–Pangu-Weather | 10.1 | 3.9 | 8.2 | yes |
  | full | west 48 h | GraphCast–IFS HRES | 4.2 | 1.6 | 3.4 | yes |
  | full | west 48 h | NeuralGCM–Pangu-Weather | 17.9 | 7.0 | 14.6 | yes |

  - Every N2 pair is now about 2.1× further apart.
  - Each pair still under 9 px has overlapping CIs. Under B15's standard ("differences smaller than the CI overlap may overlap"), these are allowed to overlap.
- Screenshots: `neuralgcm-fixture-1200.png`, `neuralgcm-fixture-768.png`, `neuralgcm-full-1200.png`, `neuralgcm-full-768.png`, and the same four for `ensemble-*`.

### F3, F4 and the minor items: summaries against the parquet files

The parquet files were recomputed by `scratch/recompute.py`; its output is in `scratch/recompute.txt`.

- **Section 7 (fixture), verbatim:**
  > On 6 flights, NeuralGCM's mean fuel regret at the shortest leads (12-24 h) is 21 kg, rank 2 of the 4 forecast models (persistence baseline excluded), 3 kg above Pangu-Weather (18 kg); at the longest lead (120 h) is 130 kg, rank 3 of the 4 forecast models (persistence baseline excluded), 49 kg above GraphCast (81 kg). Planning 12-hourly instead of 6-hourly adds roughly 15 kg of mean regret at 12-24 h for IFS HRES, GraphCast and Pangu-Weather on the same flights, so short-lead numbers here mostly reflect time resolution, not forecast quality.
- **Section 7 (full), verbatim:**
  > On 110 flights, NeuralGCM's mean fuel regret at the shortest leads (12-24 h) is 40 kg, rank 2 of the 4 forecast models (persistence baseline excluded), 1 kg above GraphCast (39 kg); at the longest lead (120 h) is 182 kg, rank 3 of the 4 forecast models (persistence baseline excluded), 29 kg above GraphCast (153 kg). Planning 12-hourly instead of 6-hourly adds roughly 32 kg of mean regret at 12-24 h for IFS HRES, GraphCast and Pangu-Weather on the same flights, so short-lead numbers here mostly reflect time resolution, not forecast quality.

| claim | fixture recomputed | full recomputed | ✔ |
|---|---|---|---|
| flights | 6 | 110 | ✔ |
| 12–24 h NeuralGCM, rank of 4 (persistence excluded) | 21.17 → 21, rank 2 | 40.29 → 40, rank 2 | ✔ |
| best, displayed | Pangu-Weather 18.07 → 18 | GraphCast 38.75 → 39 | ✔ |
| stated gap = difference of the displayed values | 21 − 18 = **3** ✔ (raw 3.09) | 40 − 39 = **1** ✔ (raw 1.54; N2's "2" is fixed) | ✔ |
| 120 h NeuralGCM, rank | 129.51 → 130, rank 3 | 182.10 → 182, rank 3 | ✔ |
| 120 h best, gap | GraphCast 80.73 → 81; 130 − 81 = 49 ✔ | GraphCast 153.10 → 153; 182 − 153 = 29 ✔ | ✔ |
| sensitivity, persistence excluded | 15.29 → "roughly 15" | 31.98 → "roughly 32" | ✔ |
| models named in the sensitivity clause | sensitivity file minus persistence = hres, graphcast, pangu → "IFS HRES, GraphCast and Pangu-Weather" | same | ✔ |

- **F3 is resolved.** Persistence's exclusion is stated in both clauses. The sensitivity clause names its 3 sources, so the reader can see that NeuralGCM is not in the sensitivity run.
- **Section 8, verbatim:**
  - fixture: "…the mean-robust plan's mean fuel regret is 61 kg against 81 kg for the best deterministic source (GraphCast). Neither choice ever beats the add-on hindsight plan (0 of 60 plans). With M = 25 the 90th percentile is close to the maximum over members, so the p90-robust plan is overly cautious and costs more fuel (mean regret 90 kg at 120 h)."
  - full: the same sentences with 121 / 153 / 0 of 1100 / 196.
  - Recomputed: M = 25; mean-robust 60.64 and 120.56; GraphCast 80.73 and 153.10; beats 0/60 and 0/1,100; p90-robust 90.14 and 195.66 ✔.
  - The floor check passes, with a max abs diff of 0.0.
- **F4 is resolved.** "penal" occurs **0** times on either full page (text and the figures' SVG text). Section 8 says "is overly cautious and costs more fuel".
- **_Avoid_ scan** (all 16 CONTEXT.md _Avoid_ lines, word-bounded; `scratch/avoid.py`, output in `scratch/avoid.txt`):
  - sections 7–8: only "model" ×2 (W1);
  - the rest of the page: the same accepted core matches as N2 ("OpenAP fuel models", "itself a model", and "error" in "wind error" and "forecast's error").
- **Section 8's opt-in note:** it lists `fetch --with neuralgcm,neuralgcm_ens`, `regret neuralgcm` and `regret ensemble`. See step 2; it shows only in the clone.
- **N2's grammar note** ("at the longest lead (120 h) is 130 kg" with no subject) is unchanged. It is minor and was not in B15's scope.

### *Fits container* and overlap sweep

| report, width | `fig-neuralgcm` svg / client / scroll | hits | `fig-ensemble` svg / client / scroll | hits |
|---|---|---|---|---|
| fixture, 1,200 | 1134 / 1154 / 1154 | 0 | 1134 / 1154 / 1154 | 0 |
| fixture, 768 | 702 / 722 / 722 | 0 | 702 / 722 / 722 | 0 |
| full, 1,200 | 1134 / 1154 / 1154 | 0 | 1134 / 1154 / 1154 | 0 |
| full, 768 | 702 / 722 / 722 | 0 | 702 / 722 / 722 | 0 |

- The sweep covered:
  - `fig-neuralgcm`: 5 titles, 5 annotations, the legend and its 5 items, and 22 tick labels (24 on the full data);
  - `fig-ensemble`: 3 titles, 1 annotation, the legend and its 4 items, and 10 tick labels.
- The page has no horizontal scroll at either width.

## Step 2: clean clone

- **Clone:** `/var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret`. It was at `5bea60b` with `?? qa_scratch/` only.
- `git pull` fast-forwarded it to **`1e82a93`**. `data/results/` holds only `regret.parquet`.
- `REGRET_BLOCK_NETWORK=1 uv run regret report` exited 0 in 5.1 s. `reports/report.html` is 5,965,022 bytes.
- **Checks at 1,200 px:**
  - **5 figures** (`fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity`), each with 3 `.main-svg`;
  - `fig-geostrophic`, `fig-neuralgcm` and `fig-ensemble` occur **0** times in the HTML;
  - **0** stderr output blocks and **0** error outputs;
  - **0** console errors; the network shows only the page;
  - headings 1–9 in order.
  - The launcher's process-level TCP warning went to the terminal, not into the report.
- **Opt-in notes**, with commands read from their `<code>` elements:

  | section | commands | right? |
  |---|---|---|
  | 6 | `uv run regret fetch --with geopotential`, `uv run regret geostrophic` | ✔ |
  | 7 | `uv run regret fetch --with neuralgcm,neuralgcm_ens`, `uv run regret neuralgcm`, `uv run regret ensemble` | ✔ |
  | 8 | `uv run regret fetch --with neuralgcm,neuralgcm_ens`, `uv run regret neuralgcm`, `uv run regret ensemble` | ✔ (N2's note is fixed) |

- **No numbers:** `\d+\s?kg` and `\d\.\d` match nothing in sections 6, 7 or 8. The digits present are static: the heading numbers, 250 hPa, 30–70°N, 2020-01-01, 2020-01-06, 12-hourly, 5-source, sections 1 to 5, 90% CIs, 50 members, and 500/700/850 hPa.
- Screenshot: `clone-chrome.png` (full page).
- **Suite:** `time REGRET_BLOCK_NETWORK=1 uv run pytest -q -rs` in the clone, with no server running:
  - **349 passed, 1 skipped, 440 warnings in 81.67 s**;
  - `time`: **82.77 s total** (96.42 s user, 19.96 s system), against a limit of 180 s;
  - the skip is `tests/test_geostrophic.py:140: no real results`, as in N2;
  - 350 tests is N2's 347 plus the 3 `def test` functions B15 added (`git show 846d3d9 -- tests | grep -c '^+def test'` = 3).
  - The clone's `git status --porcelain` stayed at `?? qa_scratch/`.

## Step 3: guards (working tree)

- `sh qa/baseline/core-hashes.sh | diff - qa/baseline/core-hashes.txt`: empty (rc 0), at the start and again at the end.
- `hashlib.sha256(build_lead_regret(pd.read_parquet("data/results/regret.parquet")).to_json().encode())` gives `cb575f4c3fa5aa58837f1886733f8462914a85936bd8d69482b70047c09c7f45`, which equals `qa/baseline/lead-regret-fig.sha256` ✔. That is the hash without a trailing newline; with one it would be `a8ee71…`.
- `git diff a416cfb -- src/regret/figures/lead_regret.py tests/test_fig_lead_regret.py` is empty.
- `git status --porcelain -- notebooks/` is empty after each `regret report` and at the end.

## Step 4: end state

- **Servers:** stopped by PID: 7574 and 7572, then 9353 and 9351. Afterwards:
  - `lsof` on 8765/8888 exits 1;
  - `ps -p` finds none of the PIDs;
  - `pgrep -fl 'ipykernel|jupyter-lab|http.server'` finds nothing.
- **Browser:** closed.
- **Working tree:** only `?? qa/R3/` before the commit.

## Files

- `report.md` (this file).
- Screenshots:
  - `neuralgcm-fixture-1200.png`, `neuralgcm-fixture-768.png`, `neuralgcm-full-1200.png`, `neuralgcm-full-768.png`;
  - `ensemble-fixture-1200.png`, `ensemble-fixture-768.png`, `ensemble-full-1200.png`, `ensemble-full-768.png`;
  - `neuralgcm-hover-768.png`: the x-unified label at fixture east 48 h;
  - `neuralgcm-ci-note-clipped.png`: F5;
  - `clone-chrome.png`.
- Scratch (gitignored):
  - `measure.js`, `measure_compact.js`, `sweep_r3.js`, `recompute.py`, `avoid.py`;
  - `recompute.txt`, `avoid.txt`, `pagetext-fixture.json`, `pagetext-full.json`;
  - `report-fixture.log`, `report-full.log`, `report-clone.log`, `pytest-clone.log`;
  - `http.log`, `http-clone.log` and the PID files.
