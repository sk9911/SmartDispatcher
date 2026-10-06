(gd) => {
  const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom].map(v => Math.round(v * 10) / 10); };
  const g = gd.getBoundingClientRect(); const fl = gd._fullLayout;
  const plots = {};
  for (const [xa, ya] of [['xaxis', 'yaxis'], ['xaxis2', 'yaxis2']]) {
    const X = fl[xa], Y = fl[ya];
    plots[xa] = [g.left + X._offset, g.top + Y._offset, g.left + X._offset + X._length, g.top + Y._offset + Y._length].map(v => Math.round(v * 10) / 10);
  }
  const anns = [...gd.querySelectorAll('g.annotation')].map((e, i) => ({ i, text: e.textContent, r: R(e) }));
  const caps = anns.filter(a => /shown at top edge/.test(a.text));
  const inter = (a, b) => Math.min(a[2], b[2]) - Math.max(a[0], b[0]) > 0 && Math.min(a[3], b[3]) - Math.max(a[1], b[1]) > 0;
  // annotation vs plot areas
  const capInfo = caps.map(c => ({ text: c.text, r: c.r,
    vsPlot: Object.fromEntries(Object.entries(plots).map(([k, p]) => [k, { intersects: inter(c.r, p), gapAbovePlotTop: Math.round((p[1] - c.r[3]) * 10) / 10 }])) }));
  // every drawn point (faint + pins + medians), per trace
  const covered = []; const counts = {};
  for (const tr of gd.querySelectorAll('.scatterlayer .trace')) {
    const d = tr.__data__ && tr.__data__[0] && tr.__data__[0].trace; if (!d) continue;
    const kind = /\(median\)/.test(d.name) ? 'median' : /above range/.test(d.name) ? 'pin' : 'faint';
    const pts = tr.querySelectorAll('.points path.point');
    counts[d.name + '|' + kind] = pts.length;
    pts.forEach((p, k) => { const r = R(p); for (const c of caps) if (inter(r, c.r)) covered.push({ trace: d.name, kind, k, r, ann: c.text.slice(0, 25) }); });
  }
  // layout intersections among title, annotations (subplot titles, caps, note), legend, axis titles, ticks
  const sel = { title: '.gtitle', ann: 'g.annotation', xt: '.xtitle', yt: '.ytitle', legend: 'g.legend', xtick: '.xtick text', ytick: '.ytick text' };
  const els = [];
  for (const [k, s] of Object.entries(sel)) gd.querySelectorAll(s).forEach((e, i) => { const r = R(e); if (r[2] - r[0] > 0 && r[3] - r[1] > 0) els.push({ k, txt: (e.textContent || '').slice(0, 45), r }); });
  const hits = [];
  for (let a = 0; a < els.length; a++) for (let b = a + 1; b < els.length; b++) {
    const A = els[a], B = els[b]; if (A.k === B.k && (A.k === 'xtick' || A.k === 'ytick')) continue;
    const ox = Math.min(A.r[2], B.r[2]) - Math.max(A.r[0], B.r[0]), oy = Math.min(A.r[3], B.r[3]) - Math.max(A.r[1], B.r[1]);
    if (ox > 0 && oy > 0) hits.push({ a: A.k + ':' + A.txt, b: B.k + ':' + B.txt, ox, oy });
  }
  const gr = R(gd); const outside = els.filter(e => e.r[0] < gr[0] - 0.5 || e.r[2] > gr[2] + 0.5 || e.r[1] < gr[1] - 0.5 || e.r[3] > gr[3] + 0.5).map(e => e.k + ':' + e.txt + ' ' + JSON.stringify(e.r));
  const nonTick = els.filter(e => !/tick/.test(e.k)).map(e => [e.k, e.txt, e.r]);
  return { gd: gr, plots, capInfo, coveredN: covered.length, covered, counts, nEls: els.length, hits, outside, nonTick,
    legendRows: [...new Set([...gd.querySelectorAll('g.legend .traces')].map(t => Math.round(t.getBoundingClientRect().top)))].length };
}
