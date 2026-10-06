import sys, pandas as pd
D = sys.argv[1]
a = pd.read_parquet(f"{D}/data/results/regret.parquet")
b = pd.read_parquet("data/results/regret.parquet")
k = ["flight_id", "source", "lead_h"]
print("cols", list(a.columns))
print("shape clone", a.shape, "wt", b.shape)
a2 = a.sort_values(k, na_position="first").reset_index(drop=True)
b2 = b.sort_values(k, na_position="first").reset_index(drop=True)
pd.testing.assert_frame_equal(a2, b2)
print("assert_frame_equal: OK")
print("flights", a.flight_id.nunique())
print(a.groupby("source", dropna=False).lead_h.agg(lambda s: sorted(s.dropna().unique().tolist())).to_string())
print(a.groupby("source", dropna=False).size().to_string())
reg = [c for c in a.columns if "regret" in c]
print("regret cols", reg, "NaN:", int(a[reg].isna().sum().sum()), "min:", a[reg].min().to_dict())
