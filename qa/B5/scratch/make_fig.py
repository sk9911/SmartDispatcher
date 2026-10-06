import pandas as pd
from regret import stats
from regret.figures.lead_regret import build_lead_regret, FIG_ID
df = pd.read_parquet('data/results/regret.parquet')
print('rows', len(df))
fig = build_lead_regret(df)
print('n_traces', len(fig.data))
for t in fig.data:
    print(t.name, t.legendgroup, t.xaxis, t.yaxis, t.showlegend)
agg = stats.aggregate(df, by=('source', 'lead_h', 'direction'))
print(agg[['source','direction','lead_h','fuel_kg_mean','fuel_kg_ci_lo','fuel_kg_ci_hi']].to_string())
fig.write_html('qa/B5/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)
print('wrote')
