import json, numpy as np, pandas as pd
from playwright.sync_api import sync_playwright
from regret.figures.wind_error import build_wind_error
from regret.figures.lead_regret import build_lead_regret
from regret.figures.sanity import build_sanity
df = pd.read_parquet("data/results/regret.parquet")
figs = {"wind": build_wind_error(df), "lead": build_lead_regret(df), "sanity": build_sanity(df)}
fw = figs["wind"]
pan = df[~df.is_truth_optimised]
for ax, name, sel in (("yaxis","forecast",pan.source!="persistence"),("yaxis2","persistence",pan.source=="persistence")):
    top = fw.layout[ax].range[1]; r = pan[sel].regret_fuel_kg
    print(name,"y-cap",round(top,1),"pinned",int((r>top).sum()),"of",len(r),"max",round(r.max(),1))
for t in fw.data:
    if t.name.endswith("(median)"):
        print(t.name,"first",round(t.y[0],1),"last",round(t.y[-1],1),"rises",t.y[-1]>t.y[0],"bins",len(t.y), [round(v,1) for v in t.y])
JS = """() => { const sel=(c)=>[...document.querySelectorAll(c)];
 const boxes=[]; const add=(k,e)=>{const r=e.getBoundingClientRect(); if(r.width>0&&r.height>0) boxes.push([k+':'+(e.textContent||'').slice(0,30),r]);};
 sel('.gtitle').forEach(e=>add('title',e)); sel('.legend').forEach(e=>add('legend',e));
 sel('.annotation').forEach(e=>add('ann',e)); sel('.g-xtitle,.g-ytitle').forEach(e=>add('axtitle',e));
 const out=[]; for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i][1],b=boxes[j][1];
  if(a.left<b.right-.5&&b.left<a.right-.5&&a.top<b.bottom-.5&&b.top<a.bottom-.5)out.push([boxes[i][0],boxes[j][0]]);}
 return {n:boxes.length,overlaps:out}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for width in (None, 768):
        for name, fig in figs.items():
            pg = b.new_page(viewport={"width": 1280, "height": 900}); errs=[]
            pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
            html = fig.to_html(include_plotlyjs=True, full_html=False, div_id="f")
            wrap = f'<div style="width:{width}px">' if width else '<div>'
            pg.set_content(f"<html><body style='margin:0'>{wrap}{html}</div></body></html>")
            pg.wait_for_selector("#f .main-svg"); pg.wait_for_timeout(800)
            res = pg.evaluate(JS)
            tag = f"{name}-{width or 'full'}"
            if name == "wind":
                res["gap"] = pg.evaluate("""() => { const g=document.getElementById('f'); const fl=g._fullLayout;
                  const out={}; g._fullData.filter(t=>t.name.endsWith('(median)')).forEach(t=>{const n=t.y.length; out[t.meta]=[fl.yaxis.l2p(t.y[n-1])-0, fl.yaxis.l2p(t.y[n-2])-0];});
                  return out; }""")
            print(tag, json.dumps(res), "console_errors", errs)
            pg.locator("#f").screenshot(path=f"qa/B6/scratch/{tag}.png"); pg.close()
    b.close()
