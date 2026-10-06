import json
from playwright.sync_api import sync_playwright
from regret import config
from regret.figures import showcase_map as sm
cfg = config.get_config("fixture")
sm.write_html(sm.build_showcase_map(cfg), "qa/B7/scratch/fig2.html")
JS = """() => { const gd=document.getElementById('fig-showcase-map');
 const R=e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};
 const els=[];const add=(k,l)=>l.forEach((e,i)=>{const r=R(e); if(r[2]-r[0]>0&&r[3]-r[1]>0) els.push([k+'#'+i,r,e])});
 add('title',[...gd.querySelectorAll('text.gtitle')]);
 add('dropdown',[...gd.querySelectorAll('.updatemenu-container')]);
 add('leadlabel',[...gd.querySelectorAll('.annotation-text-g')]);
 add('legend',[...gd.querySelectorAll('.legend')]);
 add('entry',[...gd.querySelectorAll('.legend .traces')]);
 add('slider',[...gd.querySelectorAll('.slider-container')]);
 add('sliderlabel',[...gd.querySelectorAll('.slider-container text')]);
 add('bar',[...gd.querySelectorAll('.colorbar')]);
 const hits=[];
 for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){
  const [ka,a,ea]=els[i],[kb,b,eb]=els[j];
  if(ea.contains(eb)||eb.contains(ea))continue;
  const ox=Math.min(a[2],b[2])-Math.max(a[0],b[0]),oy=Math.min(a[3],b[3])-Math.max(a[1],b[1]);
  if(ox>0.5&&oy>0.5)hits.push(ka+' x '+kb+' '+ox.toFixed(1)+'x'+oy.toFixed(1));}
 const sv=R(gd.querySelector('svg.main-svg')), vis=[];
 for(const [k,r,e] of els.filter(x=>x[0].startsWith('entry'))){
  const cx=(r[0]+r[2])/2,cy=(r[1]+r[3])/2, inside=r[0]>=sv[0]-.5&&r[2]<=sv[2]+.5&&r[1]>=sv[1]-.5&&r[3]<=sv[3]+.5;
  const top=document.elementFromPoint(cx,cy); vis.push(!!(inside&&top&&e.contains(top)));}
 return {hits, entries:vis.length, visible:vis.filter(Boolean).length, text:[...gd.querySelectorAll('.legend .traces text')].map(t=>t.textContent)};}"""
def run(container):
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1000 if container else 1200, "height": 1000})
        reqs, errs = [], []
        pg.on("request", lambda r: reqs.append(r.url)); pg.on("console", lambda m: m.type == "error" and errs.append(m.text)); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file:///Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/scratch/fig2.html")
        pg.wait_for_selector(".legend .traces")
        if container:
            pg.evaluate("""()=>{const d=document.createElement('div');d.style.width='768px';const g=document.getElementById('fig-showcase-map');g.parentNode.insertBefore(d,g);d.appendChild(g);Plotly.Plots.resize(g);}""")
        pg.wait_for_timeout(1500)
        out["gd_width"] = pg.evaluate("document.getElementById('fig-showcase-map').getBoundingClientRect().width")
        for i, lead in enumerate(cfg.leads_h):
            pg.evaluate("(i)=>{const d=document.getElementById('fig-showcase-map');const b=d.layout.updatemenus[0].buttons[i];return Plotly.update(d,b.args[0],b.args[1])}", i)
            pg.wait_for_timeout(400)
            r = pg.evaluate(JS); out[f"lead{lead}"] = {k: r[k] for k in ("hits", "entries", "visible")}
            if lead == 24: out["legend_text"] = r["text"]
        def pick_lead(txt):
            pg.locator(".updatemenu-header").first.click(); pg.wait_for_timeout(300)
            pg.locator(".updatemenu-item-text", has_text=txt).first.click(); pg.wait_for_timeout(500)
        def click_step(k):
            sl = pg.locator(".slider-container .slider-rail-rect").first.bounding_box()
            pg.mouse.click(sl["x"] + sl["width"] * k / 4 * 0.98 + 3, sl["y"] + sl["height"] / 2); pg.wait_for_timeout(500)
        pick_lead("48 h"); pick_lead("24 h"); print("lead active", pg.evaluate("document.getElementById('fig-showcase-map').layout.updatemenus[0].active")); click_step(2); t1 = pg.text_content(".cbtitle")
        pick_lead("72 h"); t2 = pg.text_content(".cbtitle")
        act = pg.evaluate("document.getElementById('fig-showcase-map').layout.sliders[0].active")
        click_step(1); t3 = pg.text_content(".cbtitle")
        out["desync"] = [t1, t2, act, t3]
        pick_lead("24 h")
        out["band"] = pg.evaluate("document.getElementById('fig-showcase-map').data[1].line.color")
        out["bg_max"] = pg.evaluate("document.getElementById('fig-showcase-map').data[0].marker.colorscale.slice(-1)[0]")
        pg.screenshot(path=f"qa/B7/scratch/fig2-{'768' if container else '1200'}.png")
        out["outside_requests"] = [u for u in reqs if not u.startswith(("file:", "data:"))]; out["errors"] = errs
        b.close()
    return out
print(json.dumps({"1200": run(False), "768": run(True)}, indent=1))
