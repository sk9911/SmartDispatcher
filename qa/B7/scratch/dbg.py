from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome"); pg=b.new_page(viewport={"width":1184,"height":1000})
    pg.goto("file:///Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/scratch/fig4.html"); pg.wait_for_selector(".legend .traces"); pg.wait_for_timeout(1500)
    print(pg.evaluate("""()=>{const g=document.getElementById('fig-showcase-map');const vis=g.data.filter(t=>t.visible!==false&&t.visible!=='legendonly');
    const els=g.querySelectorAll('.geo .scatterlayer .trace');return [g.data.length,vis.length,els.length,vis.findIndex(t=>t.meta.source==='persistence'),[...els].map(e=>!!e.querySelector('path.js-line'))]}"""))
