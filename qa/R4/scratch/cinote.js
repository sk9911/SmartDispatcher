async (page) => {
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
}
