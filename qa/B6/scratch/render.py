import pandas as pd, json
from playwright.sync_api import sync_playwright
from regret.figures.wind_error import build_wind_error, FIG_ID as W
from regret.figures.lead_regret import build_lead_regret, FIG_ID as L
df = pd.read_parquet("data/results/regret.parquet")
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome"); 
    for name, fig, fid in (("wind", build_wind_error(df), W), ("lead", build_lead_regret(df), L)):
        path = f"qa/B6/scratch/{name}.html"
        open(path, "w").write(fig.to_html(div_id=fid, include_plotlyjs=True))
        pg = b.new_page(viewport={"width": 1100, "height": 800}); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        import os; pg.goto("file://" + os.path.abspath(path)); pg.wait_for_selector(f"#{fid} .main-svg")
        pg.wait_for_timeout(1000)
        out[name] = pg.evaluate("""(id)=>{const gd=document.getElementById(id);const r=gd.getBoundingClientRect();
          const axes=Object.keys(gd._fullLayout).filter(k=>/^[xy]axis\\d*$/.test(k)).map(k=>[k,gd._fullLayout[k].range,gd._fullLayout[k]._length]);
          return {h:r.height,axes}}""", fid)
        out[name]["errors"] = errs
        pg.screenshot(path=f"qa/B6/scratch/{name}.png")
    b.close()
# forecast point share of plot area
f = df[~df.is_truth_optimised]
for panel, sub in (("forecast", f[f.source != "persistence"]), ("persistence", f[f.source == "persistence"])):
    out[panel + "_pts"] = dict(n=len(sub), xmax=sub.wind_error_ms.max(), ymin=sub.regret_fuel_kg.min(), ymax=sub.regret_fuel_kg.max())
print(json.dumps(out, indent=1, default=float))
