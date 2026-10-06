import json, re, sys
terms = []
for line in open('CONTEXT.md'):
    if line.startswith('_Avoid_:'):
        terms += [t.strip() for t in re.sub(r'\(.*?\)', '', line.split(':', 1)[1]).split(',')]
d = json.load(open(sys.argv[1]))
print('terms:', terms)
for key in ['s78', 'all']:
    t = d[key]
    print(f'== {key}: {len(t)} chars')
    for term in terms:
        pat = r'\b' + re.escape(term) + r's?\b'
        hits = [t[max(0, m.start()-50):m.end()+40].replace('\n', ' ') for m in re.finditer(pat, t, re.I)]
        if hits: print(f'  {term!r}: {len(hits)}'); [print('     ...' + h + '...') for h in hits[:6]]
    for stem in ['penal', 'rmse', 'optimal', 'oracle']:
        n = len(re.findall(stem, t, re.I))
        if n: print(f'  stem {stem!r}: {n}', [t[max(0,m.start()-40):m.end()+30].replace('\n',' ') for m in re.finditer(stem, t, re.I)][:4])
