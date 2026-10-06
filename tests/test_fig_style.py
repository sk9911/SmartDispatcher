"""Shared source colours and symbols across figures (B6)."""
from __future__ import annotations

import pandas as pd
import pytest

from regret.config import get_config
from regret.figures import style
from regret.figures.lead_regret import build_lead_regret
from regret.figures.sanity import build_sanity
from regret.figures.showcase_map import build_showcase_map
from regret.figures.wind_error import build_wind_error

OLD_MAP_COLOURS = {
    "hres": "#1f77b4", "graphcast": "#2ca02c", "pangu": "#9467bd",
    "persistence": "#7f7f7f", "neuralgcm": "#17becf",
}


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_parquet("tests/fixture_results/regret.parquet")


def test_colours_equal_old_showcase_map_values():
    for s, c in OLD_MAP_COLOURS.items():
        assert style.SOURCE_COLOURS[s] == c
        assert style.colour(s) == c
    assert style.colour("unknown-source") == style.FALLBACK == "#8c564b"


def test_symbols_distinct_per_source():
    syms = [style.symbol(s) for s in OLD_MAP_COLOURS]
    assert len(set(syms)) == len(syms)
    assert style.symbol("unknown-source")


def _colour_of(t):
    if t.type == "scattergeo":
        return t.line.color
    if t.type == "scatter" and t.mode == "markers" and t.marker.color is not None:
        return t.marker.color
    return t.line.color


def test_wind_error_uses_style(df):
    fig = build_wind_error(df)
    sources = {t.meta for t in fig.data}
    assert sources and sources <= set(df.source)
    for t in fig.data:
        assert t.marker.color == style.colour(t.meta)
        assert t.marker.symbol == style.symbol(t.meta)


def test_lead_regret_uses_style(df):
    fig = build_lead_regret(df)
    seen = set()
    for t in fig.data:
        if t.fill == "toself" or t.legendgroup not in set(df.source):
            continue
        assert t.line.color == style.colour(t.legendgroup)
        assert t.marker.symbol == style.symbol(t.legendgroup)
        seen.add(t.legendgroup)
    assert seen == set(df[~df.is_truth_optimised].source)


def test_sanity_bars_use_style(df):
    fig = build_sanity(df)
    bars = [t for t in fig.data if t.type == "bar"]
    assert bars
    for t in bars:
        assert list(t.marker.color) == [style.colour(s) for s in t.x]


def test_showcase_map_colours_unchanged():
    fig = build_showcase_map(get_config("fixture"))
    plans = [t for t in fig.data if t.meta and t.meta.get("kind") == "plan" and t.line.dash != "dot"]
    assert plans
    for t in plans:
        assert t.line.color == OLD_MAP_COLOURS.get(t.meta["source"], "#8c564b")
