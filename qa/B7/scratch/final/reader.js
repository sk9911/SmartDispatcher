async (page) => {
  const Q = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/';
  await page.goto('http://127.0.0.1:8765/qa/B7/scratch/fig-final.html');
  await page.waitForSelector('#fig-showcase-map .legend .traces'); await page.waitForTimeout(1200);
  await page.mouse.move(2, 2); await page.waitForTimeout(300);
  const IDX = { hind: 7, hres: 8, graphcast: 9, pangu: 10, halo: 11, pers: 12 };
  const geom = await page.evaluate((IDX) => {
    const gd = document.getElementById('fig-showcase-map'); const g = gd._fullLayout.geo._subplot; const r = gd.getBoundingClientRect();
    const t = gd._fullData[0]; const z = t.marker.color;
    const cells = []; for (let i = 0; i < t.lon.length; i++) { const p = g.projection([t.lon[i], t.lat[i]]); cells.push({ i, lat: t.lat[i], lon: t.lon[i], z: z[i], x: p[0] + r.x, y: p[1] + r.y }); }
    const trs = {}; for (const tr of gd.querySelectorAll('.trace.scattergeo')) { const d = tr.__data__ && tr.__data__[0] && tr.__data__[0].trace; if (d) trs[d.index] = tr; }
    const domOrder = [...gd.querySelectorAll('.trace.scattergeo')].map(tr => tr.__data__[0].trace.index);
    const lines = {};
    for (const [k, ti] of Object.entries(IDX)) { const tr = trs[ti]; const path = tr.querySelector('path.js-line'); const cs = getComputedStyle(path);
      const L = path.getTotalLength(); const m = path.getScreenCTM(); const pts = []; const N = 300;
      for (let s = 1; s < N; s++) { const a = path.getPointAtLength(L * s / N), b = path.getPointAtLength(Math.min(L, L * s / N + 1));
        const ax = m.a * a.x + m.c * a.y + m.e, ay = m.b * a.x + m.d * a.y + m.f, bx = m.a * b.x + m.c * b.y + m.e, by = m.b * b.x + m.d * b.y + m.f;
        const len = Math.hypot(bx - ax, by - ay) || 1; pts.push([ax, ay, -(by - ay) / len, (bx - ax) / len]); }
      const fd = gd._fullData[ti];
      const verts = fd.lon.map((lo, k) => { const p = g.projection([lo, fd.lat[k]]); return [lo, fd.lat[k], p[0] + r.x, p[1] + r.y]; });
      lines[k] = { ti, name: fd.name, stroke: cs.stroke, width: cs.strokeWidth, dash: cs.strokeDasharray, opacity: getComputedStyle(tr).opacity, hoverinfo: fd.hoverinfo, showlegend: fd.showlegend, legendgroup: fd.legendgroup, pts, verts }; }
    const geoRect = gd.querySelector('.geo .bglayer rect, .geolayer .bg rect').getBoundingClientRect();
    return { cells, cmax: t.marker.cmax, cmin: t.marker.cmin, scale: t.marker.colorscale, op: t.marker.opacity, domOrder, lines, dpr: window.devicePixelRatio, geoRect: [geoRect.x, geoRect.y, geoRect.width, geoRect.height] };
  }, IDX);
  const clip = { x: Math.max(0, geom.geoRect[0]), y: Math.max(0, geom.geoRect[1]), width: geom.geoRect[2], height: geom.geoRect[3] };
  const shot = async () => (await page.screenshot({ scale: 'css' })).toString('base64');
  const A = await shot();
  await page.screenshot({ path: Q + 'reader-24h-final.png', scale: 'device', clip });
  const legendPt = (name) => page.evaluate((name) => { const it = [...document.querySelectorAll('#fig-showcase-map .legend .traces')].find(e => e.textContent.trim().startsWith(name)); const t = it.querySelector('.legendtoggle').getBoundingClientRect(); return [t.x + t.width / 2, t.y + t.height / 2]; }, name);
  const clickLegend = async (name) => { const p = await legendPt(name); await page.mouse.click(p[0], p[1]); await page.waitForTimeout(600); await page.mouse.move(2, 2); await page.waitForTimeout(300); };
  // per-plan hide diffs (real legend clicks), each toggled back
  const single = {};
  for (const name of ['IFS HRES', 'GraphCast', 'Pangu-Weather', 'Persistence baseline']) {
    await clickLegend(name);
    single[name] = { shot: await shot(), vis: await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); return [7,8,9,10,11,12].map(i => i + ':' + gd._fullData[i].visible + ':' + !!([...gd.querySelectorAll('.trace.scattergeo')].find(tr => tr.__data__[0].trace.index === i))); }),
      legendOpacity: await page.evaluate((name) => { const it = [...document.querySelectorAll('#fig-showcase-map .legend .traces')].find(e => e.textContent.trim().startsWith(name)); return getComputedStyle(it).opacity; }, name) };
    await clickLegend(name);
  }
  // hide all five plans for the background-only view
  for (const name of ['Hindsight plan', 'IFS HRES', 'GraphCast', 'Pangu-Weather', 'Persistence baseline']) await clickLegend(name);
  const visAll = await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); return { vis: [7,8,9,10,11,12].map(i => i + ':' + gd._fullData[i].visible), drawn: [...gd.querySelectorAll('.trace.scattergeo')].map(tr => tr.__data__[0].trace.index) }; });
  const B = await shot();
  await page.screenshot({ path: Q + 'background-only-24h-final.png', scale: 'device', clip });
  // underlying land/sea colour at each cell centre: hide the background trace (measurement only, not a behaviour test)
  await page.evaluate(() => Plotly.restyle('fig-showcase-map', { visible: false }, [0]));
  await page.waitForTimeout(500);
  const C = await shot();
  await page.evaluate(() => Plotly.restyle('fig-showcase-map', { visible: true }, [0]));
  const singleShots = Object.fromEntries(Object.entries(single).map(([k, v]) => [k, v.shot]));
  const res = await page.evaluate(async ({ A, B, C, singleShots, geom }) => {
    const load = (b64) => new Promise(ok => { const im = new Image(); im.onload = () => { const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0); ok({ w: im.width, d: x.getImageData(0, 0, im.width, im.height).data }); }; im.src = 'data:image/png;base64,' + b64; });
    const a = await load(A), b = await load(B), c = await load(C); const S = {}; for (const [k, v] of Object.entries(singleShots)) S[k] = await load(v);
    const px = (img, x, y) => { x = Math.round(x); y = Math.round(y); const o = (y * img.w + x) * 4; return [img.d[o], img.d[o + 1], img.d[o + 2]]; };
    const lin = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const Lm = c => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
    const CR = (c1, c2) => { const l1 = Lm(c1), l2 = Lm(c2); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
    const med = arr => { const s = [...arr].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
    const gr = v => [v, v, v];
    const cells = geom.cells.map(cl => ({ ...cl, g: px(b, cl.x, cl.y)[0], under: px(c, cl.x, cl.y)[0] }));
    const cls = { quiet: cells.filter(x => x.z < 20), moderate: cells.filter(x => x.z >= 20 && x.z < 60), core: cells.filter(x => x.z >= 60) };
    const summ = (set) => ({ n: set.length, zMed: +med(set.map(x => x.z)).toFixed(1), greyMed: med(set.map(x => x.g)), greyMin: Math.min(...set.map(x => x.g)), greyMax: Math.max(...set.map(x => x.g)), land: set.filter(x => x.under < 250).length });
    const classes = Object.fromEntries(Object.entries(cls).map(([k, v]) => [k, summ(v)]));
    const sea = Object.fromEntries(Object.entries(cls).map(([k, v]) => [k, summ(v.filter(x => x.under >= 250))]));
    const ratios = (cs) => ({ coreQuiet: +CR(gr(cs.core.greyMed), gr(cs.quiet.greyMed)).toFixed(2), coreModerate: +CR(gr(cs.core.greyMed), gr(cs.moderate.greyMed)).toFixed(2), moderateQuiet: +CR(gr(cs.moderate.greyMed), gr(cs.quiet.greyMed)).toFixed(2) });
    // monotonicity: grey by 10 m/s bins
    const bins = []; for (let lo = 0; lo < 110; lo += 10) { const s = cells.filter(x => x.z >= lo && x.z < lo + 10 && x.under >= 250); if (s.length) bins.push([lo, s.length, med(s.map(x => x.g))]); }
    // cells under the hindsight path
    const nearest = (lo, la) => { let best = null, bd = 1e9; for (const cl of cells) { const d = (cl.lon - lo) ** 2 + (cl.lat - la) ** 2; if (d < bd) { bd = d; best = cl; } } return best; };
    const hindCells = [...new Set(geom.lines.hind.verts.map(v => nearest(v[0], v[1])))];
    // persistence over the core: line pixel (all shown) vs background-only pixel, at samples whose nearest cell is >= 60 m/s
    const persCore = []; const persAll = [];
    for (const [x, y, nx, ny] of geom.lines.pers.pts) {
      const fa = px(a, x, y), fb = px(b, x, y); const halo = [px(a, x + nx * 2.6, y + ny * 2.6), px(a, x - nx * 2.6, y - ny * 2.6)];
      const nc = cells.reduce((m, cl) => { const d = (cl.x - x) ** 2 + (cl.y - y) ** 2; return d < m[0] ? [d, cl] : m; }, [1e9, null])[1];
      const rec = { z: nc.z, line: fa[0], bg: fb[0], halo: halo.map(h => h[0]), crLineBg: CR(fa, fb), crLineHalo: Math.min(CR(fa, halo[0]), CR(fa, halo[1])) };
      persAll.push(rec); if (nc.z >= 60) persCore.push(rec);
    }
    const onDash = persCore.filter(r => r.line < 200);
    // per-plan visibility: pixels that change when only that plan is hidden, sampled along its own path
    const vis = {};
    const keyOf = { 'IFS HRES': 'hres', 'GraphCast': 'graphcast', 'Pangu-Weather': 'pangu', 'Persistence baseline': 'pers' };
    for (const [name, img] of Object.entries(S)) { const L = geom.lines[keyOf[name]]; let changed = 0; const coreN = [0, 0];
      for (const [x, y] of L.pts) { const p = px(a, x, y), q = px(img, x, y); const d = Math.abs(p[0] - q[0]) + Math.abs(p[1] - q[1]) + Math.abs(p[2] - q[2]);
        const nc = cells.reduce((m, cl) => { const dd = (cl.x - x) ** 2 + (cl.y - y) ** 2; return dd < m[0] ? [dd, cl] : m; }, [1e9, null])[1];
        if (d > 30) changed++; if (nc.z >= 60) { coreN[0]++; if (d > 30) coreN[1]++; } }
      vis[name] = { samples: L.pts.length, changed, pct: +(100 * changed / L.pts.length).toFixed(1), overCore: coreN }; }
    return { classes, sea, ratiosAll: ratios(classes), ratiosSea: ratios(sea), bins, hindCells: { n: hindCells.length, zMed: +med(hindCells.map(x => x.z)).toFixed(1), greyMed: med(hindCells.map(x => x.g)) },
      pers: { samples: persAll.length, overCore: persCore.length, overCoreOnDash: onDash.length, crLineBgMedCoreDash: onDash.length ? +med(onDash.map(r => r.crLineBg)).toFixed(2) : null, crLineHaloMedCoreDash: onDash.length ? +med(onDash.map(r => r.crLineHalo)).toFixed(2) : null, haloGreyMedCore: med(persCore.map(r => Math.max(...r.halo))), bgGreyMedCore: med(persCore.map(r => r.bg)), lineGreyMedCoreDash: med(onDash.map(r => r.line)) },
      vis };
  }, { A, B, C, singleShots, geom });
  const lineMeta = Object.fromEntries(Object.entries(geom.lines).map(([k, v]) => [k, { ti: v.ti, name: v.name, stroke: v.stroke, width: v.width, dash: v.dash, opacity: v.opacity, hoverinfo: v.hoverinfo, showlegend: v.showlegend, legendgroup: v.legendgroup }]));
  // data/pixel comparison of HRES vs Pangu-Weather (and other pairs)
  const V = Object.fromEntries(Object.entries(geom.lines).map(([k, v]) => [k, v.verts]));
  const cmp = (p, q) => { const P = V[p], Qv = V[q]; const key = v => v[0].toFixed(6) + ',' + v[1].toFixed(6); const setQ = new Set(Qv.map(key));
    let idxEq = 0, run = 0, best = 0; const n = Math.min(P.length, Qv.length);
    for (let k = 0; k < n; k++) { if (key(P[k]) === key(Qv[k])) { idxEq++; run++; best = Math.max(best, run); } else run = 0; }
    const shared = P.filter(v => setQ.has(key(v)));
    const pxd = P.map(v => Math.min(...Qv.map(w => Math.hypot(v[2] - w[2], v[3] - w[3]))));
    return { nP: P.length, nQ: Qv.length, sameIndexEqual: idxEq, longestRun: best, sharedWaypoints: shared.length, sharedLonRange: shared.length ? [Math.min(...shared.map(v => v[0])), Math.max(...shared.map(v => v[0]))].map(x => +x.toFixed(2)) : null,
      vertexPxDist: { medianPx: +[...pxd].sort((x, y) => x - y)[Math.floor(pxd.length / 2)].toFixed(2), within1px: pxd.filter(d => d < 1).length, within3px: pxd.filter(d => d < 3).length } }; };
  const pairs = { 'hres~pangu': cmp('hres', 'pangu'), 'graphcast~pangu': cmp('graphcast', 'pangu'), 'hres~graphcast': cmp('hres', 'graphcast'), 'hind~pangu': cmp('hind', 'pangu') };
  return { cmax: geom.cmax, scale: geom.scale, op: geom.op, dpr: geom.dpr, domOrder: geom.domOrder, lineMeta, single: Object.fromEntries(Object.entries(single).map(([k, v]) => [k, { vis: v.vis, legendOpacity: v.legendOpacity }])), visAll, pairs, ...res };
}
