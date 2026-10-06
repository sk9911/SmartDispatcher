from playwright.sync_api import sync_playwright
URL="file:///Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/B7/scratch/fig4.html"
SEL={"title":".gtitle","menu":".updatemenu-container","legend":".legend","slider":".slider-container","bar":".colorbar"}
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome")
    for cont in (False,True):
        pg=b.new_page(viewport={"width":1000 if cont else 1184,"height":1000}); reqs=[]; errs=[]
        pg.on("request",lambda r:reqs.append(r.url)); pg.on("console",lambda m:m.type=="error" and errs.append(m.text)); pg.on("pageerror",lambda e:errs.append(str(e)))
        pg.goto(URL); pg.wait_for_selector(".legend .traces")
        if cont: pg.evaluate("""()=>{const d=document.createElement('div');d.style.width='768px';const g=document.getElementById('fig-showcase-map');g.parentNode.insertBefore(d,g);d.appendChild(g);Plotly.Plots.resize(g);}""")
        pg.wait_for_timeout(1200); bad=0
        for i in range(5):
            pg.evaluate("(i)=>{const d=document.getElementById('fig-showcase-map');const b=d.layout.updatemenus[0].buttons[i];return Plotly.update(d,b.args[0],b.args[1])}",i); pg.wait_for_timeout(400)
            bx={k:pg.evaluate("(s)=>[...document.querySelectorAll(s)].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})",s) for k,s in SEL.items()}
            n=list(bx)
            for a in range(len(n)):
                for c in range(a+1,len(n)):
                    for r1 in bx[n[a]]:
                        for r2 in bx[n[c]]:
                            if not(r1[2]<=r2[0] or r2[2]<=r1[0] or r1[3]<=r2[1] or r2[3]<=r1[1]): bad+=1
        print("768" if cont else "1184","intersections",bad,"outside",[u for u in reqs if not u.startswith(("file:","data:"))],"errors",errs)
