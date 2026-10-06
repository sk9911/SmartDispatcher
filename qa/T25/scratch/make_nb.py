import nbformat as nbf
ROOT = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher'
nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_code_cell(
        "import os\nimport regret.offline\nregret.offline.install_if_requested()\n"
        f"os.chdir({ROOT!r})  # repo root\nprint(os.getcwd())"),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "from regret.figures.wind_error import build_wind_error, FIG_ID\n"
        "df = pd.read_parquet('tests/fixture_results/regret.parquet')\n"
        "fig = build_wind_error(df)\n"
        "fig.show()\n"
        "fc = df[~df['is_truth_optimised']]\n"
        "print('forecast_plan_rows', len(fc))\n"
        "print('rows_per_source', fc.groupby('source', sort=False).size().to_dict())\n"
        "print('traces', [(t.name, len(t.x)) for t in fig.data])\n"
        "print('wind_error range', fc['wind_error_ms'].min(), fc['wind_error_ms'].max())\n"
        "print('regret range', fc['regret_fuel_kg'].min(), fc['regret_fuel_kg'].max())\n"
        "print(fc.groupby('source', sort=False)[['wind_error_ms','regret_fuel_kg']].describe().T.to_string())\n"
        "print('nan wind_error', int(fc['wind_error_ms'].isna().sum()), 'nan regret', int(fc['regret_fuel_kg'].isna().sum()))\n"
        "fig.write_html('qa/T25/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)\n"
        "print('wrote fig.html')\n"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/T25/scratch/check.ipynb")
