import sys, pandas as pd
base = sys.argv[1]
r = pd.read_parquet(f'{base}/neuralgcm_regret.parquet')
s = pd.read_parquet(f'{base}/neuralgcm_sensitivity.parquet')
e = pd.read_parquet(f'{base}/ensemble_regret.parquet')
f = r[r.source != 'truth']
print('flights', r.flight_id.nunique(), 'sources', sorted(f.source.unique()), 'leads', sorted(f.lead_h.unique()))
print('min departure', r.departure_time.min(), 'regret>=0', (f.regret_fuel_kg >= 0).all())
m = f.groupby(['source', 'lead_h']).regret_fuel_kg.mean().unstack()
print(m.round(2).to_string())
short = f[f.lead_h.isin([12, 24])].groupby('source').regret_fuel_kg.mean().sort_values()
print('pooled 12-24 h:\n', short.round(2).to_string())
nop = short.drop('persistence', errors='ignore'); print('rank (excl. persistence):', list(nop.index).index('neuralgcm') + 1, 'of', len(nop))
l120 = m[120].sort_values(); print('120 h:\n', l120.round(2).to_string())
nop = l120.drop('persistence', errors='ignore'); print('rank 120 (excl. persistence):', list(nop.index).index('neuralgcm') + 1, 'of', len(nop))
s['d'] = s.regret_12h_kg - s.regret_6h_kg
print('sensitivity sources', sorted(s.source.unique()), 'n', s.n.unique())
ss = s[s.lead_h.isin([12, 24])]
print('12h-6h diff mean at 12-24 h, all sens sources: %.2f' % ss.d.mean())
print('excl persistence: %.2f' % ss[ss.source != 'persistence'].d.mean())
print(ss.groupby('source').d.mean().round(2).to_string())
print('per lead diff:\n', s.pivot(index='source', columns='lead_h', values='d').round(1).to_string())
print('core vs core_set max abs diff', (s.regret_12h_kg - s.regret_12h_core_set_kg).abs().max())
print('ensemble members', e.members.unique(), 'rows', len(e), 'beats', e.beats_hindsight.sum(), 'regret>=0', (e.regret_fuel_kg >= 0).all())
print(e.groupby(['choice', 'lead_h']).regret_fuel_kg.mean().unstack().round(2).to_string())
# floor check: regret == cost - min(hindsight cost, own)
h = r[r.is_hindsight].set_index('flight_id').fuel_kg
ee = e.join(h.rename('hind'), on='flight_id')
calc = (ee.fuel_kg - ee[['hind', 'fuel_kg']].min(axis=1))
print('floor max abs diff', (calc - ee.regret_fuel_kg).abs().max(), 'zero rows', (ee.regret_fuel_kg == 0).sum())
# R3: displayed values and gaps from rounded values
for lab, sel in [('12-24', f[f.lead_h.isin([12, 24])]), ('120', f[f.lead_h == 120])]:
    mm = sel[sel.source != 'persistence'].groupby('source').regret_fuel_kg.mean().sort_values()
    best = mm.index[0]; n = mm['neuralgcm']
    print(f'{lab}: neuralgcm {n:.2f} -> {round(n)}; best {best} {mm[best]:.2f} -> {round(mm[best])}; stated-gap rule round(a)-round(b) = {round(n) - round(mm[best])}; raw gap {n - mm[best]:.2f}; rank {list(mm.index).index("neuralgcm") + 1} of {len(mm)}')
print('sensitivity sources excl. persistence, in file order:', list(dict.fromkeys(s[s.source != "persistence"].source)))
