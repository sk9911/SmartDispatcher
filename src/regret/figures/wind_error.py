"""Wind error vs fuel regret scatter (SPEC §4.5, CONTRACTS §6)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from regret.figures import style
from regret.figures.headline import SOURCE_LABELS

FIG_ID = "fig-wind-error"

_BASELINE = "persistence"
_MAX_BINS = 8
_MIN_BINS = 2
_MIN_BIN_POINTS = 15
_FLOOR_BIN_POINTS = 5
_CAP_PERCENTILE = 99
_HEADROOM = 1.08
_ANNOTATION_SHIFT = 26  # px above the subplot title baseline
_PIN_INSET = 0.04  # pinned markers sit this share of the axis height below the top edge

_HOVER = (
    "flight %{customdata[0]}<br>source %{customdata[1]}<br>"
    "lead (h) %{customdata[2]}<br>wind error %{x:.2f} m/s<br>"
    "fuel regret %{y:.1f} kg<extra></extra>"
)
_HOVER_PINNED = (
    "flight %{customdata[0]}<br>source %{customdata[1]}<br>"
    "lead (h) %{customdata[2]}<br>wind error %{x:.2f} m/s<br>"
    "true fuel regret %{customdata[3]:,.1f} kg (above the plotted range)<extra></extra>"
)
_HOVER_MEDIAN = (
    "%{fullData.name}<br>median wind error %{x:.2f} m/s<br>median fuel regret %{y:.1f} kg<extra></extra>"
)

_COLS = ["flight_id", "source", "lead_h"]


def _label(source: str) -> str:
    return SOURCE_LABELS.get(source, source)


def _customdata(rows: pd.DataFrame) -> list[list]:
    return [[r.flight_id, _label(str(r.source)), r.lead_h] for r in rows.itertuples()]


def _n_bins(panel: pd.DataFrame) -> int:
    """clamp(fewest plans of any forecast source // 15, 2, 8): the fixture's 30 plans give 2, the full 600 give 8."""
    fewest = int(panel["source"].value_counts().min())
    return int(min(_MAX_BINS, max(_MIN_BINS, fewest // _MIN_BIN_POINTS)))


def _min_bin_points(panel: pd.DataFrame, n_bins: int) -> int:
    """Fewest plans a source needs in a bin to draw its median: min(15, max(5, fewest per source // (2 * n_bins))).

    The fixture's 30 plans over 2 bins give 7; the full results give 15 (600 // 16 = 37, capped).
    """
    fewest = int(panel["source"].value_counts().min())
    return int(min(_MIN_BIN_POINTS, max(_FLOOR_BIN_POINTS, fewest // (2 * n_bins))))


def _bin_edges(pooled: pd.Series, n_bins: int) -> np.ndarray:
    """Interior edges of n_bins quantile bins of the pooled forecast wind error (deterministic)."""
    return np.unique(np.quantile(pooled.to_numpy(float), np.linspace(0, 1, n_bins + 1)))[1:-1]


def _y_range(regret: pd.Series) -> tuple[float, float]:
    top = float(np.percentile(regret, _CAP_PERCENTILE)) * _HEADROOM
    lo = min(0.0, float(regret.min()))
    if top <= lo:
        top = lo + 1.0
    return lo - 0.03 * (top - lo) if lo < 0 else -0.03 * top, top


def _annotation(n: int, top: float, peak: float, col: int) -> dict:
    plural = "plan" if n == 1 else "plans"
    return dict(
        text=f"{n} {plural} above {top:,.0f} kg shown at top edge<br>(max {peak:,.0f} kg)",
        # above the panel's subplot title, outside the plot area, so it never covers a plan
        xref=f"x{'' if col == 1 else col} domain", yref="paper",
        x=0, y=1, yshift=_ANNOTATION_SHIFT, xanchor="left", yanchor="bottom",
        showarrow=False, align="left", font=dict(size=11),
    )


def build_wind_error(df: pd.DataFrame) -> go.Figure:
    """Forecast-plan rows only. Forecast sources left, persistence right, each with its own linear axes.

    Persistence wind error is about 10x the forecast sources', so a shared axis would squash them (B6).
    Points are faint context; binned medians (common bins) carry the trend. Each panel's y-range is capped
    at a high percentile and every plan above it is pinned at the top edge with its true value (no plan hidden).
    """
    forecast = df[~df["is_truth_optimised"]]
    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.08,
        subplot_titles=("Forecast sources", "Persistence baseline"),
    )
    panels = {1: forecast[forecast["source"] != _BASELINE], 2: forecast[forecast["source"] == _BASELINE]}
    n_bins = _n_bins(panels[1]) if len(panels[1]) else _MIN_BINS
    edges = _bin_edges(panels[1]["wind_error_ms"], n_bins) if len(panels[1]) else np.array([])
    min_bin = _min_bin_points(panels[1], n_bins) if len(panels[1]) else _MIN_BIN_POINTS
    ranges: dict[int, tuple[float, float]] = {}
    for col, panel in panels.items():
        if len(panel):
            ranges[col] = _y_range(panel["regret_fuel_kg"])

    for source in forecast["source"].drop_duplicates():
        s = str(source)
        col = 2 if s == _BASELINE else 1
        rows = forecast[forecast["source"] == source]
        lo, top = ranges[col]
        pin_y = top - _PIN_INSET * (top - lo)
        inside = rows[rows["regret_fuel_kg"] <= top]
        above = rows[rows["regret_fuel_kg"] > top]
        marker = dict(color=style.colour(s), symbol=style.symbol(s))
        fig.add_trace(
            go.Scatter(
                x=inside["wind_error_ms"], y=inside["regret_fuel_kg"], mode="markers",
                name=_label(s), meta=s, legendgroup=s, showlegend=(col == 2),
                marker=dict(**marker, size=4, opacity=0.25),
                customdata=_customdata(inside), hovertemplate=_HOVER,
            ),
            row=1, col=col,
        )
        if col == 1:
            bins = np.clip(np.digitize(rows["wind_error_ms"].to_numpy(float), edges), 0, len(edges))
            med = [
                (float(g["wind_error_ms"].median()), float(g["regret_fuel_kg"].median()))
                for _, g in rows.groupby(bins) if len(g) >= min_bin
            ]
            # always added, so every forecast source has a legend entry even with no median points
            fig.add_trace(
                go.Scatter(
                    x=[m[0] for m in med], y=[m[1] for m in med], mode="lines+markers",
                    name=f"{_label(s)} (median)", meta=s, legendgroup=s,
                    line=dict(color=style.colour(s), width=3),
                    marker=dict(**marker, size=9, line=dict(color="white", width=1)),
                    hovertemplate=_HOVER_MEDIAN,
                ),
                row=1, col=1,
            )
        if len(above):
            fig.add_trace(
                go.Scatter(
                    x=above["wind_error_ms"], y=[pin_y] * len(above), mode="markers",
                    name=f"{_label(s)} (above range)", meta=s, legendgroup=s, showlegend=False,
                    cliponaxis=False,
                    marker=dict(**marker, size=9, opacity=1, line=dict(color="black", width=1.5)),
                    customdata=[c + [float(v)] for c, v in zip(_customdata(above), above["regret_fuel_kg"])],
                    hovertemplate=_HOVER_PINNED,
                ),
                row=1, col=col,
            )

    fig.update_xaxes(title_text="wind error (m/s)")
    fig.update_yaxes(title_text="fuel regret (kg)")
    for col, (lo, top) in ranges.items():
        fig.update_yaxes(range=[lo, top], row=1, col=col)
        above = panels[col][panels[col]["regret_fuel_kg"] > top]["regret_fuel_kg"]
        if len(above):
            fig.add_annotation(**_annotation(len(above), top, float(above.max()), col))
    fig.add_annotation(
        text=(f"Lines: binned median of each source ({n_bins} common wind-error bins; "
              f"a bin with fewer than {min_bin} plans of a source is left out); faint points: single plans"),
        xref="paper", yref="paper", x=0.5, y=-0.4, xanchor="center", yanchor="top",
        showarrow=False, font=dict(size=11),
    )
    fig.update_layout(
        title=dict(text="Wind error vs fuel regret, per forecast plan", y=0.98, yanchor="top"),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.2, yanchor="top"),
        height=635, margin=dict(t=125, b=170),
    )
    return fig
