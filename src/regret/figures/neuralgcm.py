"""NeuralGCM add-on figure: mean fuel regret vs lead for five sources, 12-hourly planning (SPEC 1.5)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from regret.figures.lead_regret import build_lead_regret

FIG_ID = "fig-neuralgcm"

_HEIGHT_PX = 900
_MARGIN = dict(l=90, r=40, t=90, b=210)
_ROW1 = (0.43, 1.0)  # forecast sources: 0.57 of the 600 px plot area, about 340 px
_ROW2 = (0.0, 0.33)  # persistence baseline


def _hover_with_ci(fig: go.Figure) -> None:
    """Each line's hover text: source and ``mean [lo, hi] kg``. The CI band drawn just before a line
    holds its hi values then its lo values reversed, so the bounds are read from it."""
    data = list(fig.data)
    for band, line in zip(data[::2], data[1::2]):
        n = len(line.x)
        hi, lo = list(band.y[:n]), list(band.y[n:])[::-1]
        line.customdata = list(zip(lo, hi))
        line.hovertemplate = f"{line.name}: %{{y:.1f}} [%{{customdata[0]:.1f}}, %{{customdata[1]:.1f}}] kg<extra></extra>"


def build_neuralgcm(df: pd.DataFrame) -> go.Figure:
    """The lead-time layout of the core figure (persistence on its own row, shared y per row,
    ticks at the leads, horizontal legend, CI annotation) for the add-on's sources, with a taller
    forecast row, zero-based regret axes and x-unified hover."""
    fig = build_lead_regret(df)
    n = df["flight_id"].nunique()
    _hover_with_ci(fig)
    fig.update_yaxes(rangemode="tozero")
    fig.update_yaxes(domain=list(_ROW1), row=1)
    fig.update_yaxes(domain=list(_ROW2), row=2)
    fig.update_layout(
        title=dict(text=f"{len(set(df['source']) - {'truth'})}-source comparison on {n} flights, 12-hourly planning",
                   x=0.5, xanchor="center"),
        height=_HEIGHT_PX, margin=_MARGIN, hovermode="x unified",
    )
    for a in fig.layout.annotations:
        if "90% CI" in a.text:  # five legend entries wrap on a narrow page: keep the CI note below them
            a.y = -0.30
        elif a.text == "Forecast sources":
            a.y = sum(_ROW1) / 2
        elif a.text == "Persistence baseline":
            a.y = sum(_ROW2) / 2
    return fig
