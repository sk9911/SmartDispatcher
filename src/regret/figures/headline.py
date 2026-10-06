"""Headline table: regret per forecast source and lead time, flight directions pooled (CONTRACTS section 6)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from regret import stats

FIG_ID = "fig-headline"

# column stem -> (label, decimals shown): fixed decimals, never stripped
_METRICS = {
    "fuel_kg": ("Fuel (kg)", 1),
    "fuel_pct": ("Fuel (%)", 3),
    "time_min": ("Time (min)", 2),
    "co2_kg": ("CO\u2082 (kg)", 1),
}
# two stacked bands, each with its own source and lead columns; zero-regret share in the second
_BANDS = (("fuel_kg", "fuel_pct"), ("time_min", "co2_kg"))
_BAND_LABELS = ("Fuel", "Time and CO\u2082")

ROW_H = 49  # two text lines plus Plotly cell padding render at ~48.9 px; every row is two lines
HEADER_H = 57  # two header lines render at ~57 px
MARGIN = 10
BAND_GAP = 20  # space between the bands (below the first band's last row)
BAND_LABEL_H = 22  # space above each band for its label
FONT_SIZE = 13
# The report's output area is 1,154 px wide at a 1,200 px viewport (measured); leave room for padding.
REPORT_WIDTH = 1100
# widths in px: source, lead, then (mean (90% CI), median, p90) per metric, [zero-regret share]
# Plotly wraps text wider than column minus padding; at 13 px assume ~7.5 px/char + 16 px padding
_W_MEAN, _W_STAT = 152, 92
_W_ZERO = 110


def _widths(n_metrics: int, zero: bool) -> list[int]:
    return [175, 90] + [_W_MEAN, _W_STAT, _W_STAT] * n_metrics + ([_W_ZERO] if zero else [])


COLUMN_WIDTHS = [_widths(len(b), zero=i == len(_BANDS) - 1) for i, b in enumerate(_BANDS)]
WIDTH = max(sum(w) for w in COLUMN_WIDTHS) + 2 * MARGIN


def _band_h(n_rows: int) -> int:
    return HEADER_H + n_rows * ROW_H + 6


def layout_height(n_rows: int) -> int:
    """Figure height with both bands fully visible: every header and row, labels, gap and margins."""
    k = len(_BANDS)
    return 2 * MARGIN + k * BAND_LABEL_H + (k - 1) * BAND_GAP + k * _band_h(n_rows)


SOURCE_LABELS = {
    "hres": "IFS HRES",
    "graphcast": "GraphCast",
    "pangu": "Pangu-Weather",
    "persistence": "Persistence baseline",
    "neuralgcm": "NeuralGCM",
}


def _num(x: float, decimals: int) -> str:
    text = f"{x:.{decimals}f}"
    return text[1:] if text.startswith("-") and float(text) == 0 else text


def _ci(mean: float, lo: float, hi: float, decimals: int) -> str:
    return f"{_num(mean, decimals)}<br>[{_num(lo, decimals)}, {_num(hi, decimals)}]"


def build_headline(df: pd.DataFrame) -> go.Figure:
    """Two stacked tables of mean (90% CI), median and p90 regret per forecast source and lead time."""
    agg = stats.aggregate(df)
    n = len(agg)
    font = dict(size=FONT_SIZE)
    height = layout_height(n)
    fig = go.Figure()
    for i, metrics in enumerate(_BANDS):
        header = ["Forecast source", "Lead time<br>(h)"]
        cells: list[list] = [
            [SOURCE_LABELS.get(s, s) for s in agg["source"]],
            agg["lead_h"].astype(int).tolist(),
        ]
        for m in metrics:
            label, d = _METRICS[m]
            header += [f"{label}<br>{s}" for s in ("mean (90% CI)", "median", "p90")]
            cells.append([_ci(r[f"{m}_mean"], r[f"{m}_ci_lo"], r[f"{m}_ci_hi"], d) for _, r in agg.iterrows()])
            cells.append([_num(v, d) for v in agg[f"{m}_median"]])
            cells.append([_num(v, d) for v in agg[f"{m}_p90"]])
        if i == len(_BANDS) - 1:
            header.append("Zero-regret<br>share")
            cells.append([f"{v:.0%}" for v in agg["zero_regret_share"]])
        top_px = MARGIN + (i + 1) * BAND_LABEL_H + i * (_band_h(n) + BAND_GAP)
        y_hi, y_lo = 1 - top_px / height, 1 - (top_px + _band_h(n)) / height
        fig.add_trace(
            go.Table(
                columnwidth=COLUMN_WIDTHS[i],
                header=dict(values=header, height=HEADER_H, font=font, align="left"),
                cells=dict(values=cells, height=ROW_H, font=font, align="left"),
                domain=dict(x=[0, 1], y=[y_lo, y_hi]),
            )
        )
        fig.add_annotation(
            text=f"<b>{_BAND_LABELS[i]}</b>", xref="paper", yref="paper", x=0, y=y_hi,
            xanchor="left", yanchor="bottom", yshift=4, showarrow=False, font=dict(size=FONT_SIZE + 1),
        )
    fig.update_layout(
        width=WIDTH, height=height,
        margin=dict(l=MARGIN, r=MARGIN, t=MARGIN, b=MARGIN),
    )
    return fig
