import nbformat as nbf
ROOT = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher'
nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_code_cell(
        "import os\nimport regret.offline\nregret.offline.install_if_requested()\n"
        f"os.chdir({ROOT!r})  # repo root\nprint(os.getcwd())"),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "from regret.figures.sanity import build_sanity, FIG_ID\n"
        "fx = pd.read_parquet('tests/fixture_results/regret.parquet')\n"
        "fig = build_sanity(fx)\n"
        "fig.show()\n"
        "print('fixture rows', len(fx))\n"),
    nbf.v4.new_code_cell(
        "df = pd.read_parquet('data/results/regret.parquet')\n"
        "full = build_sanity(df)\n"
        "full.show()\n"
        "full.write_html('qa/T27/scratch/fig.html', include_plotlyjs=True, div_id=FIG_ID)\n"
        "print('full rows', len(df), '; wrote qa/T27/scratch/fig.html')\n"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/T27/scratch/check.ipynb")
