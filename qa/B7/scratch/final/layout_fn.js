(gd) => {
  const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom].map(v => Math.round(v*10)/10); };
  const els = {};
  const add = (k, list) => { list.forEach((e, i) => { const r = R(e); if (r[2]-r[0] > 0 && r[3]-r[1] > 0) els[k + (list.length > 1 ? '#' + i : '')] = r; }); };
  add('title', [...gd.querySelectorAll('text.gtitle')]);
  add('dropdown', [...gd.querySelectorAll('.updatemenu-header-group')]);
  add('leadAnnot', [...gd.querySelectorAll('.annotation text')]);
  add('legend', [...gd.querySelectorAll('.legend > rect.bg')]);
  add('legendItem', [...gd.querySelectorAll('.legend .traces')]);
  add('sliderCurrent', [...gd.querySelectorAll('.slider-group > text.slider-label')]);
  add('sliderStep', [...gd.querySelectorAll('.slider-label-group text')]);
  add('colorbar', [...gd.querySelectorAll('g.colorbar')]);
  add('cbtitle', [...gd.querySelectorAll('.cbtitle')]);
  add('sliderRail', [...gd.querySelectorAll('.slider-rail-rect')]);
  add('geo', [...gd.querySelectorAll('.geo .bglayer rect, .geolayer .bg rect')]);
  const ks = Object.keys(els), hits = [];
  const fam = k => k.split('#')[0];
  for (let i = 0; i < ks.length; i++) for (let j = i+1; j < ks.length; j++) {
    const a = els[ks[i]], b = els[ks[j]];
    if (fam(ks[i]) === fam(ks[j]) && !['sliderStep','legendItem'].includes(fam(ks[i]))) continue;
    if ([fam(ks[i]),fam(ks[j])].includes('legend') && [fam(ks[i]),fam(ks[j])].includes('legendItem')) continue;
    if ([fam(ks[i]),fam(ks[j])].includes('geo')) continue;
    if (['colorbar','cbtitle'].includes(fam(ks[i])) && ['colorbar','cbtitle'].includes(fam(ks[j]))) continue;
    const ox = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), oy = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
    if (ox > 0.5 && oy > 0.5) hits.push(`${ks[i]} x ${ks[j]} (${ox.toFixed(1)}x${oy.toFixed(1)})`);
  }
  const g = R(gd); const outside = Object.entries(els).filter(([k,r]) => k!=='geo' && (r[0] < g[0]-0.5 || r[2] > g[2]+0.5 || r[1] < g[1]-0.5 || r[3] > g[3]+0.5)).map(([k,r]) => k + ' ' + JSON.stringify(r));
  return {gd: g, els, hits, outside};
}
