import json, pandas as pd
from playwright.sync_api import sync_playwright
from regret.figures.sanity import build_sanity, FIG_ID
df = pd.read_parquet("data/results/regret.parquet")
fig = build_sanity(df)
fig.write_html("qa/T27/scratch/sanity-b9.html", include_plotlyjs="cdn" if False else True, div_id=FIG_ID)
import pathlib
html = pathlib.Path("qa/T27/scratch/sanity-b9.html").resolve()
wrap = pathlib.Path("qa/T27/scratch/sanity-b9-768.html").resolve()
body = html.read_text()
wrap.write_text('<html><body><div style="width:768px;border:1px solid #ccc">' + body.split("<body>")[1].split("</body>")[0] + '</div></body></html>' if False else
  body.replace("<body>", '<body><div style="width:768px">',1).replace("</body>", "</div></body>",1))
SWEEP = """() => {
 const root=document.querySelector('.js-plotly-plot');
 const els=[...root.querySelectorAll('text[class$="title"], .annotation, .legend, .legend *, .xtick text, .ytick text, .gtitle, .infolayer .g-gtitle')];
 const uniq=[...new Set(els)].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0});
 const tickAxis=e=>{const g=e.closest('.xtick,.ytick'); if(!g) return null; const a=g.closest('g[class*="xaxislayer"],g[class*="yaxislayer"]'); return a? a.getAttribute('class'):null};
 const hits=[];
 for(let i=0;i<uniq.length;i++)for(let j=i+1;j<uniq.length;j++){
  const a=uniq[i],b=uniq[j]; if(a.contains(b)||b.contains(a))continue;
  const ta=tickAxis(a),tb=tickAxis(b); if(ta&&ta===tb)continue;
  const A=a.getBoundingClientRect(),B=b.getBoundingClientRect();
  if(A.left<B.right-0.5&&B.left<A.right-0.5&&A.top<B.bottom-0.5&&B.top<A.bottom-0.5)hits.push([a.textContent.slice(0,30),b.textContent.slice(0,30)]);}
 const areas=[...root.querySelectorAll('.nsewdrag')].map(e=>Math.round(e.getBoundingClientRect().height));
 return {n:uniq.length,hits,areas,W:root.getBoundingClientRect().width,H:root.getBoundingClientRect().height};
}"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for name, f, vw in (("standalone", html, 1280), ("768", wrap, 900)):
        pg = b.new_page(viewport={"width": vw, "height": 900})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f.as_uri()); pg.wait_for_selector(".js-plotly-plot .nsewdrag"); pg.wait_for_timeout(800)
        print(name, json.dumps(pg.evaluate(SWEEP)), "errors:", errs)
        pg.screenshot(path=f"qa/T27/scratch/sanity-b9-{name}.png", full_page=True)
    b.close()
