import nbformat as nbf
ROOT = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher'
nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_code_cell(
        "import os\nimport regret.offline\nregret.offline.install_if_requested()\n"
        f"os.chdir({ROOT!r})  # repo root\nprint(os.getcwd())"),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "from regret.figures.lead_regret import build_lead_regret, FIG_ID\n"
        "df = pd.read_parquet('tests/fixture_results/regret.parquet')\n"
        "fig = build_lead_regret(df)\n"
        "fig.show()\n"
        "print('n_traces', len(fig.data))\n"
        "print('traces', [(t.name, t.legendgroup, t.xaxis, t.yaxis, t.showlegend) for t in fig.data])\n"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/B5/scratch/check.ipynb")
