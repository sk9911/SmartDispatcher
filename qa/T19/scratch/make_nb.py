import nbformat as nbf
nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_code_cell("import regret.offline\nregret.offline.install_if_requested()"),
    nbf.v4.new_code_cell(
        "import os\n"
        "os.chdir('/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher')  # repo root\n"
        "import pandas as pd\n"
        "from regret.figures.headline import build_headline, FIG_ID\n"
        "df = pd.read_parquet('tests/fixture_results/regret.parquet')\n"
        "fig = build_headline(df)\n"
        "fig.show()\n"
        "print(f\"n_groups={df[['source', 'lead_h']].drop_duplicates().shape[0]}\")\n"
        "print(f\"n_forecast_groups={df.loc[~df['is_truth_optimised'], ['source', 'lead_h']].drop_duplicates().shape[0]}\")\n"
        "fig.write_html('qa/T19/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)\n"
    ),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/T19/scratch/check.ipynb")
