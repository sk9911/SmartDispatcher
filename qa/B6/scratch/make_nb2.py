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
        "print('traces', [(t.name, len(t.x)) for t in fig.data])\n"
        "fig.write_html('qa/B6/scratch/wind2.html', include_plotlyjs=True, div_id=FIG_ID)\n"
        "print('wrote wind2.html')\n"),
    nbf.v4.new_code_cell(
        "from regret.figures.lead_regret import build_lead_regret, FIG_ID as LID\n"
        "from regret.figures.sanity import build_sanity, FIG_ID as SID\n"
        "lfig = build_lead_regret(df)\n"
        "lfig.show()\n"
        "lfig.write_html('qa/B6/scratch/lead2.html', include_plotlyjs=True, div_id=LID)\n"
        "sfig = build_sanity(df)\n"
        "sfig.write_html('qa/B6/scratch/sanity2.html', include_plotlyjs=True, div_id=SID)\n"
        "print('wrote lead2.html sanity2.html')\n"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/B6/scratch/check2.ipynb")
