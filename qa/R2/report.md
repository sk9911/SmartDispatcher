# R2 QA: re-check of the geostrophic section, and the final clean-clone suite

Date: 2026-10-02 · Branch `grilltest` · HEAD `cba07fc` (B14 = `ad263f6`). The working tree was clean at the start.

- **Browser:** `playwright` MCP (Chrome).
- **Servers:** neither was running at the start (both `curl` checks exited 7, and `lsof` found nothing on 8765 or 8888).
  - Steps (a) and (a′): I started both from the working tree's root with the *Shared runtime resources* commands:
    - static server: uv PID 46844, listener PID 46848;
    - JupyterLab: uv PID 46845, listener PID 46847.
    - No R2 step opens JupyterLab. I stopped it before step (b), so it was not running during the timed suite.
  - Step (b): I served **the T32 clone's root** on 8765 (uv PID 47122, listener PID 47125).
- **Overlap sweep method:** I used S4's `sweep_run.js` with one change (`scratch/sweep_r2.js`):
  - Legend items are now compared with each other too. S4's script grouped them and skipped those pairs, which the *Standard checks* rule doesn't allow.
  - The same script also records *Fits container* (the widest `.main-svg` against `.jp-OutputArea-output` `clientWidth`).
  - **Positive control:** I moved `fig-geostrophic`'s legend onto the x-axis title (`Plotly.relayout`, `legend.y: -0.08`). The method then reported 3 hits (the legend and two items), so the 0 counts below mean something. I reloaded the page afterwards.
- **Plotly interactions:** hovers used a real `page.mouse.move` via `browser_run_code_unsafe`, after `scrollIntoView` (*Plotly interactions* rule).

## Verdict: PASS on every step

| # | Step | Result |
|---|---|---|
| a1 | Regenerate the fixture report | **PASS**: rc 0 (5.3 s) |
| a2 | SBC on `fig-geostrophic` (and the other 5) | **PASS**: 3 `.main-svg` each; 1 console error, the allowed `/favicon.ico` 404; network shows only the page; `chrome.png` |
| a3 | Caption matches the figure | **PASS**: 1 point at or above ERA5 (IFS HRES 24 h); largest gap 0.0147, printed as "0.015" |
| a4 | Static markdown has no numbers; summary shown only with the figure, not on stderr | **PASS** |
| a5 | Reader view: sources and ERA5 distinguishable (px gaps) | **PASS**, with one measured near-tie (see the notes) |
| a6 | Real hover at each lead shows all 4 names | **PASS** at all 5 leads |
| a7 | "does not start at 0" label visible, not clipped | **PASS** |
| a8 | *Fits container* and overlap sweep on `fig-geostrophic`, 1,200 and 768 px | **PASS**: 1134/1154 and 702/722; 0 hits |
| a′1 | Regenerate the full report (working tree) | **PASS**: rc 0 (5.4 s) |
| a′2 | 6 figures; summary says all lower and matches the figure data | **PASS**: 0 points above ERA5, gap 0.0244, printed as "0.024" |
| a′3 | *Fits container*, all 6 figures at 1,200 px | **PASS**; overlap sweep 0 hits too |
| b1 | Clone pulled to HEAD; no `geostrophic.parquet` | **PASS**: `b001d0a` → `cba07fc`; file absent |
| b2 | `regret report` in the clone exits 0 | **PASS**: rc 0 (5.5 s) |
| b3 | Section 6: definition, opt-in note, "Not done" line; no geostrophic numbers; 5 figures; 0 stderr | **PASS** |
| b4 | `time REGRET_BLOCK_NETWORK=1 uv run pytest` < 180 s at the final HEAD | **PASS**: **303 passed, 1 skipped, in 63.0 s** wall clock (pytest: 61.83 s) |
| c | End state | **PASS**: `notebooks/` clean; servers stopped by PID; browser closed |

No failures to report.

## Step (a): fixture report (`reports/report-fixture.html`)

