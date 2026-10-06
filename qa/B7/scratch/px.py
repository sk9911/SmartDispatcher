import json, re, sys
from PIL import Image
raw = open(sys.argv[1]).read()
data = json.loads(raw[raw.index('{'):raw.rindex('}')+1])
im = Image.open(sys.argv[2]).convert('RGB')
def hx(c): c=c.lstrip('#'); return tuple(int(c[i:i+2],16) for i in (0,2,4))
names={'6':'Hindsight band','7':'IFS HRES','8':'GraphCast','9':'Pangu-Weather','10':'Persistence'}
for ti,v in data.items():
    tgt=hx(v['color']); hit=0; n=0
    for x,y in v['pts']:
        n+=1; best=999
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                p=im.getpixel((int(round(x))+dx,int(round(y))+dy)); best=min(best,max(abs(p[i]-tgt[i]) for i in range(3)))
        hit+= best<=40
    print(f"{names.get(ti,ti):16s} {v['color']} own-colour pixel within 1px at {hit}/{n} samples ({100*hit/n:.0f}%)")
