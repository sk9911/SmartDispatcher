(gd) => {
  const sel = {title: '.gtitle', ann: '.annotation', xt: '.xtitle', yt: '.ytitle', legend: 'g.legend', xtick: '.xtick text', ytick: '.ytick text'};
  const els = [];
  for (const [k, s] of Object.entries(sel)) gd.querySelectorAll(s).forEach((e, i) => {
    const r = e.getBoundingClientRect(); if (r.width && r.height) els.push({k, i, txt: (e.textContent||'').slice(0, 40), r: [r.left, r.top, r.right, r.bottom].map(Math.round)});
  });
  const hits = [];
  for (let a = 0; a < els.length; a++) for (let b = a + 1; b < els.length; b++) {
    const A = els[a], B = els[b];
    if (A.k === B.k && (A.k === 'xtick' || A.k === 'ytick')) continue;
    const ox = Math.min(A.r[2], B.r[2]) - Math.max(A.r[0], B.r[0]);
    const oy = Math.min(A.r[3], B.r[3]) - Math.max(A.r[1], B.r[1]);
    if (ox > 0 && oy > 0) hits.push({a: A.k + ':' + A.txt, ar: A.r, b: B.k + ':' + B.txt, br: B.r, ox, oy});
  }
  const lg = gd.querySelector('g.legend'); const lr = lg && lg.getBoundingClientRect();
  return {n: els.length, hits, legend: lr && [lr.left, lr.top, lr.right, lr.bottom].map(Math.round),
    legendRows: [...new Set([...gd.querySelectorAll('g.legend .traces')].map(t => Math.round(t.getBoundingClientRect().top)))].length,
    legendItems: [...gd.querySelectorAll('g.legend .legendtext')].map(t => t.textContent),
    plot: (() => {const r = gd.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]})()};
}