- `REGRET_BLOCK_NETWORK=1 REGRET_CONFIG=fixture uv run regret report` exited 0. Its only output was the usual ipykernel TCP warning.
- **Correction to qa/S4:** `reports/` is gitignored (`.gitignore:3`), so a clean `git status` after regeneration says nothing about whether the file changed. S4's "byte-identical to HEAD" claim had no basis; it doesn't affect any S4 result.

### SBC (1,200 × 900)

- `document.title` is "Forecast Regret".
- 6 figures, each with 3 `.main-svg`: `fig-headline`, `fig-showcase-map`, `fig-lead-regret`, `fig-wind-error`, `fig-sanity` and `fig-geostrophic`.
- **Console:** 1 error, the allowed `/favicon.ico` 404.
- **Network:** only `GET /reports/report-fixture.html → 200`.
- 0 `stderr` outputs. No horizontal page scroll (`scrollWidth` 1200).
- Screenshot: `chrome.png` (full page).

### Caption vs figure

- **Section 6's static markdown** has exactly two paragraphs: the definition ("Is a forecast's wind … averaged over the experiment's flights.") and the "Not done: the NeuralGCM source and the ensemble robust plan …" line.
  - It contains no geostrophic numbers. The only digits are 250 hPa, 30–70°N, the dates 2020-01-01 and 2019-12-27, and "12-hourly"/"6-hourly".
- **Section 6's outputs**, in order:
  1. the figure (`text/html`, top at y = 6085);
  2. the summary, a `text/markdown` output 1,154 × 29 px, visible, opacity 1, directly under the figure (y = 6612).
  - The section has no `stderr` output.
- **Summary text, verbatim:**

  > ERA5's ageostrophic fraction is about 0.21. The largest gap between any forecast source and ERA5 is 0.015. IFS HRES at 24 h sits just above ERA5.

- **Figure data**, read from `gd._fullData` in the page (not the parquet):

  | lead (h) | ERA5 (reference) | IFS HRES | GraphCast | Pangu-Weather |
  |---|---|---|---|---|
  | 12 | 0.21292 | 0.21003 | 0.20314 | 0.20326 |
  | 24 | 0.21292 | **0.21371** | 0.20345 | 0.19918 |
  | 48 | 0.21292 | 0.21142 | 0.20065 | 0.20010 |
  | 72 | 0.21292 | 0.21221 | 0.20114 | 0.19942 |
  | 120 | 0.21292 | 0.20641 | 0.19908 | **0.19826** |

  - ERA5 is flat at 0.21292. "About 0.21" is ✔.
  - Exactly one forecast point is at or above ERA5: IFS HRES at 24 h, +0.00079. "IFS HRES at 24 h sits just above ERA5" is ✔.
  - The largest absolute gap is Pangu-Weather at 120 h, 0.21292 − 0.19826 = 0.01466. "0.015" is ✔.
  - The figure data match `tests/fixture_results/geostrophic.parquet` to 6 decimal places.

### Reader view: separation in px

- **Axis:**
  - `yaxis.type` is `linear`, range [0.1955, 0.2165]. All 20 points are inside it, ERA5 included.
  - The title is "ageostrophic fraction (axis does not start at 0)".
  - Ticks are 0.2, 0.205, 0.21 and 0.215.
- **Scale:**
  - The figure height is a fixed 520 px and the plot area is 320 px, so the vertical scale doesn't depend on page width.
  - The scale is **15,238 px per unit**, against 1,396 in S4 (about 11×).
  - The four lines now span **149–223 px** per lead, against a 21.6 px band in total in S4.
