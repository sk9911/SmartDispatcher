import json, re, sys
terms = []
for line in open('CONTEXT.md'):
    if line.startswith('_Avoid_:'):
        terms += [t.strip() for t in re.sub(r'\(.*?\)', '', line.split(':', 1)[1]).split(',')]
print('terms:', terms)
for f in sys.argv[1:]:
    d = json.load(open(f)); t = d['text']
    print(f'== {f}: {d["h6"]!r} .. {d["h9"]!r}, {len(t)} chars')
    print('  phrase count:', t.count('of the 4 forecast sources other than the persistence baseline'))
    print('  "forecast models":', len(re.findall(r'forecast models', t)))
    for term in terms + ['penal']:
        pat = r'\b' + re.escape(term) + (r'\w*' if term == 'penal' else r's?\b')
        hits = [t[max(0, m.start()-50):m.end()+40].replace('\n', ' ') for m in re.finditer(pat, t, re.I)]
        if hits:
            print(f'  {term!r}: {len(hits)}'); [print('     ...' + h + '...') for h in hits]
