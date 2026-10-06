import os
import pandas as pd
from playwright.sync_api import sync_playwright
from regret.figures.wind_error import build_wind_error, FIG_ID

df = pd.read_parquet("data/results/regret.parquet")
html = build_wind_error(df).to_html(div_id=FIG_ID, include_plotlyjs=True, full_html=True)
path = os.path.abspath("qa/B6/scratch/wind3.html")
open(path, "w").write(html)
JS = """() => {
 const r=e=>{const b=e.getBoundingClientRect();return [b.left,b.top,b.right,b.bottom]};
 const I=(a,b)=>a[0]<b[2]&&b[0]<a[2]&&a[1]<b[3]&&b[1]<a[3];
 const g=document.querySelector('#fig-wind-error');
 const anns=[...g.querySelectorAll('.annotation')].map(e=>({t:e.textContent,r:r(e)}));
 const caps=anns.filter(a=>a.t.includes('top edge'));
 const subs=anns.filter(a=>/^(Forecast sources|Persistence baseline)$/.test(a.t));
 const plots=[...g.querySelectorAll('.nsewdrag')].map(r);
 const items={title:r(g.querySelector('.gtitle')),legend:r(g.querySelector('.legend')),
  note:anns.find(a=>a.t.startsWith('Lines:')).r};
 g.querySelectorAll('.xtitle,.x2title').forEach((e,i)=>items['xtitle'+i]=r(e));
 subs.forEach((s,i)=>items['sub'+i]=s.r); caps.forEach((s,i)=>items['cap'+i]=s.r);
 const ks=Object.keys(items), pairs=[];
 for(let i=0;i<ks.length;i++)for(let j=i+1;j<ks.length;j++) if(I(items[ks[i]],items[ks[j]])) pairs.push([ks[i],ks[j]]);
 return {n_caps:caps.length,n_plots:plots.length,capVsPlot:caps.map(c=>plots.map(p=>I(c.r,p))),pairs,n_items:ks.length,
   caps:caps.map(c=>c.r),plots};
}"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for w in (1184, 768):
        pg = b.new_page(viewport={"width": 1224 if w == 1184 else 800, "height": 760})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file://" + path)
        if w == 768:
            pg.add_style_tag(content="body{margin:0}#fig-wind-error{width:768px!important}")
            pg.evaluate("Plotly.Plots.resize(document.querySelector('#fig-wind-error'))")
        pg.wait_for_timeout(1500)
        res = pg.evaluate(JS)
        print(w, res, "console errors", errs)
        pg.screenshot(path=f"qa/B6/scratch/wind3-{w}.png", full_page=True)
    b.close()
