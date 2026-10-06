async (page) => {
  const Q = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/';
  await page.goto('http://127.0.0.1:8765/qa/B7/scratch/fig.html');
  await page.waitForSelector('#fig-showcase-map .legend .traces'); await page.waitForTimeout(1000);
  await page.mouse.move(2, 2); await page.waitForTimeout(300);
  // geometry: cells and plan samples, in viewport css px
  const geom = await page.evaluate(() => {
    const gd = document.getElementById('fig-showcase-map'); const g = gd._fullLayout.geo._subplot; const r = gd.getBoundingClientRect();
    const t = gd._fullData[0]; const z = t.marker.color;
    const cells = []; for (let i = 0; i < t.lon.length; i++) { const p = g.projection([t.lon[i], t.lat[i]]); cells.push({ i, lat: t.lat[i], lon: t.lon[i], z: z[i], x: p[0] + r.x, y: p[1] + r.y }); }
    const fills = [...gd.querySelectorAll('.trace.scattergeo')].find(tr => tr.__data__[0].trace.index === 0).querySelectorAll('path.point');
    const fillOf = [...fills].slice(0, 5).map(p => [p.style.fill, p.style.opacity]);
    const plans = {};
    for (const tr of gd.querySelectorAll('.trace.scattergeo')) { const ti = tr.__data__[0].trace.index; if (ti < 6 || ti > 10) continue;
      const path = tr.querySelector('path.js-line'); const L = path.getTotalLength(); const m = path.getScreenCTM(); const pts = [];
      const N = 200; for (let k = 1; k < N; k++) { const a = path.getPointAtLength(L * k / N), b = path.getPointAtLength(Math.min(L, L * k / N + 1));
        const ax = m.a * a.x + m.c * a.y + m.e, ay = m.b * a.x + m.d * a.y + m.f, bx = m.a * b.x + m.c * b.y + m.e, by = m.b * b.x + m.d * b.y + m.f;
        const len = Math.hypot(bx - ax, by - ay) || 1; pts.push([ax, ay, -(by - ay) / len, (bx - ax) / len]); }
      plans[ti] = { name: gd._fullData[ti].name, color: gd._fullData[ti].line.color, pts }; }
    return { cells, cmax: t.marker.cmax, cmin: t.marker.cmin, scale: t.marker.colorscale, op: t.marker.opacity, fillOf, plans,
      hind: gd._fullData[6].lon.map((lo, k) => [lo, gd._fullData[6].lat[k]]) };
  });
  const shotA = await page.screenshot({ scale: 'css' });
  await page.screenshot({ path: Q + 'reader-24h-attempt2.png', scale: 'device', clip: { x: 240, y: 110, width: 630, height: 490 } });
  // hide all five plans with real legend clicks, for a background-only image
  for (let k = 0; k < 5; k++) { const b = await page.evaluate((k) => { const t = document.querySelectorAll('#fig-showcase-map .legend .traces')[k].querySelector('.legendtoggle').getBoundingClientRect(); return [t.x + t.width / 2, t.y + t.height / 2]; }, k);
    await page.mouse.click(b[0], b[1]); await page.waitForTimeout(500); }
  await page.mouse.move(2, 2); await page.waitForTimeout(400);
  const shotB = await page.screenshot({ scale: 'css' });
  await page.screenshot({ path: Q + 'background-only-24h-attempt2.png', scale: 'device', clip: { x: 240, y: 110, width: 630, height: 490 } });
  const res = await page.evaluate(async ({ A, B, geom }) => {
    const load = (b64) => new Promise(ok => { const im = new Image(); im.onload = () => { const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0); ok({ w: im.width, d: x.getImageData(0, 0, im.width, im.height).data }); }; im.src = 'data:image/png;base64,' + b64; });
    const a = await load(A), b = await load(B);
    const px = (img, x, y) => { x = Math.round(x); y = Math.round(y); const o = (y * img.w + x) * 4; return [img.d[o], img.d[o + 1], img.d[o + 2]]; };
    const lin = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const L = c => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
    const CR = (c1, c2) => { const l1 = L(c1), l2 = L(c2); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
    const med = arr => { const s = [...arr].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
    const q = (arr, p) => { const s = [...arr].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
    // background colour of each cell from the background-only image (centre pixel)
    const cells = geom.cells.map(c => ({ ...c, rgb: px(b, c.x, c.y) }));
    const zs = cells.map(c => c.z); const z90 = q(zs, 0.9);
    const core = cells.filter(c => c.z >= z90), quiet = cells.filter(c => c.z < 20);
    // cells under the hindsight path: nearest cell to each band vertex
    const near = new Set(); for (const [lo, la] of geom.hind) { let best = null, bd = 1e9; for (const c of cells) { const d = (c.lon - lo) ** 2 + (c.lat - la) ** 2; if (d < bd) { bd = d; best = c; } } near.add(best.i); }
    const under = cells.filter(c => near.has(c.i));
    const gray = c => c.rgb[0];
    const summ = (set) => ({ n: set.length, zMed: +med(set.map(c => c.z)).toFixed(1), greyMed: med(set.map(gray)), greyMin: Math.min(...set.map(gray)), greyMax: Math.max(...set.map(gray)) });
    const white = [255, 255, 255];
    const coreVsQuiet = CR([med(core.map(gray)), med(core.map(gray)), med(core.map(gray))], [med(quiet.map(gray)), med(quiet.map(gray)), med(quiet.map(gray))]);
    const darkest = cells.reduce((m, c) => gray(c) < gray(m) ? c : m, cells[0]);
    // colour of the darkest possible cell: top of scale #b0b0b0 at opacity 0.8 over white / over land #eeeeee
    const top = [176, 176, 176]; const blend = (fg, bg, a) => fg.map((v, k) => Math.round(a * v + (1 - a) * bg[k]));
    const theo = { topOverWhite: blend(top, white, 0.8), topOverLand: blend(top, [238, 238, 238], 0.8) };
    theo.crTopWhite = +CR(theo.topOverWhite, white).toFixed(2);
    // attempt-1 Greys core rgb(15,15,15) at 0.8 over white
    const a1 = blend([15, 15, 15], white, 0.8); theo.attempt1Core = a1; theo.attempt1CrVsWhite = +CR(a1, white).toFixed(2);
    // plan lines: line pixel vs background pixel at the same point
    const plans = {};
    for (const [ti, p] of Object.entries(geom.plans)) {
      const off = (+ti === 6) ? 2.5 : 0; const crs = [], hits = []; let onDash = 0;
      for (const [x, y, nx, ny] of p.pts) {
        const xs = off ? [[x + nx * off, y + ny * off], [x - nx * off, y - ny * off]] : [[x, y]];
        let bestCr = 0; let used = null;
        for (const [sx, sy] of xs) { const fa = px(a, sx, sy), fb = px(b, sx, sy); const diff = Math.abs(fa[0] - fb[0]) + Math.abs(fa[1] - fb[1]) + Math.abs(fa[2] - fb[2]); if (diff > 30) { const cr = CR(fa, fb); if (cr > bestCr) { bestCr = cr; used = [fa, fb]; } } }
        if (used) { onDash++; crs.push(bestCr); hits.push(used); }
      }
      const sample = hits.length ? hits[Math.floor(hits.length / 2)] : null;
      plans[ti] = { name: p.name, nominal: p.color, samples: p.pts.length, drawnSamples: onDash, crMed: crs.length ? +med(crs).toFixed(2) : null, crMin: crs.length ? +Math.min(...crs).toFixed(2) : null, below3: crs.filter(c => c < 3).length, below15: crs.filter(c => c < 1.5).length, exampleLineVsBg: sample };
    }
    // a cross-section through the jet along 50W: z and grey for each lat
    const sec = cells.filter(c => Math.abs(c.lon - (-48.5)) < 1.3).sort((u, v) => v.lat - u.lat).map(c => [c.lat, c.z, gray(c)]);
    const sec2 = cells.filter(c => Math.abs(c.lon - (-28.5)) < 1.3).sort((u, v) => v.lat - u.lat).map(c => [c.lat, c.z, gray(c)]);
    return { z90: +z90.toFixed(1), zMax: Math.max(...zs), core: summ(core), quiet: summ(quiet), under: summ(under), coreVsQuiet: +coreVsQuiet.toFixed(2),
      underVsQuiet: +CR([med(under.map(gray))].concat([med(under.map(gray)), med(under.map(gray))]), [med(quiet.map(gray)), med(quiet.map(gray)), med(quiet.map(gray))]).toFixed(2),
      darkest: { z: darkest.z, rgb: darkest.rgb, lat: darkest.lat, lon: darkest.lon }, theo, plans, sec, sec2, lons: [...new Set(cells.map(c => c.lon))].slice(0, 30) };
  }, { A: shotA.toString('base64'), B: shotB.toString('base64'), geom });
  return { cmin: geom.cmin, cmax: geom.cmax, scale: geom.scale, op: geom.op, fillOf: geom.fillOf, ...res };
}
