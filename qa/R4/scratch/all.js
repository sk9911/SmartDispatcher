async (page) => {
  const cinote = async (page) => {
  const out = {};
  for (const id of ['fig-neuralgcm', 'fig-ensemble']) {
    const ann = await page.evaluate((id) => {
      const gd = document.getElementById(id);
      const a = [...gd.querySelectorAll('.annotation')].find(e => /Shaded bands|90% CI/.test(e.textContent));
      if (!a) return null;
      a.scrollIntoView({ block: 'center' });
      return true;
    }, id);
    if (!ann) { out[id] = 'no CI annotation'; continue; }
    await page.waitForTimeout(300);
    out[id] = await page.evaluate((id) => {
      const gd = document.getElementById(id);
      const a = [...gd.querySelectorAll('.annotation')].find(e => /Shaded bands|90% CI/.test(e.textContent));
      const svg = a.closest('.main-svg');
      const r = a.getBoundingClientRect(), s = svg.getBoundingClientRect();
      const inside = r.left >= s.left - 0.5 && r.right <= s.right + 0.5 && r.top >= s.top - 0.5 && r.bottom <= s.bottom + 0.5;
      const cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
      const hit = document.elementFromPoint(cx, cy);
      const stack = document.elementsFromPoint(cx, cy).slice(0, 5).map(e => e.tagName + '.' + (e.getAttribute('class') || ''));
      // Plotly gives every .main-svg and annotation pointer-events:none, so elementFromPoint skips them.
      // Paint-order test: force pointer-events on this figure's SVG content (page only, removed again), re-query.
      const st = document.createElement('style');
      st.textContent = '#' + id + ' .main-svg, #' + id + ' .main-svg * { pointer-events: all !important; }';
      document.head.appendChild(st);
      const hit2 = document.elementsFromPoint(cx, cy).find(e => !['svg', 'g', 'DIV'].includes(e.tagName)); // topmost painted shape/text; svg and g are transparent containers
      const stack2 = document.elementsFromPoint(cx, cy).slice(0, 6).map(e => e.tagName + '.' + (e.getAttribute('class') || ''));
      st.remove();
      const inView = cy >= 0 && cy <= innerHeight;
      const rel = v => +v.toFixed(1);
      return { text: a.textContent, ann: [rel(r.top - s.top), rel(r.bottom - s.top), rel(r.left - s.left), rel(r.right - s.left)],
        svgWH: [rel(s.width), rel(s.height)], inside, hitIsAnn: !!hit && a.contains(hit),
        pe: getComputedStyle(a).pointerEvents, inView, forcedHitIsAnn: !!hit2 && a.contains(hit2), forcedHit: hit2 ? hit2.tagName + '.' + (hit2.getAttribute('class') || '') + ':' + (hit2.textContent || '').slice(0, 40) : null, stack2,
        hit: hit ? hit.tagName + '.' + (hit.getAttribute('class') || '') + ':' + (hit.textContent || '').slice(0, 40) : null, stack };
    }, id);
  }
  return out;
};
  const sweep = async (page) => page.evaluate(`(
() => {
  const IDS = ['fig-neuralgcm', 'fig-ensemble'];
  const out = {};
  for (const id of IDS) {
    const gd = document.getElementById(id);
    if (!gd) { out[id] = 'missing'; continue; }
    const items = [];
    const add = (el, kind, group) => items.push({ el, kind, group });
    gd.querySelectorAll('text[class$="title"]').forEach(e => add(e, 'title:' + e.getAttribute('class'), null));
    gd.querySelectorAll('.annotation').forEach((e, i) => add(e, 'annotation#' + i + ':' + (e.textContent || '').slice(0, 30), null));
    gd.querySelectorAll('.legend').forEach(e => add(e, 'legend', null));
    gd.querySelectorAll('.legend .traces').forEach((e, i) => add(e, 'legenditem#' + i + ':' + (e.textContent || '').slice(0, 25), null));
    gd.querySelectorAll('.updatemenu-container').forEach(e => add(e, 'updatemenu', null));
    gd.querySelectorAll('.slider-container').forEach(e => add(e, 'slider', null));
    gd.querySelectorAll('.colorbar').forEach((e, i) => add(e, 'colorbar#' + i, null));
    // tick labels of every subplot, grouped by axis (g.xtick, g.x2tick, g.ytick, g.y3tick, colorbar ticks)
    gd.querySelectorAll('g[class$="tick"] text, g[class$="tick"] > text').forEach(e => {
      const g = e.closest('g[class$="tick"]');
      const cls = g.getAttribute('class');
      const cb = e.closest('.colorbar');
      const grp = cb ? 'cbtick:' + [...gd.querySelectorAll('.colorbar')].indexOf(cb) : 'tick:' + cls;
      add(e, grp + ':' + e.textContent, grp);
    });
    const dropped = [];
    const rects = [];
    const seenEl = new Set();
    for (const it of items) {
      if (seenEl.has(it.el)) continue; seenEl.add(it.el);
      const r = it.el.getBoundingClientRect();
      const cs = getComputedStyle(it.el);
      const op = it.el.closest('[style*="opacity: 0"]');
      if (r.width < 0.5 || r.height < 0.5 || cs.display === 'none' || cs.visibility === 'hidden' || !(it.el.textContent || it.kind.startsWith('legend') || it.kind.startsWith('colorbar') || it.kind === 'updatemenu' || it.kind === 'slider') ) {
        dropped.push(it.kind); continue;
      }
      rects.push({ ...it, r });
    }
    const hits = [];
    for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (a.group && a.group === b.group) continue; // same-axis ticks, legend item pairs
      const ox = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const oy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (ox > 0 && oy > 0) hits.push({ a: a.kind, b: b.kind, ox: +ox.toFixed(1), oy: +oy.toFixed(1) });
    }
    const counts = {};
    rects.forEach(x => { const k = x.kind.split(/[:#]/)[0]; counts[k] = (counts[k] || 0) + 1; });
    out[id] = { size: Math.round(gd.getBoundingClientRect().width) + 'x' + Math.round(gd.getBoundingClientRect().height), counts, dropped: dropped.length, droppedKinds: [...new Set(dropped.map(d => d.split(':').slice(0, 2).join(':')))].slice(0, 10), hits };
  }
  for (const id of IDS) { const gd = document.getElementById(id); if (!gd) continue; const c = gd.closest('.jp-OutputArea-output'); out[id].fit = { svg: Math.max(...[...gd.querySelectorAll('.main-svg')].map(s => Math.round(s.getBoundingClientRect().width))), client: c.clientWidth, scroll: c.scrollWidth }; }
  out._page = { innerWidth, scrollWidth: document.documentElement.scrollWidth };
  return out;
}
)()`);
  const measure = async (page) => {
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
    res[id] = { hovermode: info.hovermode, height: info.height, bandsTraces: info.bandsTraces, scale: scale.map(x => `${x.axis} ${x.len}px ${x.pxPerKg}px/kg top ${x.range[1].toFixed(0)} maxHi ${x.maxHi} maxMean ${x.maxMean} clipped ${x.clipped}`), checksAllOk: info.checks.every(c => c.bandX_eq && c.cd_eq_band && c.lo_le_y_le_hi && c.bandHoverSkip && c.bandInLegend === false), axes: info.axes.map(a => a.k + ':' + a.type + ':' + a.len + 'px:' + a.range.join('..') + ':' + a.rangemode),
      hoverPanelLead: { total: hoverPanelLead.length, ok: hoverPanelLead.filter(h => h.ok).length, fails: hoverPanelLead.filter(h => !h.ok), sample: hoverPanelLead.slice(0, 1).map(h => h.items) },
      hoverMarker: { total: hoverMarker.length, ok: hoverMarker.filter(h => h.ok).length, fails: hoverMarker.filter(h => !h.ok) },
      nClose: pairs.filter(p => p.px < 9).length, nCloseOverlap: pairs.filter(p => p.px < 9 && p.ciOverlap).length,
      closeNoOverlap: pairs.filter(p => p.px < 9 && !p.ciOverlap).map(p => `${p.sub}@${p.lead} ${p.a}-${p.b} ${p.kg}kg/${p.px}px`),
      minPx: Math.min(...pairs.map(p => p.px)), nPairs: pairs.length };
  }
  return res;
};
  const w = page.viewportSize().width;
  const rep = page.url().includes('fixture') ? 'fixture' : 'full';
  const ci = await cinote(page);
  const sw = await sweep(page);
  const m = await measure(page);
  for (const id of ['fig-neuralgcm', 'fig-ensemble']) {
    await page.mouse.move(5, 5);
    await page.locator('#' + id).screenshot({ path: '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/R4/' + id.replace('fig-', '') + '-' + rep + '-' + w + '.png' });
  }
  const s = { rep, w };
  for (const id of ['fig-neuralgcm', 'fig-ensemble']) {
    const c = ci[id];
    s[id] = { ci: { inside: c.inside, box_top_bottom: c.ann.slice(0, 2), svgH: c.svgWH[1], elementFromPoint_isAnn: c.hitIsAnn, pe: c.pe, paintTopIsAnn: c.forcedHitIsAnn },
      sweep: { hits: sw[id].hits.length, counts: sw[id].counts, dropped: sw[id].dropped, fit: sw[id].fit },
      hover: { panelLead: m[id].hoverPanelLead.ok + '/' + m[id].hoverPanelLead.total, markers: m[id].hoverMarker.ok + '/' + m[id].hoverMarker.total, sample: m[id].hoverPanelLead.sample } };
  }
  s.page = sw._page;
  return s;
}