- **Gaps:** `|yaxis.l2p(a) − yaxis.l2p(b)|` for all 6 pairs at each lead. I fixed the threshold before measuring: the marker size, 9 px.

  | lead (h) | smallest pair (px) | 2nd smallest (px) | ERA5 − IFS HRES (px) | GraphCast vs Pangu-Weather (px) |
  |---|---|---|---|---|
  | 12 | GraphCast–Pangu-Weather **1.8** | IFS HRES–ERA5 44.1 | 44.1 | **1.8** |
  | 24 | IFS HRES–ERA5 12.1 | GraphCast–Pangu-Weather 65.0 | 12.1 (IFS HRES above) | 65.0 |
  | 48 | GraphCast–Pangu-Weather **8.4** | IFS HRES–ERA5 22.8 | 22.8 | **8.4** |
  | 72 | IFS HRES–ERA5 10.8 | GraphCast–Pangu-Weather 26.2 | 10.8 | 26.2 |
  | 120 | GraphCast–Pangu-Weather 12.5 | IFS HRES–ERA5 99.1 | 99.1 | 12.5 |

  - All other pairs are ≥ 99 px.
  - **Every IFS HRES–ERA5 gap is now ≥ 10.8 px.** In S4 they were 1.0–9.1 px.
  - **Two gaps are below the 9 px marker size:** GraphCast vs Pangu-Weather at 12 h (1.8 px) and at 48 h (8.4 px).
    - At 12 h the values are 0.20314 vs 0.20326, a difference of 0.00012. That is a near-tie in the data, which the lead's decision recorded as "near-ties are the data, so no jitter".
    - At 48 h the diamond and the square overlap partly but both stay visible (`geostrophic-768.png`).
    - Both points can be reached by hover at both leads (next section). I recorded this as a measured note, not a failure.
- **Screenshots:**
  - `geostrophic-hover-12h.png` (1,200 px, the unified hover at 12 h);
  - `geostrophic-768.png` (768 px, with the summary under the figure).

  The four lines read as four, and ERA5's dashed line is clear of IFS HRES except where IFS HRES crosses it at 24 h.

### Hover

- `_fullLayout.hovermode` is `"x unified"`. The hover template is `"%{fullData.name}: %{y:.3f}"` on all 4 traces.
- I scrolled the figure into view, then moved a real mouse to x = `left + margin.l + xaxis.l2p(lead)`, y = the middle of the plot. I read `.hoverlayer text` after 250 ms.

  | lead | mouse (x, y) | hover text |
  |---|---|---|
  | 12 | (151, 420) | 12 · IFS HRES: 0.210 · GraphCast: 0.203 · Pangu-Weather: 0.203 · ERA5 (reference): 0.213 |
  | 24 | (254, 420) | 24 · IFS HRES: 0.214 · GraphCast: 0.203 · Pangu-Weather: 0.199 · ERA5 (reference): 0.213 |
  | 48 | (459, 420) | 48 · IFS HRES: 0.211 · GraphCast: 0.201 · Pangu-Weather: 0.200 · ERA5 (reference): 0.213 |
  | 72 | (665, 420) | 72 · IFS HRES: 0.212 · GraphCast: 0.201 · Pangu-Weather: 0.199 · ERA5 (reference): 0.213 |
  | 120 | (1076, 420) | 120 · IFS HRES: 0.206 · GraphCast: 0.199 · Pangu-Weather: 0.198 · ERA5 (reference): 0.213 |

- All 4 names appear at all 5 leads, so all 20 points can be reached. In S4, GraphCast at 12 h and 48 h could not be reached.

### "does not start at 0" label

- `text.ytitle` reads, complete, "ageostrophic fraction (axis does not start at 0)".
- Its rect (x 26.7–43.7, height 329.3 px) lies inside the `.main-svg` rect (x 23–1157, height 520), so it isn't clipped.
- It is visible in every screenshot.

### Fits container and overlap sweep (fresh load at each width)

| Figure | 1,200 px: svg / client / scroll | hits | 768 px: svg / client / scroll | hits |
|---|---|---|---|---|
| fig-geostrophic | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-headline | 1067 / 1154 / 1154 ✔ | 0 | 1067 / 722 / 1087 (the accepted B13 case) | 0 |
| fig-showcase-map | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-lead-regret | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-wind-error | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |
| fig-sanity | 1134 / 1154 / 1154 ✔ | 0 | 702 / 722 / 722 ✔ | 0 |

