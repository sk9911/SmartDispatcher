import json
from playwright.sync_api import sync_playwright
from regret import config
from regret.figures import showcase_map as sm
cfg = config.get_config("fixture")
sm.write_html(sm.build_showcase_map(cfg), "qa/B7/scratch/fig.html")
import pathlib
uri = pathlib.Path("qa/B7/scratch/fig.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    page = b.new_page(viewport={"width": 1280, "height": 900})
    reqs, errs = [], []
    page.on("request", lambda r: reqs.append(r.url))
    page.on("console", lambda m: m.type == "error" and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(uri); page.wait_for_selector(".legend .traces"); page.wait_for_timeout(1500)
    ev = lambda js: page.evaluate(js)
    cb = lambda: page.text_content(".cbtitle")
    # slider: click on step 2 (GraphCast) by clicking its grip position via mouse on the rail
    def click_step(i):
        box = page.locator(".slider-rail-rect").bounding_box()
        n = 1 + len(cfg.sources)
        page.mouse.click(box["x"] + box["width"] * i / (n - 1), box["y"] + box["height"] / 2)
        page.wait_for_timeout(500)
    def pick_lead(lead):
        page.locator(".updatemenu-header").first.click(); page.wait_for_timeout(300)
        page.locator(".updatemenu-item-text", has_text=f"{lead} h").last.click(); page.wait_for_timeout(600)
    click_step(2); print("after slider step 2 @24h:", cb())
    pick_lead(72); print("after 72h button:", cb(), "| slider.active =", ev("document.getElementById('fig-showcase-map').layout.sliders[0].active"))
    print("bg hover:", ev("document.getElementById('fig-showcase-map').data[0].hovertemplate"))
    click_step(2); print("after slider step 2 @72h:", cb())
    pick_lead(72); 
    print("line trace marker.color untouched:", ev("document.getElementById('fig-showcase-map').data[2].marker && document.getElementById('fig-showcase-map').data[2].marker.color"))
    for lead in cfg.leads_h:
        pick_lead(lead)
        print("legend entries lead", lead, page.locator(".legend .traces").count())
    pick_lead(24)
    sel = {"title": ".gtitle", "dropdown": ".updatemenu-container", "legend": ".legend", "slider labels": ".slider-container .slider-label, .slider-container .slider-labels", "colorbar": ".colorbar"}
    boxes = {k: ev("[...document.querySelectorAll('%s')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})" % v) for k, v in sel.items()}
    # tighter: slider label text elements
    boxes["slider text"] = ev("[...document.querySelectorAll('.slider-container text')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})")
    boxes["cbtitle"] = ev("[...document.querySelectorAll('.cbtitle')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})")
    boxes["dropdown text"] = ev("[...document.querySelectorAll('.updatemenu-container text, .infolayer .annotation')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})")
    print({k: len(v) for k, v in boxes.items()})
    bad = []
    ks = list(boxes)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            for r1 in boxes[ks[i]]:
                for r2 in boxes[ks[j]]:
                    if not (r1[2] <= r2[0] or r2[2] <= r1[0] or r1[3] <= r2[1] or r2[3] <= r1[1]):
                        bad.append((ks[i], ks[j], r1, r2))
    print("overlaps:", [(a, b_) for a, b_, *_ in bad][:20])
    print("cbtitle height vs colorbar:", boxes["cbtitle"], boxes["colorbar"])
    print("outside requests:", [u for u in reqs if not u.startswith(("file:", "data:"))], "errors:", errs)
    page.screenshot(path="qa/B7/scratch/b7.png"); b.close()
