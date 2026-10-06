# N2 QA: the NeuralGCM add-on and ensemble robust plan on both paths

Date: 2026-10-02 · Branch `grilltest` · HEAD `5bea60b` (D3 = `4507fc4`, N3 = `5e674fd`). The working tree was clean at the start.

- **Browser:** `playwright` MCP (Chrome).
- **Servers:** neither was running at the start (both `curl` checks exited 7, and `lsof` found nothing on 8765 or 8888).
  - Path (a): I started both from the working tree's root with the *Shared runtime resources* commands:
    - static server: uv PID 96516, listener PID 96525;
    - JupyterLab (`REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture`, confirmed in the listener's environment): uv PID 96517, listener PID 96524.
    - I stopped all four before path (b).
  - Path (b): I served **the T32 clone's root** on 8765 (uv PID 99245, listener PID 99247). I stopped it before the timed suite, so no server was running during `pytest`.
- **Overlap sweep:** R2's `sweep_r2.js` with the ID list extended to all 8 figures (`scratch/sweep_n2.js`). Legend items are compared with each other, and the same script records *Fits container* (the widest `.main-svg` against the `.jp-OutputArea-output` `clientWidth`).
  - **Positive control:** at 768 px I moved `fig-neuralgcm`'s legend onto the bottom row's x-axis titles (`Plotly.relayout`, `legend.y: -0.08`). The method then reported 4 hits (the legend and one item against each of `x3title` and `x4title`), so the 0 counts below mean something. I reloaded the page afterwards.
- **Plotly interactions:** hovers used a real `page.mouse.move` via `browser_run_code_unsafe`, after `scrollIntoView` (*Plotly interactions* rule).
  - The mouse goes to each marker's pixel position (`xaxis._offset + l2p(x)`, `yaxis._offset + l2p(y)`), and I read `.hoverlayer .hovertext` after 150 ms.
  - If the source's name is missing, a ±8 px grid in 2 px steps is searched. The search starts at dx = −8, so "found at −8" in the scratch output is search order, not a required offset.
  - A point counts as **unreachable** only if no position in that grid shows its source's name.
- **Distinguishability threshold:** fixed before measuring, as in R2: the 9 px marker size.

## Verdict: FAIL, on two reader-view items of `fig-neuralgcm`; everything else passes

| # | Step | Result |
|---|---|---|
| 1a | Regenerate the fixture report | **PASS**: rc 0 (5.1 s) |
| 1b | SBC, 8 figure IDs | **PASS**: 3 `.main-svg` each; 1 console error, the allowed `/favicon.ico` 404; network shows only the page; `chrome.png` |
| 1c | "Assumptions and limitations" has 8 bullets | **PASS**: 8 |
| 1d | Section order 6, 7, 8, 9 | **PASS** |
| 2 | *Fits container* (1,200 px) and overlap sweep (1,200 and 768 px), all 8 figures | **PASS**: 0 hits; everything fits except the accepted B13 headline at 768 px, which has its scroll caption |
| 3 | JupyterLab Run All on a scratch copy, fixture config | **PASS**: 8 `.jp-OutputArea .js-plotly-plot`, 0 stderr outputs, 0 errors, **`elapsed_s=3.6`**, Idle |
| 4a | Captions state the reduced method | **PASS** |
| 4b | Summaries match the fixture parquet files, recomputed | **PASS** on the numbers. Note F3: persistence is left out of the sentence without saying so |
| 4c | Persistence on its own row | **PASS** |
| 4d | Sources distinguishable (px gaps) | **FAIL** (F1): `fig-neuralgcm`'s forecast-source row is crushed at 12–72 h. `fig-ensemble` has near-ties only (note) |
| 4e | Hover reachable for every source (real mouse) | **FAIL** (F2): `fig-neuralgcm` 5 of 50 points unreachable (fixture); `fig-ensemble` 20 of 20 |
| 4f | CI annotation present | **PASS** on both |
| 4g | Titles name N flights and M | **PASS** |
| 4h | No avoided words | **PASS** on literal terms. One stem match for the lead to rule on (F4: "over-penalises") |
| 5 | Full working-tree report: 8 figures, *Fits container* at 1,200 px, summaries match `data/results`, recomputed | **PASS**. The F1 and F2 failures also occur on the full data: 2 of 50 `fig-neuralgcm` points and 1 of 20 `fig-ensemble` points are unreachable |
| 6a | Clone pulled to HEAD; `data/results/` has only `regret.parquet` | **PASS**: `5e674fd` → **`5bea60b`** |
| 6b | SBC with the 5 core IDs | **PASS**: 0 console errors; network shows only the page |
| 6c | Sections 6, 7 and 8 show opt-in notes naming the right commands, with no numbers | **PASS** |
| 6d | 0 stderr output blocks | **PASS** |
| 6e | *Fits container* and the overlap sweep at both widths | **PASS** |
| 6f | `time REGRET_BLOCK_NETWORK=1 uv run pytest` in the clone, < 180 s | **PASS**: **346 passed, 1 skipped, in 83.7 s** wall clock (pytest: 82.58 s) |
| 7 | Baseline hashes; `notebooks/` clean; servers stopped; browser closed | **PASS** |

## Failures (step, expected, actual)

**F1. Step 4d / 5: `fig-neuralgcm` forecast sources are not distinguishable at 12–72 h.**
- **Expected:** at each lead, the forecast-source markers are far enough apart to tell apart (≥ 9 px, the marker size), except for real near-ties in the data.
- **Actual:** row 1 (forecast sources) is 172 px tall.
  - Its y range is −45…701 kg on the fixture and −20…422 kg on the full data.
  - That range is set by IFS HRES's 120 h CI band (upper 664 kg on the fixture, ~400 kg westbound on the full data).
  - So the scale is 0.23 px/kg on the fixture and 0.39 px/kg on the full data: 9 px is 39 kg and 23 kg respectively.
  - At 12–72 h, most source pairs sit within a few px, although many differ by 5–24 kg. That is the same failure mode as S4's geostrophic figure, which B14 fixed by zooming the axis.
- **Pairs closer than 9 px that are not data near-ties (≥ 3 kg apart)**, from `scratch/gaps_kg.py`, which recomputes the per-direction means from the parquet files. They match the figure's `_fullData` to 0.01 kg.

  | data | direction, lead | examples (kg apart → px apart) |
  |---|---|---|
  | fixture | east 72 h | GraphCast–NeuralGCM 10.1 kg → 2.3 px; NeuralGCM–Pangu-Weather 13.9 → 3.2; GraphCast–Pangu-Weather 24.0 → 5.5 |
  | fixture | east 24 h | IFS HRES–NeuralGCM 12.3 → 2.8; IFS HRES–Pangu-Weather 13.8 → 3.2 |
  | fixture | west 48 h | IFS HRES–NeuralGCM 11.3 → 2.6; GraphCast–Pangu-Weather 15.6 → 3.6; NeuralGCM–Pangu-Weather 28.4 → 6.5 |
  | full | east 48 h | IFS HRES–Pangu-Weather 13.8 → 5.4; IFS HRES–NeuralGCM 14.2 → 5.5; GraphCast–IFS HRES 15.6 → 6.1 |
  | full | east 72 h | GraphCast–NeuralGCM 7.2 → 2.8; GraphCast–IFS HRES 19.4 → 7.6 |
  | full | west 24 h | GraphCast–NeuralGCM 3.2 → 1.2; GraphCast–IFS HRES 6.6 → 2.6; NeuralGCM–Pangu-Weather 10.1 → 3.9 |
  | full | west 48 h | GraphCast–IFS HRES 4.2 → 1.6; NeuralGCM–Pangu-Weather 17.9 → 7.0 |

  - At 12–72 h, every lead in both directions has at least one such pair on both data sets.
- **Real near-ties, which are notes, not failures:**
  - Full data, eastbound 12 h: all four sources within 0.9 kg (13.5–14.4).
  - Fixture, westbound 12 and 24 h: IFS HRES, NeuralGCM and Pangu-Weather are 23.6–23.8 kg. With 3 westbound fixture flights the means coincide exactly.
- **Screenshots:** `neuralgcm-1200.png` (fixture), `neuralgcm-full.png` (full data). In both, the 12–72 h lines read as one bundle.
- `fig-ensemble` does not fail this item:
  - its y range is 0…213 kg (fixture) and 0…246 kg (full) on 270 px;
  - its sub-9 px pairs are within ~1.5 kg (e.g. fixture 12 h: mean-robust 21.3, p90-robust 22.1, GraphCast 21.7, NeuralGCM 22.9; full 24 h: mean-robust 39.3 vs p90-robust 40.1 vs GraphCast 38.1).

**F2. Step 4e / 5: some `fig-neuralgcm` and `fig-ensemble` points cannot be reached by hover.**
- **Expected:** a real mouse can bring up every source's hover label at every lead.
- **Actual:** `hovermode` is `closest` in both figures, and a coincident or near-coincident marker of another trace wins. The geostrophic figure uses `x unified` since B14, which lists every source at a lead. These points stayed unreachable even with the ±8 px search:

  | data | figure | unreachable (source, panel, lead) | what the hover shows instead |
  |---|---|---|---|
  | fixture | `fig-neuralgcm` (5/50) | IFS HRES east 12 h (13.3 kg); IFS HRES west 12, 24, 48 h; Pangu-Weather west 24 h | NeuralGCM |
  | fixture | `fig-ensemble` | none (20/20) | — |
  | full | `fig-neuralgcm` (2/50) | IFS HRES west 24 h (66.2 kg); Pangu-Weather east 12 h (13.9 kg) | Pangu-Weather 66.5; NeuralGCM 14.4 |
  | full | `fig-ensemble` (1/20) | Mean-robust plan 24 h (39.3 kg) | GraphCast 38.1 |

  - 16 further `fig-neuralgcm` points on the fixture (19 on the full data) need the nearby search: the mouse on the marker itself shows another source.

## Step (a): fixture report (`reports/report-fixture.html`)

- `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture uv run regret report` exited 0 in 5.1 s. Its only output was the ipykernel TCP warning that T28b and N3 noted.
- `reports/` is gitignored, so `git status` can't show whether the file changed.

### SBC (1,200 × 900)

- `document.title` is "Forecast Regret".
- 8 figures in page order, each with 3 `.main-svg`: `fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity`, `fig-geostrophic`, `fig-neuralgcm` and `fig-ensemble`.
- **Console:** 1 error, the allowed `/favicon.ico` 404.
- **Network:** only `GET /reports/report-fixture.html → 200`.
- 0 stderr and 0 error outputs. No horizontal page scroll (`scrollWidth` 1200).
- Section headings: 1 … 5, then "6. Stretch: geostrophic balance at 250 hPa", "7. NeuralGCM add-on: 5-source comparison", "8. Ensemble robust plan (NeuralGCM ensemble)" and "9. Method, assumptions and limitations".
- "Assumptions and limitations" (an h3 in section 9) has **8 bullets**. The last reads "The IFS ensemble is unused (no 250 hPa in WeatherBench 2), and so is GenCast; GFS is not in WeatherBench 2."
- Screenshot: `chrome.png` (full page).

### Fits container and overlap sweep (fresh load at each width)

| Figure | 1,200 px: svg / client / scroll | hits | 768 px: svg / client / scroll | hits |
|---|---|---|---|---|
| fig-headline | 1067 / 1154 / 1154 ✔ | 0 | 1067 / 722 / 1087 (accepted B13 case; caption "On a narrow screen, scroll…" present) | 0 |
| fig-showcase-map | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-lead-regret | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-wind-error | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-sanity | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-geostrophic | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-neuralgcm | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-ensemble | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |

- `fig-neuralgcm` swept 5 titles (`gtitle`, `x3title`, `x4title`, `ytitle` and `y3title`), 5 annotations, the legend and its 5 items, and 19 tick labels.
- `fig-ensemble` swept 3 titles, 1 annotation, the legend and its 4 items, and 10 tick labels.
- The page has no horizontal scroll at either width.
- Screenshots: `neuralgcm-768.png` and `ensemble-768.png`.

## Step 3: JupyterLab Run All (scratch copy, fixture config)

- I copied `notebooks/regret_report.ipynb` to `qa/N2/scratch/regret_report.ipynb` and opened it at `/lab/tree/qa/N2/scratch/regret_report.ipynb`, then chose Run → Run All Cells from the real menu.
- I waited until no prompt showed `[*]` and the `elapsed_s=` output was present:
  - **all 10 code cells executed** (`[1]` … `[10]`);
  - **8** `.jp-OutputArea .js-plotly-plot`, in the 8 IDs' order;
  - **0** `application/vnd.jupyter.stderr` outputs and **0** error outputs;
  - output MIME types: `text/html`, `text/markdown` and `application/vnd.jupyter.stdout` (only `elapsed_s=3.6`);
  - Kernel status: Idle.
- **`elapsed_s=3.6`** (limit 120).
- Screenshot: `notebook.png`.
- JupyterLab also restored a `check.ipynb` tab from an earlier QA task's workspace. It was hidden, never run, and had 0 outputs; the counts above are for the `regret_report.ipynb` panel only.
- **Config:** PLAN's *Shared runtime resources* says an N2 check on the full config restarts JupyterLab with `REGRET_CONFIG=full`. The lead's brief and N2's check line ask for the fixture config, so I ran the fixture. The full config's notebook ran in step 5 through `regret report` (8 figures, 0 stderr), not through the JupyterLab UI.

## Step 4: reader view of sections 7 and 8 (fixture)

### Captions (static markdown)

- **Section 7:**
  > Reduced method: only the flights with a NeuralGCM initialisation at every lead (departures from 2020-01-06), and every source, not only NeuralGCM, planned from the steps at the lead and 12 h later (12-hourly planning), so differences between sources are not time-resolution differences. The add-on has its own candidate set (the truth-optimised plan and all five forecast sources) and its own results, separate from sections 1 to 5; the core experiment is unchanged. Lines are means and shaded bands are 90% CIs.

  This covers matched flights from 2020-01-06 ✔ and 12-hourly planning for all sources ✔. The flight count is in the data-driven summary and the figure title ("6 flights" on the fixture, "110 flights" on the full data).
- **Section 8:**
  > On the add-on's flights and 12-hourly planning, a plan is made on each of M members … Regret is floored at 0 against the add-on's hindsight plan, and the share of flights where a chosen plan beats it is reported. M is a subset of the 50 members, chosen from measured run time (cost grows with the square of M). The IFS ensemble and GenCast are not used: WeatherBench 2 stores them only at 500/700/850 hPa.

  This covers M from measured cost ✔ and regret floored against the add-on hindsight plan ✔. M = 25 is in the summary and the title. The figure's annotation repeats the floor.

### Summaries against the parquet files (`scratch/recompute.py`)

- **Section 7 summary (fixture), verbatim:**
  > On 6 flights, NeuralGCM's mean fuel regret at the shortest leads (12-24 h) is 21 kg, rank 2 of 4 forecast sources, 3 kg above Pangu-Weather (18 kg); at the longest lead (120 h) is 130 kg, rank 3 of 4 forecast sources, 49 kg above GraphCast (81 kg). Planning 12-hourly instead of 6-hourly adds roughly 15 kg of mean regret at 12-24 h for the core forecast sources on the same flights, so short-lead numbers here mostly reflect time resolution, not forecast quality.

  | claim | recomputed (`tests/fixture_results/`) | ✔ |
  |---|---|---|
  | 6 flights | `flight_id.nunique()` = 6 | ✔ |
  | NeuralGCM 12–24 h pooled mean 21 kg | 21.17 | ✔ |
  | rank 2 of 4; Pangu-Weather 18 kg; 3 kg above | Pangu-Weather 18.07, NeuralGCM 21.17, IFS HRES 22.07, GraphCast 24.44 (persistence 713.48 excluded); gap 3.10 | ✔ |
  | 120 h: 130 kg, rank 3 of 4, 49 kg above GraphCast (81 kg) | GraphCast 80.73, Pangu-Weather 118.14, NeuralGCM 129.51, IFS HRES 229.84; gap 48.78 | ✔ |
  | sensitivity "roughly 15 kg" at 12–24 h, core forecast sources | mean of `regret_12h_kg − regret_6h_kg` at 12 and 24 h over IFS HRES, GraphCast and Pangu-Weather = **15.29**; with persistence included = 11.40 | ✔ (see F3) |

- **Section 8 summary (fixture), verbatim:**
  > The robust plans use M = 25 of the 50 members. At 120 h the mean-robust plan's mean fuel regret is 61 kg against 81 kg for the best deterministic source (GraphCast). Neither choice ever beats the add-on hindsight plan (0 of 60 plans). With M = 25 the 90th percentile is close to the maximum over members, so the p90-robust plan over-penalises (mean regret 90 kg at 120 h).

  | claim | recomputed | ✔ |
  |---|---|---|
  | M = 25 | `members.unique()` = [25] | ✔ |
  | mean-robust 120 h 61 kg | 60.64 | ✔ |
  | best deterministic at 120 h is GraphCast, 81 kg | 80.73 (from `neuralgcm_regret.parquet`, persistence excluded) | ✔ |
  | 0 of 60 beat the hindsight plan | `beats_hindsight.sum()` = 0, 60 rows | ✔ |
  | p90-robust 120 h 90 kg | 90.14 | ✔ |

- **Floor:** every ensemble row's `regret_fuel_kg` equals `fuel_kg − min(add-on hindsight fuel, own fuel)` (max abs diff 0.0). Regret ≥ 0 in both files. The fixture has 2 zero-regret rows of 60 and the full data 162 of 1,100. Both are far from the ≥ half that the test-only fallback would give.
- In the sensitivity table, `regret_12h_kg` equals `regret_12h_core_set_kg` exactly on the fixture; on the full data the max difference is 0.014 kg. This matches N1c's "≤ 0.02 kg".

### Figures

- **Titles:**
  - "5-source comparison on 6 flights, 12-hourly planning" (N ✔);
  - "Ensemble robust plans (M = 25 members), 6 flights, 12-hourly planning" (M ✔, N ✔).
- **Persistence on its own row:**
  - `fig-neuralgcm` is 2 × 2: Eastbound and Westbound columns, with a "Forecast sources" row (y and y2, domain 0.57–1) and a "Persistence baseline" row (y3 and y4, domain 0–0.43).
  - Only persistence traces are on x3/x4, and no persistence trace is on row 1. ✔
- **CI annotation:**
  - `fig-neuralgcm`: "Shaded bands: 90% CI of the mean";
  - `fig-ensemble`: "Shaded bands: 90% CI of the mean. Regret is floored at 0 against the NeuralGCM add-on hindsight plan." ✔
  - Every band's `fillcolor` is its source's line colour at alpha 0.2 (0.15 in `fig-ensemble`), with line width 0. All band traces have `hoverinfo: skip` and no legend entry.
- **Distinguishability and hover:** see F1 and F2.
  - `fig-ensemble` is fine on separation: near-ties only, all 20 points reachable on the fixture.
  - Line styles in `fig-ensemble`: robust plans solid (star, pentagon); NeuralGCM and GraphCast dashed (triangle, diamond).
- Screenshots: `neuralgcm-1200.png` and `ensemble-1200.png`.

### Words

- I grepped every CONTEXT.md _Avoid_ term (36 terms, word-bounded, case-insensitive, plural allowed) over the page text, scripts and styles excluded, including the figures' SVG text (`scratch/avoid.py`).
- **Sections 7 and 8: 0 literal matches** on both the fixture and the full report.
- **Stem match, for the lead to rule on (F4):** "the p90-robust plan **over-penalises**" in the section 8 summary shares the stem of the _Avoid_ term "Penalty" (avoided for Regret). Here it describes the p90 criterion's treatment of plans, not regret.
- The rest of the page (core sections, unchanged since T32) matches "model" twice ("OpenAP fuel models", "ERA5 … is itself a model") and "error" 9 times ("wind error", the CONTEXT term, and "a weather forecast's error"). Earlier QA tasks accepted these; they are outside the add-on.

## Step 5: full report (working tree)

- **Before:** `data/results/` has `regret.parquet`, `geostrophic.parquet`, `neuralgcm_regret.parquet`, `neuralgcm_sensitivity.parquet` and `ensemble_regret.parquet`.
- `REGRET_BLOCK_NETWORK=1 uv run regret report` exited 0 in 5.2 s; `reports/report.html` is 6,004,257 bytes. The only output was the ipykernel TCP warning.
- **Checks at 1,200 px:**
  - **8 figures**, each with 3 `.main-svg`;
  - **0** console errors;
  - network: only `GET /reports/report.html → 200`;
  - 0 stderr.
- ***Fits container* at 1,200 px:** all 8 pass (`fig-headline` 1067/1154, the other 7 1134/1154, scroll = client). The overlap sweep found 0 hits.
- **Titles:**
  - "5-source comparison on 110 flights, 12-hourly planning";
  - "Ensemble robust plans (M = 25 members), 110 flights, 12-hourly planning".
- **Section 7 summary (full), verbatim:**
  > On 110 flights, NeuralGCM's mean fuel regret at the shortest leads (12-24 h) is 40 kg, rank 2 of 4 forecast sources, 2 kg above GraphCast (39 kg); at the longest lead (120 h) is 182 kg, rank 3 of 4 forecast sources, 29 kg above GraphCast (153 kg). Planning 12-hourly instead of 6-hourly adds roughly 32 kg of mean regret at 12-24 h for the core forecast sources on the same flights, so short-lead numbers here mostly reflect time resolution, not forecast quality.

  | claim | recomputed (`data/results/`) | ✔ |
  |---|---|---|
  | 110 flights, first departure 2020-01-06 | 110; `departure_time.min()` = 2020-01-06 00:00 | ✔ |
  | 12–24 h: NeuralGCM 40, rank 2 of 4, GraphCast 39, 2 kg above | GraphCast 38.75, NeuralGCM 40.29, Pangu-Weather 40.78, IFS HRES 41.69; gap 1.54 | ✔ |
  | 120 h: 182, rank 3 of 4, 29 above GraphCast 153 | GraphCast 153.10, Pangu-Weather 170.51, NeuralGCM 182.10, IFS HRES 250.53; gap 29.00 | ✔ |
  | sensitivity "roughly 32 kg" | 31.98 without persistence (23.97 with it); per source: IFS HRES 33.6, Pangu-Weather 32.2, GraphCast 30.2 | ✔ (see F3) |

  The 120 h values match N1c's plan-change entry (GraphCast 153, Pangu-Weather 171, NeuralGCM 182, IFS HRES 251, persistence 1,249).
- **Section 8 summary (full), verbatim:**
  > The robust plans use M = 25 of the 50 members. At 120 h the mean-robust plan's mean fuel regret is 121 kg against 153 kg for the best deterministic source (GraphCast). Neither choice ever beats the add-on hindsight plan (0 of 1100 plans). With M = 25 the 90th percentile is close to the maximum over members, so the p90-robust plan over-penalises (mean regret 196 kg at 120 h).

  This recomputes to M = 25, mean-robust 120.56, GraphCast 153.10, 0 of 1,100 rows beat the hindsight plan, and p90-robust 195.66 ✔. These match S1's plan-change entry (44/39/54/75/121 and 45/40/59/86/196).
- Screenshots: `neuralgcm-full.png` and `ensemble-full.png`.

## Step 6 (path b): clean clone

- **Clone:** `/var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret`.
  - Before the pull it was at `5e674fd`, and `status --porcelain` showed only `?? qa_scratch/` (from T32).
  - `git pull` fast-forwarded it to **`5bea60b`** (PLAN.md and docs/CONTRACTS.md), the same as the working tree's HEAD.
  - `data/results/` holds **only `regret.parquet`**.
- **Report:** `REGRET_BLOCK_NETWORK=1 uv run regret report` exited 0 in 5.1 s; `reports/report.html` is 5,964,929 bytes.
  - I stopped the working-tree servers first, then served the clone's root.
  - `curl` through 8765 returned the same 5,964,929 bytes, which confirms the server was serving the clone.
- **SBC (1,200 px):**
  - **5 figures** (headline, showcase map, lead regret, wind error and sanity), each with 3 `.main-svg`;
  - `fig-geostrophic`, `fig-neuralgcm` and `fig-ensemble` occur **0** times anywhere in the HTML;
  - **0** console errors (no favicon request this time);
  - network: only the page;
  - 0 stderr and 0 error outputs. Section order 6, 7, 8, 9.
  - Screenshot: `clone-chrome.png` (full page).
- **Opt-in notes** (each a `text/markdown` output, 1,154 × 52 px, with `<code>` for the commands):

  | section | note's commands | right? |
  |---|---|---|
  | 6 | `uv run regret fetch --with geopotential`, `uv run regret geostrophic` | ✔ |
  | 7 | `uv run regret fetch --with neuralgcm,neuralgcm_ens`, `uv run regret neuralgcm` | ✔ |
  | 8 | `uv run regret ensemble` "(after `uv run regret neuralgcm`)" | ✔ (see the notes) |

- **No numbers:** over each section's text, `\d+\s?kg` matches nothing and `0\.\d` matches nothing in all three sections.
  - All the digits present are static: heading numbers, 250 hPa, 30–70°N, 2020-01-01, 2020-01-06, 12-hourly, 5-source, 90% CIs, 50 members, 500/700/850 hPa, and "sections 1 to 5".
  - No summary sentence is present.
- ***Fits container* and overlap sweep:**
  - 1,200 px: `fig-headline` 1067/1154, the other 4 1134/1154; 0 hits.
  - 768 px: `fig-headline` 1067/722/1087 (accepted B13), the other 4 702/722; 0 hits.
- **Suite:** `time REGRET_BLOCK_NETWORK=1 uv run pytest` in the clone at `5bea60b`, run after `regret report` (so `uv` had already synced), with no server running:
  - **346 passed, 1 skipped, 440 warnings in 82.58 s**;
  - `time`: **83.74 s total** (97.09 s user, 19.97 s system). The limit is 180 s.
  - The skip is `tests/test_geostrophic.py:140: no real results`, as in R2. I confirmed it with `-rs` on that file. 346 + 1 = 347, N3's count.
  - The clone's `git status --porcelain` stayed at `?? qa_scratch/`.

## Notes, not failures

- **F3: persistence is left out of the section 7 summary without saying so.**
  - "rank 2 of 4 forecast sources", "rank 3 of 4" and "roughly 15 / 32 kg … for the core forecast sources" all exclude the persistence baseline. The recomputes match only with it excluded: the sensitivity would be 11.4 / 24.0 kg with it.
  - CONTEXT.md defines persistence as a forecast source, and the figure title and caption say "5-source" and "all five forecast sources".
  - The numbers are right; the sentence just doesn't say what it excludes. This is a wording item for the lead.
- **F4: "over-penalises"** (section 8 summary, both data sets). See *Words*; the lead should rule on it.
- **Rounding in the full section 7 summary:** "40 kg … 2 kg above GraphCast (39 kg)". The true gap is 1.54, which rounds to 2, but a reader subtracting the printed values gets 1. The fixture's "21 … 3 kg above … (18 kg)" is consistent.
- **Section 8's opt-in note** names `regret ensemble` after `regret neuralgcm`, but not the `fetch --with neuralgcm,neuralgcm_ens` step. That step appears only in section 7's note, just above it.
- **`fig-neuralgcm` row 1's y-axis extends below 0** (−45 kg on the fixture, −20 kg on the full data; auto-range padding), although regret is never negative. `fig-ensemble` starts at 0.
- **Grammar:** the section 7 summary's second clause, "at the longest lead (120 h) is 130 kg", drops its subject. It reads fine but is elliptical.
- **Full-config JupyterLab run:** not done through the UI; see step 3.

## End state

- **Baseline:** `sh qa/baseline/core-hashes.sh | diff - qa/baseline/core-hashes.txt` printed nothing (rc 0).
- **Notebooks:** `git status --porcelain -- notebooks/` printed nothing. The working tree shows only `?? qa/N2/` before the commit.
- **Servers:** stopped by the PIDs I started: 96525, 96516, 96524 and 96517, then 99247 and 99245. Afterwards:
  - `lsof` on 8765/8888 exits 1;
  - `ps` finds none of the PIDs;
  - `pgrep -fl 'ipykernel|jupyter-lab|http.server'` finds nothing.
- **Browser:** closed.
- **Clone:** pulled to `5bea60b` and its report regenerated (`reports/` is gitignored there too). Nothing else changed.

## Files

- `report.md` (this file).
- Screenshots:
  - `chrome.png`: fixture report, full page, 1,200 px;
  - `neuralgcm-1200.png` and `ensemble-1200.png`: fixture add-on figures, 1,200 px;
  - `neuralgcm-768.png` and `ensemble-768.png`: fixture add-on figures, 768 px;
  - `neuralgcm-full.png` and `ensemble-full.png`: full-data add-on figures, 1,200 px;
  - `notebook.png`: JupyterLab after Run All (fixture);
  - `clone-chrome.png`: the clone's report, full page, 1,200 px.
- Scratch (gitignored):
  - `sweep_n2.js`, `hover.js`, `hover2.js`, `recompute.py`, `gaps_kg.py` and `avoid.py`;
  - `sections-fixture.json`, `figs-fixture.json`, `pagetext-fixture.json`, `pagetext-full.json`, `clone-sections.json` and `recompute-full.txt`;
  - `report-fixture.log`, `report-full.log`, `report-clone.log` and `pytest-clone.log`;
  - `http.log`, `http-clone.log` and `jupyter.log`;
  - the PID files;
  - `regret_report.ipynb` (the run copy).
