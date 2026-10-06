"""Report export: execute the report notebook and write self-contained HTML (CONTRACTS 2.13)."""

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from regret.config import Config, get_config
from regret.offline import ENV_VAR

DEFAULT_NOTEBOOK = Path("notebooks/regret_report.ipynb")
CELL_TIMEOUT_S = 600
REPORT_TITLE = "Forecast Regret"


def export(cfg: Config, out_path: Path, *, notebook: Path | None = None) -> Path:
    notebook = Path(notebook) if notebook is not None else DEFAULT_NOTEBOOK
    out_path = Path(out_path)
    nb = nbformat.read(notebook, as_version=4)

    env = {"REGRET_CONFIG": cfg.mode}
    if ENV_VAR in os.environ:
        env[ENV_VAR] = os.environ[ENV_VAR]
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)  # the kernel inherits this process's environment
    try:
        NotebookClient(
            nb, timeout=CELL_TIMEOUT_S, kernel_name="python3",
            resources={"metadata": {"path": str(notebook.resolve().parent)}},
        ).execute()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    exporter = HTMLExporter(
        exclude_input=True, exclude_input_prompt=True, exclude_output_prompt=True,
        require_js_url="", mathjax_url="",  # no CDN scripts: the report must work offline
    )
    nb.metadata["title"] = REPORT_TITLE  # the exporter uses it for <title>
    body, _ = exporter.from_notebook_node(nb)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return out_path


def main(argv=None) -> int:
    import argparse

    argparse.ArgumentParser(
        prog="regret report", description="Execute the report notebook and write the HTML report."
    ).parse_args(argv)
    cfg = get_config()
    export(cfg, cfg.report_path)
    return 0
