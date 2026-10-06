import json,re,sys
raw=open('qa/B3/scratch/attempt2-cells.json').read()
# file may contain a quoted JSON string after a heading
m=raw[raw.index('"{'):] if '"{' in raw else raw[raw.index('{'):]
d=json.loads(json.loads(m.strip().splitlines()[0])) if m.startswith('"') else json.loads(m)
print('nCols',d['nCols'],'kit',d['kit'],'scrollbar',d['scrollbarGlyph'])
print('headerValues',d['headerValues'])
kt,kb=d['kit']['top'],d['kit']['bottom']
for c in d['cols']:
  for b in c['blocks']:
    if not b['n']: continue
    cells=b['cells']
    hs=sorted(set(x['h'] for x in cells)); lines=[x['lines'] for x in cells]
    out=[i for i,x in enumerate(cells) if x['top']<kt-0.5 or x['bot']>kb+0.5]
    over=[ (i,x['text'],x['tR']-x['right']) for i,x in enumerate(cells) if x['tR'] and x['tR']>x['right']+0.1]
    print(c['i'],b['id'],'n',b['n'],'w',cells[0]['w'],'heights',hs,'lines',sorted(set(lines)),'first',cells[0]['top'],'last',cells[-1]['top'],cells[-1]['bot'],'outside',out,'overflow',over[:3])