- `fig-geostrophic` swept 3 titles (the figure title, `xtitle` and `ytitle`), the legend and its 4 items (compared pairwise), and 9 tick labels (5 x, 4 y).
- At 768 px the legend stays on one line (`geostrophic-768.png`).
- The page has no horizontal scroll at either width.

## Step (a′): full report (working tree)

- **Before:** `data/results/geostrophic.parquet` exists (3,139 bytes, from S2), and `reports/` is untracked (gitignored).
- `REGRET_BLOCK_NETWORK=1 uv run regret report` exited 0 (5.4 s). `reports/report.html` is now 5,970,413 bytes.
  - `git status` afterwards showed only `?? qa/R2/`. The regenerated report is gitignored, so there is nothing to commit.
- **Checks at 1,200 px:**
  - **6 figures**, each with 3 `.main-svg`.
  - **0** console errors.
  - Network: only `GET /reports/report.html → 200`.
  - 0 `stderr`. `hovermode` is `x unified`.
- **Summary, verbatim:**

  > ERA5's ageostrophic fraction is about 0.21. The largest gap between any forecast source and ERA5 is 0.024; all forecast sources are slightly more balanced (lower) than ERA5. Smoother fields are a possible explanation, not a finding; the sample is small and nothing here was tested for it.

- **Figure data:**

  | lead (h) | ERA5 | IFS HRES | GraphCast | Pangu-Weather | smallest gap (px) |
  |---|---|---|---|---|---|
  | 12 | 0.2107 | 0.2090 | 0.2011 | 0.2014 | 2.5 (GraphCast–Pangu-Weather) |
  | 24 | 0.2107 | 0.2089 | 0.1982 | 0.1940 | 16.8 |
  | 48 | 0.2107 | 0.2065 | 0.1938 | 0.1930 | 7.4 |
  | 72 | 0.2107 | 0.2051 | 0.1901 | 0.1911 | 9.7 |
  | 120 | 0.2107 | 0.2092 | 0.1863 | 0.1905 | 13.9 |

  - ERA5 is flat (one distinct value), so its per-lead value and its mean agree.
  - **0** forecast points are at or above ERA5, checked both per lead and against the mean. "All forecast sources … lower" is ✔.
  - The largest gap is GraphCast at 120 h, 0.0244, printed as "0.024" ✔. It matches S4's full-results value.
  - The y range is [0.1819, 0.215].
- ***Fits container* at 1,200 px:** all 6 pass:
  - `fig-headline` 1067/1154;
  - the other 5 figures 1134/1154;
  - scroll = client in every case.

  The overlap sweep found 0 hits in all 6.
- Screenshot: `geostrophic-full.png`.

## Step (b): clean clone

- **Clone:** `/var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret`.
  - Before the pull it was at `b001d0a` on `grilltest`, tracking `origin/grilltest` (origin is the working tree). `status --porcelain` showed only `?? qa_scratch/`, from T32.
  - `git pull` fast-forwarded it to **`cba07fc`**, the same as the working tree's HEAD.
  - `data/results/` holds only `regret.parquet`. `test -e data/results/geostrophic.parquet` exits 1.
- **Report:** `REGRET_BLOCK_NETWORK=1 uv run regret report` exited 0 (5.5 s). `reports/report.html` is 5,961,193 bytes.
  - I stopped the working-tree servers, then served the clone's root.
  - `curl` through 8765 returned the same 5,961,193 bytes, which confirms the server was serving the clone.
- **Page checks (1,200 px):**
  - **5 figures** (headline, showcase map, lead regret, wind error and sanity), each with 3 `.main-svg`.
  - `#fig-geostrophic` is absent, and the string doesn't appear anywhere in the HTML.
  - **0** `stderr` and 0 `error` outputs. **0** console errors. Network: only the page.
