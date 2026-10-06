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
        "df = pd.read_parquet('data/results/regret.parquet')\n"
        "fig = build_wind_error(df)\n"
        "fig.show()\n"
        "fig.write_html('qa/B6/scratch/wind-final.html', include_plotlyjs=True, div_id=FIG_ID)\n"
        "print('wrote wind-final.html', len(df))\n"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/B6/scratch/check-final.ipynb")
