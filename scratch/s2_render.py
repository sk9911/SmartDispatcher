import sys, json, pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright
from regret.figures.geostrophic import build_geostrophic, FIG_ID
src = "data/results/geostrophic.parquet"
df = pd.read_parquet(src)
fig = build_geostrophic(df)
Path("scratch/s2_fig.html").write_text(fig.to_html(div_id=FIG_ID, include_plotlyjs=True, full_html=True))
inner = fig.to_html(div_id=FIG_ID, full_html=False, include_plotlyjs=True)
Path("scratch/s2_fig768.html").write_text(f'<html><body style="margin:0"><div style="width:768px;border:1px solid red">{inner}</div></body></html>')
JS = """() => {
 const root=document.getElementById('fig-geostrophic');
 const sels=['.gtitle','.xtitle','.ytitle','.xtick text','.ytick text','.legend .traces','.annotation'];
 const els=[];
 sels.forEach(s=>root.querySelectorAll(s).forEach(e=>els.push([s,e])));
 const r=els.map(([s,e])=>[s,e.getBoundingClientRect(),e]);
 const out=[];
 for(let i=0;i<r.length;i++)for(let j=i+1;j<r.length;j++){
  const [sa,a,ea]=r[i],[sb,b,eb]=r[j];
  if(ea.contains(eb)||eb.contains(ea))continue;
  if(sa===sb&&(sa.includes('tick')))continue;
  if(a.width==0||b.width==0)continue;
  if(a.left<b.right&&b.left<a.right&&a.top<b.bottom&&b.top<a.bottom)out.push([sa,sb,ea.textContent,eb.textContent]);
 }
 const sv=root.querySelector('svg.main-svg').getBoundingClientRect();
 return {n:r.length,overlaps:out,svgW:sv.width,rootW:root.getBoundingClientRect().width,scrollW:document.documentElement.scrollWidth,vw:window.innerWidth};
}"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for name, w in (("s2_fig.html",1100),("s2_fig768.html",900)):
        pg = b.new_page(viewport={"width": w, "height": 900})
        errs=[]
        pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file://"+str(Path("scratch/"+name).resolve()))
        pg.wait_for_selector(".main-svg")
        pg.wait_for_timeout(800)
        res = pg.evaluate(JS)
        print(name, json.dumps(res), "console errors:", errs)
        pg.screenshot(path=f"scratch/{name}.png")
    b.close()
