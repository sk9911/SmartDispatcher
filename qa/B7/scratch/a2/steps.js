async (page) => {
  const Q = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/';
  await page.goto('http://127.0.0.1:8765/qa/B7/scratch/fig.html');
  await page.waitForSelector('#fig-showcase-map .legend .traces'); await page.waitForTimeout(800);
  await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); window.__hov = []; gd.on('plotly_hover', e => window.__hov.push(e.points.map(p => p.curveNumber))); });
  const pickLead = async (lead) => {
    await page.locator('#fig-showcase-map .updatemenu-header').click(); await page.waitForTimeout(300);
    await page.locator('#fig-showcase-map .updatemenu-item-text', { hasText: new RegExp('^' + lead + ' h$') }).last().click(); await page.waitForTimeout(800); };
  const legend = () => page.evaluate(() => [...document.querySelectorAll('#fig-showcase-map .legend .traces')].map(t => ({ text: t.textContent, op: t.style.opacity || getComputedStyle(t).opacity, idx: t.__data__[0].trace.index })));
  const vertexPts = (ti, idxs) => page.evaluate(([ti, idxs]) => { const gd = document.getElementById('fig-showcase-map'); const g = gd._fullLayout.geo._subplot; const r = gd.getBoundingClientRect();
      const t = gd._fullData[ti]; return idxs.filter(i => i < t.lon.length).map(i => { const p = g.projection([t.lon[i], t.lat[i]]); return { i, x: p[0] + r.x, y: p[1] + r.y }; }); }, [ti, idxs]);
  const probe = async (x, y) => {
    await page.mouse.move(5, 5); await page.waitForTimeout(150);
    const before = await page.evaluate(() => window.__hov.length);
    await page.mouse.move(x, y); await page.waitForTimeout(350);
    return page.evaluate((b) => ({ curve: window.__hov.length > b ? window.__hov[window.__hov.length - 1] : null, text: [...document.querySelectorAll('#fig-showcase-map .hoverlayer text')].map(e => e.textContent).join(' | ') }), before); };
  const out = {};
  // step 4: legend at every lead
  out.legend = {};
  for (const lead of [12, 24, 48, 72, 120]) { await pickLead(lead); out.legend[lead] = await legend(); }
  // step 5: hover probes at 24 h
  await pickLead(24);
  out.n = await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); return gd._fullData.slice(6, 11).map((t, k) => [6 + k, t.name, t.lon.length, t.line.width, t.opacity, t.line.dash, t.line.color]); });
  out.bandEnds = await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); const b = gd._fullData[6], p = gd._fullData[9]; return { bandFirst: [b.lon[0], b.lat[0]], bandLast: [b.lon[b.lon.length - 1], b.lat[b.lat.length - 1]], panguFirst: [p.lon[0], p.lat[0]], panguLast: [p.lon[p.lon.length - 1], p.lat[p.lat.length - 1]] }; });
  out.order = await page.evaluate(() => [...document.querySelectorAll('#fig-showcase-map .trace.scattergeo')].map(t => t.__data__[0].trace.index).filter(i => i >= 6 && i <= 10));
  out.probes = {};
  for (const ti of [7, 8, 9, 10]) {
    const n = await page.evaluate((ti) => document.getElementById('fig-showcase-map')._fullData[ti].lon.length, ti);
    let idxs = []; for (let k = 1; k <= 10; k++) idxs.push(Math.round(k * (n - 1) / 11));
    if (ti === 9) { const m5 = []; for (let k = 1; k <= 8; k++) m5.push(5 * Math.round(k * (n - 1) / 45)); idxs = idxs.concat(m5); }
    const pts = await vertexPts(ti, idxs); const res = [];
    for (const p of pts) { const r = await probe(p.x, p.y); res.push({ i: p.i, curve: r.curve, text: r.text }); }
    out.probes[ti] = res;
  }
  await page.mouse.move(5, 5);
  // step 3a: real hover on every plan at 72 h
  await pickLead(72);
  out.hover72 = {};
  for (const ti of [17, 18, 19, 20, 16]) { const n = await page.evaluate((ti) => document.getElementById('fig-showcase-map')._fullData[ti].lon.length, ti);
    const pts = await vertexPts(ti, [Math.round(n * 0.3), Math.round(n * 0.5)]); out.hover72[ti] = [];
    for (const p of pts) out.hover72[ti].push(await probe(p.x, p.y)); }
  await page.mouse.move(5, 5); await page.waitForTimeout(200);
  // step 7: legend click at 72 h on Persistence baseline (real mouse click on its legendtoggle)
  const box = await page.evaluate(() => { const t = [...document.querySelectorAll('#fig-showcase-map .legend .traces')].find(t => t.textContent === 'Persistence baseline'); const r = t.querySelector('.legendtoggle').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
  await page.mouse.click(box[0], box[1]); await page.waitForTimeout(700);
  out.legendClick72 = { legend: await legend(), vis: await page.evaluate(() => document.getElementById('fig-showcase-map').data.map((t, i) => [i, t.visible]).filter(x => x[0] % 5 === 0 && x[0] > 0)) ,
    persistenceDrawn: await page.evaluate(() => [...document.querySelectorAll('#fig-showcase-map .trace.scattergeo')].filter(t => t.__data__[0].trace.index === 20).map(t => t.querySelectorAll('path.js-line').length)) };
  await page.screenshot({ path: Q + 'legend-click-72h-attempt2.png' });
  await pickLead(120);
  out.after120 = { legend: await legend(), vis: await page.evaluate(() => document.getElementById('fig-showcase-map').data.map((t, i) => [i, t.visible]).filter(x => x[0] % 5 === 0 && x[0] > 0)) };
  return out;
}
