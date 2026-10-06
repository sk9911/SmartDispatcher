import nbformat as nbf
ROOT = '/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher'
nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_code_cell(
        "import os\nimport regret.offline\nregret.offline.install_if_requested()\n"
        f"os.chdir({ROOT!r})  # repo root\n"
        "from IPython.display import HTML, display\n"
        "from regret.figures import showcase_map\n"
        "display(HTML(showcase_map.geo_assets_html()))\nprint(os.getcwd())"),
    nbf.v4.new_code_cell(
        "from regret.config import get_config\n"
        "from regret.figures.showcase_map import build_showcase_map, FIG_ID\n"
        "fig = build_showcase_map(get_config('fixture'))\n"
        "fig.show()\n"
        "showcase_map.write_html(fig, 'qa/B7/scratch/fig.html')\n"
        "print('n_traces', len(fig.data))\n"
        "print([(i, t.name, t.meta) for i, t in enumerate(fig.data)])\n"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "qa/B7/scratch/check.ipynb")
