async (page) => {
  const res = {};
  for (const id of ['fig-neuralgcm', 'fig-ensemble']) {
    await page.evaluate((id) => document.getElementById(id).scrollIntoView({block: 'center'}), id);
    await page.waitForTimeout(300);
    const pts = await page.evaluate((id) => {
      const gd = document.getElementById(id); const L = gd._fullLayout; const box = gd.getBoundingClientRect();
      const out = [];
      gd._fullData.forEach((t, ti) => {
        if (t.hoverinfo === 'skip' || t.mode !== 'lines+markers') return;
        const xa = L[t.xaxis.replace('x', 'xaxis')], ya = L[t.yaxis.replace('y', 'yaxis')];
        for (let i = 0; i < t.x.length; i++) out.push({ti, name: t.name, sub: t.xaxis, lead: t.x[i], y: t.y[i],
          px: box.left + xa._offset + xa.l2p(t.x[i]), py: box.top + ya._offset + ya.l2p(t.y[i])});
      });
      return out;
    }, id);
    // pixel gaps at each lead per subplot
    const gaps = {};
    for (const p of pts) { const k = p.sub + '@' + p.lead; (gaps[k] = gaps[k] || []).push(p); }
    const gapOut = {};
    for (const [k, arr] of Object.entries(gaps)) {
      const pairs = [];
      for (let i = 0; i < arr.length; i++) for (let j = i + 1; j < arr.length; j++) pairs.push({a: arr[i].name, b: arr[j].name, d: +Math.abs(arr[i].py - arr[j].py).toFixed(1)});
      pairs.sort((u, v) => u.d - v.d); gapOut[k] = pairs.slice(0, 3);
    }
    const hov = [];
    for (const p of pts) {
      await page.mouse.move(p.px, p.py);
      await page.waitForTimeout(150);
      const txt = await page.evaluate((id) => [...document.getElementById(id).querySelectorAll('.hoverlayer .hovertext')].map(e => e.textContent).join(' | '), id);
      hov.push({name: p.name, sub: p.sub, lead: p.lead, y: +p.y.toFixed(2), ok: txt.includes(p.name), txt});
      await page.mouse.move(5, 5); await page.waitForTimeout(60);
    }
    res[id] = {gaps: gapOut, unreachable: hov.filter(h => !h.ok), reached: hov.filter(h => h.ok).length, total: hov.length, sample: hov.slice(0, 2)};
  }
  return res;
}
