import pandas as pd
for p in ("data/results/regret.parquet", "tests/fixture_results/regret.parquet"):
    df = pd.read_parquet(p)
    print("==", p, len(df), "rows; truth-optimised", int(df.is_truth_optimised.sum()))
    print(df.groupby("direction")["time_min"].describe()[["count","min","50%","mean","max"]].round(2))
    for c in ("fuel_flow_min_kgh","fuel_flow_max_kgh"):
        print(c, df[c].describe()[["min","25%","50%","75%","max"]].round(1).to_dict())
    fc = df[~df.is_truth_optimised]
    g = fc.groupby("source", sort=False)["optimiser_gap_fuel_kg"]
    print("gap count", g.count().to_dict(), "total", int(g.count().sum()))
    print("gap mean", g.mean().round(1).to_dict())
    print("gap values", {s: sorted(v.dropna().round(1).tolist()) for s, v in g})
    print("truth rows gap non-null:", int(df[df.is_truth_optimised].optimiser_gap_fuel_kg.notna().sum()))
    if "trip_fuel_kg" in df: print(df.groupby("direction")["trip_fuel_kg"].describe()[["min","50%","max"]].round(0))
print(list(df.columns))
