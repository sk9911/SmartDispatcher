"""One colour and marker symbol per forecast source, shared by every figure (B6)."""
from __future__ import annotations

SOURCE_COLOURS = {
    "hres": "#1f77b4",
    "graphcast": "#2ca02c",
    "pangu": "#9467bd",
    "persistence": "#7f7f7f",
    "neuralgcm": "#17becf",
}
FALLBACK = "#8c564b"

SOURCE_SYMBOLS = {
    "hres": "circle",
    "graphcast": "diamond",
    "pangu": "square",
    "persistence": "x",
    "neuralgcm": "triangle-up",
}
FALLBACK_SYMBOL = "star"


def colour(source: str) -> str:
    return SOURCE_COLOURS.get(source, FALLBACK)


def symbol(source: str) -> str:
    return SOURCE_SYMBOLS.get(source, FALLBACK_SYMBOL)
