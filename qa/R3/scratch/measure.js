async (page) => {
  // R3: real-mouse x-unified hover at every (panel, lead) and every marker; geometry; CI pairing; gaps with CI overlap.
  const res = {};
  const readLabel = (id) => page.evaluate((id) => {
    const lg = document.querySelector('#' + id + ' .hoverlayer .legend');
    if (!lg) return null;
    const title = lg.querySelector('.legendtitletext');
    return { title: title ? title.textContent : null,
      items: [...lg.querySelectorAll('.legendtext')].map(e => e.getAttribute('data-unformatted') || e.textContent) };
  }, id);
  for (const id of ['fig-neuralgcm', 'fig-ensemble']) {
    await page.evaluate((id) => document.getElementById(id).scrollIntoView({ block: 'center' }), id);
    await page.waitForTimeout(400);
    const info = await page.evaluate((id) => {
      const gd = document.getElementById(id); const L = gd._fullLayout; const box = gd.getBoundingClientRect();
      const data = gd._fullData;
      const lines = [], checks = [];
      data.forEach((t, ti) => {
        if (t.mode !== 'lines+markers') return;
        const xa = L[t.xaxis.replace('x', 'xaxis')], ya = L[t.yaxis.replace('y', 'yaxis')];
        const cd = t.customdata || [];
        lines.push({ ti, name: t.name, sub: t.xaxis + t.yaxis, xa: t.xaxis, ya: t.yaxis, hovertemplate: t.hovertemplate,
          pts: t.x.map((x, i) => ({ lead: x, y: t.y[i], lo: cd[i] ? cd[i][0] : null, hi: cd[i] ? cd[i][1] : null,
            px: box.left + xa._offset + xa.l2p(x), py: box.top + ya._offset + ya.l2p(t.y[i]) })) });
        // CI pairing vs the band trace drawn just before (neuralgcm) or any band with same axes + colour
        const band = data.slice(0, ti).reverse().find(b => b.fill === 'toself' && b.xaxis === t.xaxis && b.yaxis === t.yaxis);
        if (band) {
          const n = t.x.length;
          const bx = band.x.slice(0, n), hi = band.y.slice(0, n), lo = band.y.slice(n).reverse();
          checks.push({ name: t.name, sub: t.xaxis, bandX_eq: JSON.stringify(bx) === JSON.stringify(t.x),
            cd_eq_band: cd.every((c, i) => Math.abs(c[0] - lo[i]) < 1e-6 && Math.abs(c[1] - hi[i]) < 1e-6),
            lo_le_y_le_hi: t.y.every((y, i) => cd[i][0] <= y + 1e-9 && y <= cd[i][1] + 1e-9),
            bandColour: band.fillcolor, lineColour: t.line.color, bandHoverSkip: band.hoverinfo === 'skip', bandInLegend: band.showlegend });
        } else checks.push({ name: t.name, sub: t.xaxis, band: 'none found' });
      });
      const axes = Object.keys(L).filter(k => /^[xy]axis\d*$/.test(k)).map(k => ({ k, type: L[k].type, len: +L[k]._length.toFixed(1),
        range: L[k].range.map(v => +(+v).toFixed(2)), rangemode: L[k].rangemode, domain: L[k].domain, tickvals: L[k].tickvals }));
      const bandsTraces = data.filter(t => t.fill === 'toself').length;
      return { lines, checks, axes, bandsTraces, hovermode: L.hovermode, height: L.height, width: L.width };
    }, id);
    // group by panel
    const panels = {};
    for (const l of info.lines) (panels[l.sub] = panels[l.sub] || []).push(l);
    const hoverPanelLead = [], hoverMarker = [];
    const re = /^(.+): (-?[\d.]+) \[(-?[\d.]+), (-?[\d.]+)\] kg$/;
    const judge = (lab, sub, lead) => {
      const exp = panels[sub].map(l => { const p = l.pts.find(q => q.lead === lead); return { name: l.name, y: p.y, lo: p.lo, hi: p.hi }; });
      if (!lab) return { ok: false, why: 'no label' };
      const parsed = lab.items.map(s => { const m = s.match(re); return m ? { name: m[1], y: +m[2], lo: +m[3], hi: +m[4] } : { bad: s }; });
      const bad = parsed.filter(p => p.bad);
      const names = parsed.map(p => p.name).sort().join('|'), expNames = exp.map(e => e.name).sort().join('|');
      const numsOk = exp.every(e => { const p = parsed.find(q => q.name === e.name); return p && Math.abs(p.y - e.y) <= 0.051 && Math.abs(p.lo - e.lo) <= 0.051 && Math.abs(p.hi - e.hi) <= 0.051; });
      const ok = bad.length === 0 && names === expNames && numsOk && String(lab.title) === String(lead);
      return { ok, title: lab.title, n: parsed.length, names, expNames, numsOk, bad: bad.map(b => b.bad), items: lab.items };
    };
    for (const [sub, ls] of Object.entries(panels)) {
      const ya = await page.evaluate(([id, yk]) => { const gd = document.getElementById(id); const L = gd._fullLayout; const a = L[yk.replace('y', 'yaxis')]; return gd.getBoundingClientRect().top + a._offset + a._length / 2; }, [id, ls[0].ya]);
      for (const p of ls[0].pts) {
        await page.mouse.move(5, 5); await page.waitForTimeout(60);
        await page.mouse.move(p.px, ya); await page.waitForTimeout(200);
        const lab = await readLabel(id);
        hoverPanelLead.push({ sub, lead: p.lead, ...judge(lab, sub, p.lead) });
      }
      for (const l of ls) for (const p of l.pts) {
        await page.mouse.move(5, 5); await page.waitForTimeout(60);
        await page.mouse.move(p.px, p.py); await page.waitForTimeout(200);
        const lab = await readLabel(id);
        const j = judge(lab, sub, p.lead);
        hoverMarker.push({ name: l.name, sub, lead: p.lead, ok: j.ok && j.names.includes(l.name), j: j.ok ? undefined : j });
      }
    }
    await page.mouse.move(5, 5);
    // gaps: every pair at each (panel, lead), px apart, kg apart, CI overlap
    const pairs = [];
    for (const [sub, ls] of Object.entries(panels)) {
      const leads = ls[0].pts.map(p => p.lead);
      for (const lead of leads) {
        const v = ls.map(l => ({ name: l.name, ...l.pts.find(p => p.lead === lead) }));
        for (let i = 0; i < v.length; i++) for (let j = i + 1; j < v.length; j++) {
          const a = v[i], b = v[j];
          pairs.push({ sub, lead, a: a.name, b: b.name, kg: +Math.abs(a.y - b.y).toFixed(2), px: +Math.abs(a.py - b.py).toFixed(1),
            ciOverlap: Math.max(a.lo, b.lo) <= Math.min(a.hi, b.hi) });
        }
      }
    }
    // scale: per y axis, px/kg, top vs largest hi and largest mean
    const scale = info.axes.filter(a => a.k.startsWith('y')).map(a => {
      const yk = a.k.replace('axis', '');
      const ls = info.lines.filter(l => l.ya === yk);
      const maxHi = Math.max(...ls.flatMap(l => l.pts.map(p => p.hi))), maxY = Math.max(...ls.flatMap(l => l.pts.map(p => p.y)));
      const minLo = Math.min(...ls.flatMap(l => l.pts.map(p => p.lo)));
      return { axis: a.k, type: a.type, rangemode: a.rangemode, len: a.len, range: a.range, pxPerKg: +(a.len / (a.range[1] - a.range[0])).toFixed(3),
        maxHi: +maxHi.toFixed(1), maxMean: +maxY.toFixed(1), minLo: +minLo.toFixed(1), clipped: maxHi > a.range[1] || minLo < a.range[0], headroomPct: +((a.range[1] - maxHi) / (a.range[1] - a.range[0]) * 100).toFixed(1) };
    });
    res[id] = { hovermode: info.hovermode, height: info.height, bandsTraces: info.bandsTraces, axes: info.axes, scale, checks: info.checks,
      hoverPanelLead: { total: hoverPanelLead.length, ok: hoverPanelLead.filter(h => h.ok).length, fails: hoverPanelLead.filter(h => !h.ok), sample: hoverPanelLead.slice(0, 2) },
      hoverMarker: { total: hoverMarker.length, ok: hoverMarker.filter(h => h.ok).length, fails: hoverMarker.filter(h => !h.ok) },
      closePairs: pairs.filter(p => p.px < 9).sort((u, v) => u.px - v.px),
      closeNoOverlap: pairs.filter(p => p.px < 9 && !p.ciOverlap), minPx: Math.min(...pairs.map(p => p.px)), nPairs: pairs.length,
      allPairs: pairs };
  }
  return res;
}
