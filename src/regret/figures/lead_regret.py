"""Mean fuel regret vs lead time per forecast source, eastbound and westbound (CONTRACTS section 6)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from regret import stats
from regret.figures import style
from regret.figures.headline import SOURCE_LABELS

FIG_ID = "fig-lead-regret"

_DIRECTIONS = ("eastbound", "westbound")


def _rgba(hex_colour: str, alpha: float) -> str:
    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


_BASELINE = "persistence"
_LEAD_TICKS = [12, 24, 48, 72, 120]
_HEIGHT_PX = 700


def build_lead_regret(df: pd.DataFrame) -> go.Figure:
    """Mean fuel regret (kg) vs lead time with a shaded 90% CI band.

    2 x 2 grid: columns are eastbound and westbound; the top row holds the forecast sources and the
    bottom row the persistence baseline, so its much larger regret does not squash the others (B5).
    Each row has one linear y-axis shared across its two columns.
    """
    agg = stats.aggregate(df, by=("source", "lead_h", "direction"))
    sources = list(dict.fromkeys(agg["source"]))
    fig = make_subplots(
        rows=2, cols=2, shared_xaxes=True, shared_yaxes="rows",
        column_titles=[d.capitalize() for d in _DIRECTIONS],
        row_titles=["Forecast sources", "Persistence baseline"],
        vertical_spacing=0.14,
    )
    for source in sources:
        row = 2 if source == _BASELINE else 1
        colour = style.colour(source)
        label = SOURCE_LABELS.get(source, source)
        for col, direction in enumerate(_DIRECTIONS, start=1):
            g = agg[(agg["source"] == source) & (agg["direction"] == direction)].sort_values("lead_h")
            if g.empty:
                continue
            x = g["lead_h"].tolist()
            fig.add_trace(
                go.Scatter(
                    x=x + x[::-1],
                    y=g["fuel_kg_ci_hi"].tolist() + g["fuel_kg_ci_lo"].tolist()[::-1],
                    fill="toself", fillcolor=_rgba(colour, 0.2), line=dict(width=0),
                    hoverinfo="skip", mode="lines", name=f"{label} 90% CI",
                    legendgroup=source, showlegend=False,
                ),
                row=row, col=col,
            )
            fig.add_trace(
                go.Scatter(
                    x=x, y=g["fuel_kg_mean"].tolist(), mode="lines+markers",
                    line=dict(color=colour), marker=dict(symbol=style.symbol(source), size=7, color=colour), name=label, legendgroup=source,
                    showlegend=(col == 1),
                    hovertemplate=f"{label}<br>lead time %{{x}} h<br>mean fuel regret %{{y:.1f}} kg<extra></extra>",
                ),
                row=row, col=col,
            )
    fig.add_annotation(  # a legend key for the bands would toggle nothing, so explain them in text
        text="Shaded bands: 90% CI of the mean", xref="paper", yref="paper", x=0.5, y=-0.24,
        xanchor="center", yanchor="top", showarrow=False, font=dict(size=12),
    )
    fig.update_xaxes(tickvals=_LEAD_TICKS)
    fig.update_xaxes(title_text="lead time (h)", row=2)
    fig.update_yaxes(title_text="mean fuel regret (kg)", col=1)
    fig.update_layout(height=_HEIGHT_PX, margin=dict(l=90, r=40, t=60, b=150),
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.17, yanchor="top"))
    return fig
