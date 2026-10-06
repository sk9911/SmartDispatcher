async (page) => {
  const Q = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/';
  await page.goto('http://127.0.0.1:8765/qa/B7/scratch/fig.html');
  await page.waitForSelector('#fig-showcase-map .legend .traces'); await page.waitForTimeout(800);
  await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map'); window.__hov = []; gd.on('plotly_hover', e => window.__hov.push(e.points.map(p => p.curveNumber))); });
  const state = () => page.evaluate(() => { const gd = document.getElementById('fig-showcase-map');
    const c = gd._fullData[0].marker.color; let s = 0; for (let k = 0; k < c.length; k++) s += c[k];
    return { cbtitle: gd.querySelector('.cbtitle').textContent, active: gd.layout.sliders[0].active,
      current: gd.querySelector('.slider-group > text.slider-label').textContent,
      grip: Math.round(gd.querySelector('.slider-grip-rect').getBoundingClientRect().x),
      bgSum: Math.round(s * 10) / 10, bgHoverTpl: gd.data[0].hovertemplate,
      header: gd.querySelector('.updatemenu-header text').textContent,
      visiblePlans: gd.data.map((t, i) => [i, t.visible, t.name, t.meta && t.meta.lead_h]).filter(x => x[1] === true).map(x => x[0] + ':' + x[2] + '@' + x[3]) }; });
  const clickStep = async (i) => {
    const pt = await page.evaluate((i) => { const gd = document.getElementById('fig-showcase-map');
      const lab = gd.querySelectorAll('.slider-label-group text')[i].getBoundingClientRect();
      const rail = gd.querySelector('.slider-rail-rect').getBoundingClientRect();
      return [lab.x + lab.width / 2, rail.y + rail.height / 2]; }, i);
    await page.mouse.click(pt[0], pt[1]); await page.waitForTimeout(700); return pt; };
  const pickLead = async (lead) => {
    await page.locator('#fig-showcase-map .updatemenu-header').click(); await page.waitForTimeout(300);
    await page.locator('#fig-showcase-map .updatemenu-item-text', { hasText: new RegExp('^' + lead + ' h$') }).last().click(); await page.waitForTimeout(800); };
  const hoverBg = async () => {
    const pt = await page.evaluate(() => { const gd = document.getElementById('fig-showcase-map');
      const pts = [...gd.querySelectorAll('.geolayer .trace.scattergeo, .layer.frontplot .trace.scattergeo, .trace.scattergeo')].filter(t => t.__data__ && t.__data__[0].trace.index === 0)[0].querySelectorAll('.point');
      const geo = gd.querySelector('.geo .bglayer rect, .geolayer .bg rect') ; 
      let best = null; for (const p of pts) { const r = p.getBoundingClientRect(); const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
        if (r.width === 0) continue; if (!best || cy > best[1] + 0.1 || (Math.abs(cy - best[1]) < 0.1 && Math.abs(cx - 600) < Math.abs(best[0] - 600))) best = [cx, cy]; }
      return best; });
    await page.mouse.move(10, 10); await page.waitForTimeout(200);
    await page.mouse.move(pt[0], pt[1]); await page.waitForTimeout(500);
    const t = await page.evaluate(() => [...document.querySelectorAll('#fig-showcase-map .hoverlayer text')].map(e => e.textContent).join(' | '));
    const curve = await page.evaluate(() => window.__hov[window.__hov.length - 1]);
    await page.mouse.move(10, 10); await page.waitForTimeout(200);
    return { pt: pt.map(Math.round), text: t, curve }; };
  const out = {};
  out.s0_initial = await state();
  const era5Sum = out.s0_initial.bgSum;
  out.click1 = await clickStep(2);
  out.s1_graphcast24 = await state();
  await page.screenshot({ path: Q + 'desync-1-graphcast-24h.png' });
  await pickLead(72);
  out.s2_after72 = await state();
  out.s2_bgHover = await hoverBg();
  await page.screenshot({ path: Q + 'desync-2-after-72h-button.png' });
  out.click2 = await clickStep(2);
  out.s3_step2_72 = await state();
  out.s3_bgHover = await hoverBg();
  await page.screenshot({ path: Q + 'desync-3-graphcast-72h.png' });
  out.era5Sum = era5Sum;
  out.verdict = { era5Restored: out.s2_after72.bgSum === era5Sum && out.s2_after72.active === 0 && /ERA5/.test(out.s2_after72.cbtitle) && /ERA5/.test(out.s2_after72.current),
    step2: /GraphCast/.test(out.s3_step2_72.cbtitle) && /lead 72 h/.test(out.s3_step2_72.cbtitle) && out.s3_step2_72.bgSum !== era5Sum && out.s3_step2_72.bgSum !== out.s1_graphcast24.bgSum };
  return out;
}
