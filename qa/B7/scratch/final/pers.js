async (page) => {
  await page.goto('http://127.0.0.1:8765/qa/B7/scratch/fig-final.html');
  await page.waitForSelector('#fig-showcase-map .legend .traces'); await page.waitForTimeout(1200);
  await page.mouse.move(2, 2); await page.waitForTimeout(300);
  const geom = await page.evaluate(() => {
    const gd = document.getElementById('fig-showcase-map');
    const tr = [...gd.querySelectorAll('.trace.scattergeo')].find(t => t.__data__[0].trace.index === 12);
    const path = tr.querySelector('path.js-line'); const L = path.getTotalLength(); const m = path.getScreenCTM(); const pts = [];
    for (let s = 1; s < 600; s++) { const a = path.getPointAtLength(L * s / 600), b = path.getPointAtLength(Math.min(L, L * s / 600 + 1));
      const ax = m.a * a.x + m.c * a.y + m.e, ay = m.b * a.x + m.d * a.y + m.f, bx = m.a * b.x + m.c * b.y + m.e, by = m.b * b.x + m.d * b.y + m.f;
      const len = Math.hypot(bx - ax, by - ay) || 1; pts.push([ax, ay, -(by - ay) / len, (bx - ax) / len]); }
    return { pts };
  });
  const A = (await page.screenshot({ scale: 'css' })).toString('base64');
  // background-only reference via real legend clicks on all five
  const clickLegend = async (name) => { const p = await page.evaluate((name) => { const it = [...document.querySelectorAll('#fig-showcase-map .legend .traces')].find(e => e.textContent.trim().startsWith(name)); const t = it.querySelector('.legendtoggle').getBoundingClientRect(); return [t.x + t.width / 2, t.y + t.height / 2]; }, name); await page.mouse.click(p[0], p[1]); await page.waitForTimeout(600); await page.mouse.move(2, 2); await page.waitForTimeout(300); };
  const names = ['Hindsight plan', 'IFS HRES', 'GraphCast', 'Pangu-Weather', 'Persistence baseline'];
  for (const n of names) await clickLegend(n);
  const B = (await page.screenshot({ scale: 'css' })).toString('base64');
  for (const n of names) await clickLegend(n);
  const pix = await page.evaluate(async ({ A, B, pts }) => {
    const load = (b64) => new Promise(ok => { const im = new Image(); im.onload = () => { const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0); ok({ w: im.width, d: x.getImageData(0, 0, im.width, im.height).data }); }; im.src = 'data:image/png;base64,' + b64; });
    const a = await load(A), b = await load(B);
    const px = (img, x, y) => { x = Math.round(x); y = Math.round(y); const o = (y * img.w + x) * 4; return [img.d[o], img.d[o + 1], img.d[o + 2]]; };
    const lin = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const Lm = c => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
    const CR = (c1, c2) => { const l1 = Lm(c1), l2 = Lm(c2); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
    const med = arr => { const s = [...arr].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
    // samples where the background under the line is a dark cell (grey < 170, i.e. >= ~60 m/s)
    const dark = []; const bgHist = { white: 0, light: 0, mid: 0, dark: 0 };
    for (const [x, y, nx, ny] of pts) { const bg = px(b, x, y)[0]; bgHist[bg >= 250 ? 'white' : bg >= 200 ? 'light' : bg >= 170 ? 'mid' : 'dark']++;
      if (bg < 170) { const line = px(a, x, y); const h1 = px(a, x + nx * 2.5, y + ny * 2.5), h2 = px(a, x - nx * 2.5, y - ny * 2.5); const out1 = px(a, x + nx * 4.5, y + ny * 4.5);
        dark.push({ bg, line: line[0], halo: Math.min(h1[0], h2[0]), outside: out1[0], onDash: line[0] < 200 }); } }
    const dd = dark.filter(r => r.onDash);
    return { n: pts.length, bgHist, darkN: dark.length, darkOnDash: dd.length, bgMed: med(dark.map(r => r.bg)), lineMed: med(dd.map(r => r.line)), haloMedOnDark: med(dark.map(r => r.halo)), outsideMed: med(dark.map(r => r.outside)),
      crLineVsHalo: dd.length ? +CR([med(dd.map(r => r.line))].concat([0,0]).map((v,i,arr)=>arr[0]), [med(dark.map(r => r.halo))].concat([0,0]).map((v,i,arr)=>arr[0])).toFixed(2) : null,
      crLineVsBg: dd.length ? +CR([1,1,1].map(() => med(dd.map(r => r.line))), [1,1,1].map(() => med(dark.map(r => r.bg)))).toFixed(2) : null,
      crHaloVsBg: +CR([1,1,1].map(() => med(dark.map(r => r.halo))), [1,1,1].map(() => med(dark.map(r => r.bg)))).toFixed(2),
      // halo-only probe points: in dash gaps over dark cells (line pixel white = halo shows on the centre)
      gapProbes: pts.filter(([x, y]) => { const bg = px(b, x, y)[0], l = px(a, x, y)[0]; return bg < 200 && l >= 245; }).map(([x, y]) => [x, y]).filter((_, i) => i % 2 === 0).slice(0, 12),
      edgeProbes: pts.filter(([x, y]) => px(b, x, y)[0] < 200).filter((_, i) => i % 5 === 0).slice(0, 12).map(([x, y, nx, ny]) => [x + nx * 2.5, y + ny * 2.5]) };
  }, { A, B, pts: geom.pts });
  // real mouse moves onto halo pixels; log plotly_hover curve numbers
  await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); window.__hov = []; gd.on('plotly_hover', e => window.__hov.push(e.points.map(p => p.curveNumber))); });
  const probes = [];
  for (const [x, y] of pix.gapProbes.concat(pix.edgeProbes)) {
    await page.mouse.move(2, 2); await page.waitForTimeout(120);
    const before = await page.evaluate(() => window.__hov.length);
    await page.mouse.move(x, y); await page.waitForTimeout(350);
    const ev = await page.evaluate((b) => window.__hov.slice(b), before);
    const txt = await page.evaluate(() => [...document.querySelectorAll('#fig-showcase-map .hoverlayer text')].map(e => e.textContent).join(' | ').slice(0, 90));
    probes.push({ at: [Math.round(x), Math.round(y)], curves: [...new Set(ev.flat())], txt });
  }
  await page.mouse.move(2, 2);
  // legend entry count at every lead + persistence legend click at 72 h hides line and halo
  const leads = {};
  for (const lead of [12, 24, 48, 72, 120]) {
    await page.locator('#fig-showcase-map .updatemenu-header').click(); await page.waitForTimeout(300);
    await page.locator('#fig-showcase-map .updatemenu-item-text', { hasText: new RegExp('^' + lead + ' h$') }).last().click(); await page.waitForTimeout(700);
    leads[lead] = await page.evaluate(() => [...document.querySelectorAll('#fig-showcase-map .legend .traces')].map(e => e.textContent.trim()));
  }
  return { pix: { ...pix, gapProbes: pix.gapProbes.length, edgeProbes: pix.edgeProbes.length }, probes, haloHit: probes.filter(p => p.curves.some(c => [5, 11, 17, 23, 29].includes(c))).length, leads: Object.fromEntries(Object.entries(leads).map(([k, v]) => [k, v.length + ': ' + v.join(' / ')])) };
}
