import json,re
raw=open('qa/B3/scratch/attempt2-cells.json').read()
d=json.loads(json.loads(raw[raw.index('"{'):].strip().splitlines()[0]))
cols=[[c for b in col['blocks'] if b['id']=='cells1' for c in b['cells']] for col in d['cols']]
CI={2,5,8,11}
bad=[]
for ci,cells in enumerate(cols):
  for ri,c in enumerate(cells):
    lt=c['lineTexts'] or [c['text']]
    if ci in CI:
      ok=len(lt)==2 and re.fullmatch(r'-?\d+(\.\d+)?',lt[0]) and re.fullmatch(r'\[-?\d+(\.\d+)?, -?\d+(\.\d+)?\]',lt[1])
    else: ok=len(lt)==1
    if not ok: bad.append((ci,ri,lt))
print('2c bad',bad)
# text vertical fit
print('text outside rect', [(ci,ri) for ci,cells in enumerate(cols) for ri,c in enumerate(cells) if c['tT']<c['top'] or c['tB']>c['bot']])
print('row tops col0',[c['top'] for c in cols[0]])
# decimals
def dec(s): return len(s.split('.')[1]) if '.' in s else 0
for ci,cells in enumerate(cols):
  nums=[n for c in cells for n in re.findall(r'-?\d+(?:\.\d+)?', ' '.join(c['lineTexts'] or [c['text']]))] if ci else []
  if ci: print(ci, sorted(set(dec(n) for n in nums)), 'n',len(nums), 'ex', (cells[0]['lineTexts'] or [cells[0]['text']]))
rows=[[ ' '.join(cols[ci][ri]['lineTexts'] or [cols[ci][ri]['text']]) for ci in range(15)] for ri in range(20)]
for r in rows: print(r[0],r[1],'|',r[2],'|',r[5],'|',r[6],r[7])
# Fuel% zero vs fuel kg
z=[]
for r in rows:
  kg=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', r[2]+' '+r[3]+' '+r[4])]
  pc=re.findall(r'-?\d+(?:\.\d+)?', r[5]+' '+r[6]+' '+r[7])
  for k,p in zip(kg,pc):
    if k>0 and float(p)==0: z.append((r[0],r[1],k,p))
  if any(p=='0' for p in pc): z.append(('bare0',r[0],r[1]))
print('2d zero issues',z)
