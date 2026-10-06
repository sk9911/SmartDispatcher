"""Ageostrophic fraction vs lead time, one line per forecast source (S2, CONTRACTS §6)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from regret.figures import style
from regret.figures.headline import SOURCE_LABELS

FIG_ID = "fig-geostrophic"
_REFERENCE = "era5"
_REF_LABEL = "ERA5 (reference)"


_PAD = 0.18


def _y_range(df: pd.DataFrame) -> list[float]:
    """Linear range over every line, ERA5 included, with proportional padding."""
    v = df["ageostrophic_fraction"]
    lo, hi = float(v.min()), float(v.max())
    pad = (hi - lo) * _PAD or 0.01
    return [round(lo - pad, 4), round(hi + pad, 4)]


def geostrophic_summary(df: pd.DataFrame) -> str:
    """Caption sentences written from the results (never from fixed numbers)."""
    era5 = df[df["source"] == _REFERENCE]
    fc = df[df["source"] != _REFERENCE]
    level = float(era5["ageostrophic_fraction"].mean())
    gap = float((fc["ageostrophic_fraction"] - level).abs().max())
    above = fc[fc["ageostrophic_fraction"] >= level].sort_values("lead_h")
    text = (
        f"ERA5's ageostrophic fraction is about {level:.2f}. "
        f"The largest gap between any forecast source and ERA5 is {gap:.3f}; "
    )
    if above.empty:
        return text + (
            "all forecast sources are slightly more balanced (lower) than ERA5. "
            "Smoother fields are a possible explanation, not a finding; the sample is small "
            "and nothing here was tested for it."
        )
    parts = [f"{SOURCE_LABELS.get(r.source, r.source)} at {int(r.lead_h)} h" for r in above.itertuples()]
    verb = "sits" if len(parts) == 1 else "sit"
    return f"{text[:-2]}. {' and '.join(parts) if len(parts) < 3 else ', '.join(parts)} {verb} just above ERA5."


def build_geostrophic(df: pd.DataFrame) -> go.Figure:
    """df columns: source, lead_h, ageostrophic_fraction, n_fields (``era5`` rows are the reference)."""
    leads = sorted(int(x) for x in df["lead_h"].unique())
    fig = go.Figure()
    for source in [s for s in dict.fromkeys(df["source"]) if s != _REFERENCE]:
        d = df[df["source"] == source].sort_values("lead_h")
        fig.add_trace(
            go.Scatter(
                x=d["lead_h"], y=d["ageostrophic_fraction"], mode="lines+markers",
                name=SOURCE_LABELS.get(source, source),
                line=dict(color=style.colour(source), width=2),
                marker=dict(symbol=style.symbol(source), size=9),
                hovertemplate="%{fullData.name}: %{y:.3f}<extra></extra>",
            )
        )
    ref = df[df["source"] == _REFERENCE].sort_values("lead_h")
    if len(ref):
        # ERA5 at the same valid times: a flat-ish reference, drawn dashed across the leads
        fig.add_trace(
            go.Scatter(
                x=ref["lead_h"], y=ref["ageostrophic_fraction"], mode="lines", name=_REF_LABEL,
                line=dict(color="#333333", width=2, dash="dash"),
                hovertemplate="%{fullData.name}: %{y:.3f}<extra></extra>",
            )
        )
    fig.update_layout(
        title=dict(text="Ageostrophic fraction at 250 hPa, 30–70°N, by lead time", x=0.0, xanchor="left"),
        height=520,
        margin=dict(l=70, r=20, t=70, b=130),
        xaxis=dict(title=dict(text="lead time (h)"), tickmode="array", tickvals=leads, ticktext=[str(l) for l in leads]),
        yaxis=dict(
            title=dict(text="ageostrophic fraction (axis does not start at 0)"),
            type="linear",
            range=_y_range(df),
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0.0),
        template="plotly_white",
    )
    return fig
