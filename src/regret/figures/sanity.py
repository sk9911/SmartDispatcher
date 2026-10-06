"""Sanity panel: replay time, fuel-flow range, optimiser gap (SPEC §5.2, CONTRACTS §6)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from regret.figures import style
from regret.figures.headline import SOURCE_LABELS

FIG_ID = "fig-sanity"
HEIGHT_PX = 780
# Direction and min/max boxes are not sources: neutral greys, none of style.SOURCE_COLOURS.
_NEUTRAL = {
    "eastbound": "#4d4d4d",
    "westbound": "#a6a6a6",
    "minimum fuel flow": "#4d4d4d",
    "maximum fuel flow": "#a6a6a6",
}


def build_sanity(df: pd.DataFrame) -> go.Figure:
    """Four subplots over all replayed plans (truth-optimised rows included)."""
    fig = make_subplots(
        rows=2,
        cols=2,
        vertical_spacing=0.2,
        horizontal_spacing=0.12,
        subplot_titles=(
            "replay time by direction",
            "fuel-flow range",
            "optimiser-gap count",
            "optimiser-gap size",
        ),
    )
    for direction in ("eastbound", "westbound"):
        fig.add_trace(
            go.Box(
                y=df.loc[df["direction"] == direction, "time_min"],
                name=direction,
                boxmean=True,
                marker_color=_NEUTRAL[direction],
                line_color=_NEUTRAL[direction],
                hovertemplate="%{y:.1f} min<extra>" + direction + "</extra>",
            ),
            row=1,
            col=1,
        )
    for name, col in (
        ("minimum fuel flow", "fuel_flow_min_kgh"),
        ("maximum fuel flow", "fuel_flow_max_kgh"),
    ):
        fig.add_trace(
            go.Box(
                y=df[col],
                name=name,
                boxmean=True,
                marker_color=_NEUTRAL[name],
                line_color=_NEUTRAL[name],
                hovertemplate="%{y:,.0f} kg/h<extra>" + name + "</extra>",
            ),
            row=1,
            col=2,
        )

    forecast = df[~df["is_truth_optimised"]]
    sources = list(dict.fromkeys(forecast["source"]))
    gaps = forecast.groupby("source")["optimiser_gap_fuel_kg"]
    counts = gaps.count().reindex(sources).astype(int)
    means = gaps.mean().reindex(sources)
    fig.add_trace(
        go.Bar(x=sources, y=counts, name="optimiser-gap count", showlegend=False,
               marker_color=[style.colour(s) for s in sources]),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=sources, y=means, name="optimiser-gap size", showlegend=False,
               text=[f"n={n}" for n in counts], textposition="outside", cliponaxis=False,
               marker_color=[style.colour(s) for s in sources]),
        row=2,
        col=2,
    )
    fig.update_yaxes(title_text="replay time (min)", row=1, col=1)
    fig.update_yaxes(title_text="fuel flow (kg/h)", row=1, col=2)
    fig.update_yaxes(title_text="gap count (plans)", dtick=1, tick0=0, row=2, col=1)  # whole plans only
    fig.update_yaxes(title_text="mean gap size (kg)", row=2, col=2)
    labels = [SOURCE_LABELS.get(str(s), str(s)).replace(" ", "<br>", 1).replace("-", "-<br>", 1)
              if len(SOURCE_LABELS.get(str(s), str(s))) > 9 else SOURCE_LABELS.get(str(s), str(s))
              for s in sources]
    for col in (1, 2):  # x stays the source id (colour lookup); tick text shows the label
        fig.update_xaxes(title_text="forecast source", tickmode="array", tickvals=sources, ticktext=labels,
                         row=2, col=col)
    fig.update_xaxes(tickangle=0, row=2)
    fig.update_yaxes(automargin=True)
    for src, n in counts.items():  # zero gaps are a result, not missing data
        if n == 0:
            for col in (1, 2):
                fig.add_annotation(x=src, y=0, text="0 gaps", showarrow=False, yshift=12,
                                   xref=f"x{2 + col}",
                                   yref=f"y{2 + col}")
    fig.add_annotation(
        text="max equal for all plans: same initial mass",
        xref="x2 domain", yref="y2 domain", x=0.5, y=0.5, showarrow=False,
        font=dict(size=11, color="#555555"),
    )
    fig.update_layout(showlegend=False, height=HEIGHT_PX, margin=dict(l=80, r=30, t=50, b=80))
    return fig