- **Section 6 text**, from the "6." heading to the "7." heading, scripts excluded:
  - the definition paragraph;
  - the "Not done: the NeuralGCM source and the ensemble robust plan …" line;
  - the opt-in note (`text/markdown`, 1,154 × 52 px, visible), with `<code>` for `uv run regret fetch --with geopotential` and `uv run regret geostrophic`.
- **No numbers:**
  - "0.2" occurs **0** times and "0.0" **0** times.
  - The pattern `\d\.\d+` matches nothing in the section.
  - The summary sentence is absent.
- Screenshot: `clone-section6.png`.
- **Suite:** `time REGRET_BLOCK_NETWORK=1 uv run pytest` in the clone at `cba07fc`, run after `regret report` (so `uv` had already synced), with JupyterLab stopped (only the idle clone static server on 8765 was running):
  - **303 passed, 1 skipped, 332 warnings in 61.83 s**;
  - `time`: **63.03 s total** (65.45 s user, 17.33 s system). The limit is 180 s.
  - The skip is `tests/test_geostrophic.py:140: no real results`. That test checks the full geostrophic results, which a clean clone lacks by design (S2's opt-in decision). I confirmed it with `-rs` on that file.
  - T32 ran 291 tests; the suite now collects 304. The 13 new tests were added after T32 (S2, S3 and B14 added tests; I didn't attribute them one by one).
  - This commit touches only `qa/R2/`, so `cba07fc`'s code is the final code HEAD.
  - The clone's `git status --porcelain` stayed at `?? qa_scratch/`.

## Notes, not failures

- **GraphCast vs Pangu-Weather at 12 h** are 1.8 px apart on the fixture and 2.5 px on the full results, below the 9 px marker size.
  - These are near-ties in the data (0.00012 apart on the fixture, about 0.0003 on the full results). The lead's decision rules out jitter for them.
  - The unified hover lists both, so neither point is hidden.
  - The fixture at 48 h (8.4 px) and the full results at 48 h (7.4 px) are also just under the marker size, but different symbols keep both visible.
- **Unified hover header:** the header shows the lead as a bare number ("12", "120"), without "h". The x-axis title says "lead time (h)", so the meaning is recoverable. This is a possible polish item.
- **Summary wording when a source sits above ERA5** (the fixture case): the sentence names the point above ERA5 but not that the rest are lower. It also drops the "possible explanation, not a finding" sentence. That sentence explains forecasts being lower, so dropping it is consistent; I mention it only so the lead knows the fixture caption is shorter.
- **The fixture regeneration** can't be compared byte-for-byte through git, because `reports/` is gitignored (see the correction under step (a)).

## End state

- **Notebooks:** `git status --porcelain -- notebooks/` printed nothing. The working tree shows only `?? qa/R2/` before the commit.
- **Servers:** stopped by the PIDs I started: 46848, 46844, 46847 and 46845, then 47125 and 47122. Afterwards:
  - `lsof` on 8765/8888 exits 1;
  - both `curl` checks exit 7;
  - `ps` finds none of the PIDs;
  - `pgrep -fl 'ipykernel|jupyter|http.server'` finds nothing.
- **Browser:** closed.
- **Clone:** pulled to `cba07fc` and its report regenerated (`reports/` is gitignored there too). Nothing else changed.

## Files

- `report.md` (this file).
- Screenshots:
  - `chrome.png`: fixture report, full page, 1,200 px;
  - `geostrophic-hover-12h.png`: fixture `fig-geostrophic` with the unified hover at 12 h;
  - `geostrophic-768.png`: fixture `fig-geostrophic` and summary at 768 px;
  - `geostrophic-full.png`: the full report's `fig-geostrophic` and summary, 1,200 px;
  - `clone-section6.png`: the clone's section 6 with the opt-in note.
- Scratch (gitignored):
  - `sweep_r2.js` (and S4's scripts);
  - `report-fixture.log`, `report-full.log`, `report-clone.log` and `pytest-clone.log`;
  - `http.log`, `http-clone.log` and `jupyter.log`;
  - the PID files.
