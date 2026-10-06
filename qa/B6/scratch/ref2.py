import numpy as np, pandas as pd
from regret.figures.wind_error import build_wind_error, _bin_edges, _y_range
df = pd.read_parquet('data/results/regret.parquet')
fc = df[~df.is_truth_optimised]
fig = build_wind_error(df)
for t in fig.data: print(repr(t.name), t.xaxis, len(t.x))
f = fc[fc.source!='persistence']; p = fc[fc.source=='persistence']
print('edges', np.round(_bin_edges(f.wind_error_ms),2))
for name, pan in (('fc',f),('pers',p)):
    lo,top=_y_range(pan.regret_fuel_kg); ab=pan[pan.regret_fuel_kg>top]
    print(name,'range',round(lo,1),round(top,1),'above',len(ab),'max',ab.regret_fuel_kg.max(), ab.groupby('source').size().to_dict())
for t in fig.data:
    if 'median' in (t.name or ''): print(t.name, [round(v,1) for v in t.x], [round(v,1) for v in t.y])
print([a.text for a in fig.layout.annotations])
r = f.sort_values('regret_fuel_kg').iloc[-1]; print(r[['flight_id','source','lead_h','wind_error_ms','regret_fuel_kg']].to_dict())
