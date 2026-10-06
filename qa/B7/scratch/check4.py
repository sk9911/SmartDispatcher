import json, re
from playwright.sync_api import sync_playwright
import numpy as np
exec(open("qa/B7/scratch/check2.py").read().split("def run")[0].split("cfg = ")[0])  # imports only
JS = re.search(r'JS = """(.*?)"""', open("qa/B7/scratch/check2.py").read(), re.S).group(1)
URL = "file:///Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/scratch/fig4.html"
def L(c):
    c = np.array(c[:3]) / 255; c = np.where(c <= .03928, c/12.92, ((c+.055)/1.055)**2.4); return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b):
    a, b = L(a), L(b); return (max(a, b)+.05)/(min(a, b)+.05)
def run(container):
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1000 if container else 1184, "height": 1000})
        errs = []; pg.on("console", lambda m: m.type == "error" and errs.append(m.text)); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_selector(".legend .traces")
        if container:
            pg.evaluate("""()=>{const d=document.createElement('div');d.style.width='768px';const g=document.getElementById('fig-showcase-map');g.parentNode.insertBefore(d,g);d.appendChild(g);Plotly.Plots.resize(g);}""")
        pg.wait_for_timeout(1500)
        out["gd_width"] = pg.evaluate("document.getElementById('fig-showcase-map').getBoundingClientRect().width")
        # contrast: hide plans, screenshot, read marker pixels
        pg.evaluate("()=>{const g=document.getElementById('fig-showcase-map');Plotly.restyle(g,{visible:false},g.data.map((_,i)=>i).filter(i=>g.data[i].meta.kind!=='background'))}")
        pg.wait_for_timeout(500)
        pts = pg.evaluate("""()=>{const g=document.getElementById('fig-showcase-map');const t=g._fullData[0];
          const pts=[...g.querySelectorAll('.geo .scatterlayer .trace:first-child .point')]; const r=[];
          pts.forEach((e,i)=>{const b=e.getBoundingClientRect();r.push([b.x+b.width/2,b.y+b.height/2,t.marker.color[i]])});return r}""")
        pg.screenshot(path="qa/B7/scratch/_bg.png")
        from PIL import Image
        im = Image.open("qa/B7/scratch/_bg.png").convert("RGB"); dpr = 1
        sc = [(im.getpixel((int(x), int(y))), z) for x, y, z in pts if 0 <= x < im.width and 0 <= y < im.height]
        core = [np.array(c) for c, z in sc if z >= 60]; quiet = [np.array(c) for c, z in sc if z < 20]
        cm, qm = np.mean(core, 0), np.mean(quiet, 0)
        out["n_core_quiet"] = [len(core), len(quiet)]; out["core_rgb"] = cm.round().tolist(); out["quiet_rgb"] = qm.round().tolist()
        out["core_vs_quiet_mean"] = round(cr(cm, qm), 2)
        out["core_vs_quiet_darkest10%_vs_lightest"] = round(cr(np.percentile(core, 10, 0), np.percentile(quiet, 90, 0)), 2)
        mod = [np.array(c) for c, z in sc if 20 <= z < 60]; mm = np.mean(mod, 0)
        out["n_mod"] = len(mod); out["mod_rgb"] = mm.round().tolist()
        out["core_vs_moderate"] = round(cr(cm, mm), 2); out["moderate_vs_quiet"] = round(cr(mm, qm), 2)
        pg.evaluate("()=>{const g=document.getElementById('fig-showcase-map');Plotly.restyle(g,{visible:true},g.data.map((_,i)=>i).filter(i=>g.data[i].meta.kind!=='background'&&g.data[i].meta.lead_h===24))}")
        pg.wait_for_timeout(500)
        # persistence line: sample points along its path in the plans-hidden background vs plans-shown pixel
        # locate with the legend swatch-independent approach: svg path of the persistence trace
        samples = pg.evaluate("""()=>{const g=document.getElementById('fig-showcase-map');
          const vis=g.data.filter(t=>t.visible!==false&&t.visible!=='legendonly'); const i=vis.findIndex(t=>t.meta.source==='persistence');
          const el=g.querySelectorAll('.geo .scatterlayer .trace')[i]; const p=el.querySelector('path.js-line'); const n=p.getTotalLength(); const m=p.getScreenCTM(); const o=[];
          for(let k=2;k<n-2;k+=3){const q=p.getPointAtLength(k);o.push([q.x*m.a+q.y*m.c+m.e,q.x*m.b+q.y*m.d+m.f]);} return o}""")
        pg.evaluate("()=>{const g=document.getElementById('fig-showcase-map');Plotly.restyle(g,{visible:false},g.data.map((_,i)=>i).filter(i=>g.data[i].meta.kind!=='background'))}")
        pg.wait_for_timeout(400); pg.screenshot(path="qa/B7/scratch/_bg2.png")
        bg = Image.open("qa/B7/scratch/_bg2.png").convert("RGB")
        line = np.array([80, 80, 80]); lc = np.array([127, 127, 127])
        cs = [cr(lc, bg.getpixel((int(x), int(y)))) for x, y in samples if 0 <= x < bg.width and 0 <= y < bg.height]
        jet = [cr(lc, bg.getpixel((int(x), int(y)))) for x, y in samples if 0 <= x < bg.width and 0 <= y < bg.height and sum(bg.getpixel((int(x), int(y)))) < 3*190]
        out["persistence_vs_bg_all"] = {"n": len(cs), "min": round(min(cs), 2), "median": round(float(np.median(cs)), 2)}
        out["persistence_vs_bg_dark_pixels(<190)"] = {"n": len(jet), "min": round(min(jet), 2) if jet else None, "median": round(float(np.median(jet)), 2) if jet else None}
        pg.evaluate("()=>{const g=document.getElementById('fig-showcase-map');Plotly.restyle(g,{visible:true},g.data.map((_,i)=>i).filter(i=>g.data[i].meta.kind!=='background'&&g.data[i].meta.lead_h===24))}")
        pg.wait_for_timeout(400)
        # band visibility: band stroke vs bg
        pg.screenshot(path="qa/B7/scratch/_shown.png")
        sh = Image.open("qa/B7/scratch/_shown.png").convert("RGB")
        ring = []
        for x, y in samples:
            if 4 <= x < sh.width-5 and 4 <= y < sh.height-5 and sum(bg.getpixel((int(x), int(y)))) < 3*190:
                best = max((sh.getpixel((int(x)+dx, int(y)+dy)) for dx in range(-4, 5) for dy in range(-4, 5)), key=sum)
                ring.append(cr(np.array(best), bg.getpixel((int(x), int(y)))))
        out["halo_brightest_px_vs_bg_under_core(n,median)"] = [len(ring), round(float(np.median(ring)), 2) if ring else None]
        out["band_vs_core_bg"] = round(cr(np.array([255, 127, 14]), cm), 2)
        out["band_vs_quiet_bg"] = round(cr(np.array([255, 127, 14]), qm), 2)
        for i, lead in enumerate([12, 24, 48, 72][:0] or []): pass
        import regret.config as C
        leads = pg.evaluate("document.getElementById('fig-showcase-map').layout.updatemenus[0].buttons.map(b=>b.label)")
        for i, lab in enumerate(leads):
            pg.evaluate("(i)=>{const d=document.getElementById('fig-showcase-map');const b=d.layout.updatemenus[0].buttons[i];return Plotly.update(d,b.args[0],b.args[1])}", i)
            pg.wait_for_timeout(400); r = pg.evaluate(JS); out[f"lead{lab}"] = {k: r[k] for k in ("hits", "entries", "visible")}
        def pick_lead(txt):
            pg.locator(".updatemenu-header").first.click(); pg.wait_for_timeout(300)
            pg.locator(".updatemenu-item-text", has_text=txt).first.click(); pg.wait_for_timeout(500)
        def click_step(k):
            sl = pg.locator(".slider-container .slider-rail-rect").first.bounding_box()
            pg.mouse.click(sl["x"] + sl["width"] * k / 4 * 0.98 + 3, sl["y"] + sl["height"] / 2); pg.wait_for_timeout(500)
        pick_lead("48 h"); pick_lead("24 h"); click_step(2); t1 = pg.text_content(".cbtitle")
        pick_lead("72 h"); t2 = pg.text_content(".cbtitle"); act = pg.evaluate("document.getElementById('fig-showcase-map').layout.sliders[0].active")
        click_step(1); t3 = pg.text_content(".cbtitle"); out["desync"] = [t1, t2, act, t3]
        pick_lead("24 h"); pick_lead("24 h") if False else None
        pg.wait_for_timeout(300)
        out["colorbar_title_box"] = pg.evaluate("(()=>{const e=document.querySelector('.cbtitle');const r=e.getBoundingClientRect();const s=document.querySelector('svg.main-svg').getBoundingClientRect();return [r.left,r.right,s.right]})()")
        pg.screenshot(path=f"qa/B7/scratch/fig4-{'768' if container else '1184'}.png")
        out["errors"] = errs; b.close()
    return out
print(json.dumps({"1184": run(False), "768": run(True)}, indent=1))
