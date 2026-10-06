import sys, itertools, pandas as pd
base, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
scale = 172 / (hi - lo)
r = pd.read_parquet(f'{base}/neuralgcm_regret.parquet')
f = r[(r.source != 'truth') & (r.source != 'persistence')]
m = f.groupby(['direction', 'lead_h', 'source']).regret_fuel_kg.mean()
print(f'scale {scale:.3f} px/kg; 9 px = {9/scale:.1f} kg')
for (d, l), g in m.groupby(level=[0, 1]):
    v = g.droplevel([0, 1])
    pairs = sorted(((abs(v[a]-v[b]), a, b) for a, b in itertools.combinations(v.index, 2)))
    under = [f'{a}-{b} {dk:.1f} kg/{dk*scale:.1f} px' for dk, a, b in pairs if dk*scale < 9]
    print(d[:4], l, f'values {dict(v.round(1))}', '| <9px:', len(under), '| scale-crushed (>=3 kg):', [u for u in under if float(u.split()[1]) >= 3])
