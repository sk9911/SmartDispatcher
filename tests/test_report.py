"""Report export (CONTRACTS 2.13) on a tiny notebook that shows one Plotly figure."""

import re

import nbformat
import pytest

from regret.config import get_config
from regret.report import export

FIG_ID = "fig-tiny"
INPUT_MARKER = "SECRET_INPUT_MARKER"

CELLS = [
    f"""import os
# {INPUT_MARKER}
print("mode=" + os.environ["REGRET_CONFIG"])""",
    f"""import plotly.graph_objects as go
from IPython.display import HTML, display
import plotly.offline as po
po.init_notebook_mode(connected=False)
fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
display(HTML(fig.to_html(div_id="{FIG_ID}", full_html=False, include_plotlyjs=False)))""",
]


@pytest.fixture(scope="module")
def html(tmp_path_factory):
    d = tmp_path_factory.mktemp("report")
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(c) for c in CELLS])
    nb_path = d / "tiny.ipynb"
    nbformat.write(nb, nb_path)
    out = export(get_config("fixture"), d / "sub" / "out.html", notebook=nb_path)
    assert out == d / "sub" / "out.html"
    return out.read_text(encoding="utf-8")


def test_kernel_gets_config_mode(html):
    assert "mode=fixture" in html


def test_no_input_cells(html):
    assert INPUT_MARKER not in html


def test_no_network_references(html):
    assert not re.findall(r'<script[^>]+src="https?:', html)
    assert not re.findall(r'<link[^>]+href="https?:', html)


def test_plotly_js_inline_exactly_once(html):
    assert len(re.findall(r"plotly\.js v\d", html)) == 1


def test_figure_div_id_present(html):
    assert f'id="{FIG_ID}"' in html


def test_page_title_is_forecast_regret(html):
    assert "<title>Forecast Regret</title>" in html
