"""Ensemble robust plan figure: mean fuel regret vs lead for the robust choices, with context (SPEC 1.3)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from regret import stats
from regret.figures import style
from regret.figures.headline import SOURCE_LABELS
from regret.figures.lead_regret import _rgba

FIG_ID = "fig-ensemble"

_HEIGHT_PX = 520
_LEAD_FALLBACK = [12, 24, 48, 72, 120]
_CHOICE_STYLE = {  # neutral, distinct from the source colours
    "mean_robust": ("Mean-robust plan", "#d62728", "star"),
    "p90_robust": ("p90-robust plan", "#ff7f0e", "pentagon"),
}


def _series(values_by_lead: dict[int, list[float]]) -> pd.DataFrame:
    rows = []
    for lead, v in sorted(values_by_lead.items()):
        lo, hi = stats.bootstrap_mean_ci(v)
        rows.append({"lead_h": lead, "mean": sum(v) / len(v), "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def _addon_series(addon_df: pd.DataFrame, source: str) -> pd.DataFrame:
    g = addon_df[(addon_df["source"] == source) & ~addon_df["is_truth_optimised"]]
    return _series({int(k): v["regret_fuel_kg"].tolist() for k, v in g.groupby("lead_h")})


def _best_core(addon_df: pd.DataFrame) -> str:
    core = addon_df[~addon_df["is_truth_optimised"] & ~addon_df["source"].isin(["neuralgcm", "persistence"])]
    return core.groupby("source")["regret_fuel_kg"].mean().idxmin()


def build_ensemble(df: pd.DataFrame, addon_df: pd.DataFrame) -> go.Figure:
    """Mean floored fuel regret (kg) vs lead for the mean- and p90-robust plans, beside the add-on's
    NeuralGCM deterministic plan and the best core source, with shaded 90% CIs."""
    members = int(df["members"].iloc[0])
    n = df["flight_id"].nunique()
    best = _best_core(addon_df)
    lines = []
    for choice in ("mean_robust", "p90_robust"):
        name, colour, symbol = _CHOICE_STYLE[choice]
        g = df[df["choice"] == choice]
        s = _series({int(k): v["regret_fuel_kg"].tolist() for k, v in g.groupby("lead_h")})
        lines.append((name, colour, symbol, s, "solid"))
    for source in ("neuralgcm", best):
        lines.append((SOURCE_LABELS.get(source, source), style.colour(source), style.symbol(source),
                      _addon_series(addon_df, source), "dash"))
    fig = go.Figure()
    for name, colour, symbol, s, dash in lines:
        x = s["lead_h"].tolist()
        fig.add_trace(go.Scatter(
            x=x + x[::-1], y=s["hi"].tolist() + s["lo"].tolist()[::-1], fill="toself",
            fillcolor=_rgba(colour, 0.15), line=dict(width=0), hoverinfo="skip", mode="lines",
            name=f"{name} 90% CI", legendgroup=name, showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=x, y=s["mean"].tolist(), mode="lines+markers", name=name, legendgroup=name,
            line=dict(color=colour, dash=dash), marker=dict(symbol=symbol, size=8, color=colour),
            customdata=list(zip(s["lo"], s["hi"])),
            hovertemplate=f"{name}: %{{y:.1f}} [%{{customdata[0]:.1f}}, %{{customdata[1]:.1f}}] kg<extra></extra>",
        ))
    ticks = sorted(set(df["lead_h"])) or _LEAD_FALLBACK
    fig.add_annotation(
        text="Shaded bands: 90% CI of the mean. Regret is floored at 0 against the NeuralGCM add-on hindsight plan.",
        xref="paper", yref="paper", x=0.5, y=-0.36, xanchor="center", yanchor="top",
        showarrow=False, font=dict(size=12),
    )
    fig.update_xaxes(tickvals=ticks, title_text="lead time (h)")
    fig.update_yaxes(title_text="mean fuel regret (kg)", rangemode="tozero")
    fig.update_layout(
        title=dict(text=f"Ensemble robust plans (M = {members} members), {n} flights, 12-hourly planning",
                   x=0.5, xanchor="center"),
        hovermode="x unified", height=_HEIGHT_PX, margin=dict(l=90, r=40, t=80, b=170),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.2, yanchor="top"),
    )
    return fig
