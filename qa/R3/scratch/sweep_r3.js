async (page) => page.evaluate(`(
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
)()`)
