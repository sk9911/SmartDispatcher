import json
raw=open('qa/B3/scratch/attempt2-lines.json').read()
s=raw[raw.index('"{'):].strip().splitlines()[0]
d=json.loads(json.loads(s))
print('overflowCount',d['overflowCount']); [print(' ',o) for o in d['ovf']]
print('lastRow',d['lastRow']); print('svg',d['svg'])
for h in d['hdr']: print(h)
