"""Showcase map: every plan for the showcase flight over the 250 hPa wind (CONTRACTS section 6)."""
from __future__ import annotations

import logging
import time as _time
from importlib import resources
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from regret import config as _config
from regret import planner, regret, replay, sources
from regret.figures import style
from regret.figures.headline import SOURCE_LABELS
from regret.types import TRUTH_LEAD_H, TRUTH_SOURCE, Config

FIG_ID = "fig-showcase-map"
BASEMAP_KEY = "world_110m"  # plotly.js topojson name: "<geo.scope>_<geo.resolution>"
DEFAULT_LEAD_H = 24
GRID_STEP_DEG = 2.5
# monotone: white under ~10 m/s, light grey at 20, mid grey at 60, dark grey from ~100 m/s (cmax ~ 111);
# stops are fractions of cmax, drawn at 0.8 opacity so the on-screen greys are lighter than these
BG_SCALE = [[0.0, "#ffffff"], [0.09, "#f6f6f6"], [0.18, "#e0e0e0"], [0.54, "#969696"],
            [0.9, "#3c3c3c"], [1.0, "#323232"]]
HALO_COLOUR = "#ffffff"
HINDSIGHT_COLOUR = "rgba(255,127,14,0.95)"  # no source uses orange
log = logging.getLogger(__name__)


def _label(source: str) -> str:
    return SOURCE_LABELS.get(source, source)


def showcase_plans(cfg: Config) -> dict:
    """Per-flight procedure (CONTRACTS 2.11, steps 1-4) for the showcase flight."""
    flight = _config.showcase_flight(cfg)
    truth = sources.truth_winds(cfg)
    plans = [planner.plan(truth, flight, source=TRUTH_SOURCE, lead_h=TRUTH_LEAD_H)]
    for source in cfg.sources:
        for lead in cfg.leads_h:
            wind = sources.forecast_winds(cfg, source, flight, lead)
            plans.append(planner.plan(wind, flight, source=source, lead_h=lead))
    replays = [replay.replay(p, flight, truth) for p in plans]
    hindsight = regret.select_hindsight(replays, cfg.sources)
    return {"flight": flight, "truth": truth, "plans": plans, "replays": replays, "hindsight": hindsight}


def _speed_grid(wind, lat, lon, when) -> np.ndarray:
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    u, v = wind.uv(la, lo, np.datetime64(when, "ns"))
    return np.round(np.hypot(u, v), 1).ravel()


def build_showcase_map(cfg: Config, *, plans: dict | None = None) -> go.Figure:
    """Map of the showcase flight's plans with a lead dropdown and a forecast-wind slider."""
    p = plans or showcase_plans(cfg)
    flight, truth, hindsight = p["flight"], p["truth"], p["hindsight"]
    box = cfg.box
    # the 1.5-degree data grid starts half a cell inside the box edges
    lat = np.arange(box.lat_min_deg + 1.0, box.lat_max_deg - 0.5 + 1e-9, GRID_STEP_DEG)
    lon = np.arange(box.lon_min_deg + 1.5, box.lon_max_deg - 0.5 + 1e-9, GRID_STEP_DEG)
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    when = flight.departure_time
    era5 = _speed_grid(truth, lat, lon, when)

    fields = {(s, lead): _speed_grid(sources.forecast_winds(cfg, s, flight, lead), lat, lon, when)
              for s in cfg.sources for lead in cfg.leads_h}
    zmax = float(max(era5.max(), *(f.max() for f in fields.values())))
    title_era5 = "ERA5 (truth) wind (m/s)"

    def step(label, z, title, hover):
        return {"label": label, "method": "restyle",
                "args": [{"marker.color": [z], "marker.colorbar.title.text": [title],
                          "hovertemplate": [hover]}, [0]]}

    hover_era5 = "ERA5 (truth): %{marker.color:.1f} m/s<extra></extra>"

    def steps_for(lead):
        out = [step("ERA5", era5, title_era5, hover_era5)]
        for s in cfg.sources:
            out.append(step(_label(s), fields[(s, lead)], f"{_label(s)}, lead {lead} h (m/s)",
                            f"{_label(s)} forecast, lead {lead} h: %{{marker.color:.1f}} m/s<extra></extra>"))
        return out

    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=la.ravel(), lon=lo.ravel(), mode="markers", name="Wind speed", showlegend=False,
        marker={"symbol": "square", "size": 9, "color": era5, "colorscale": BG_SCALE, "cmin": 0,
                "cmax": zmax, "opacity": 0.8, "line": {"width": 0},
                "colorbar": {"title": {"text": title_era5, "side": "right"}, "thickness": 14,
                             "len": 0.7, "y": 0.5}},
        hovertemplate=hover_era5, meta={"kind": "background"}))

    hind_path = [pl for pl in p["plans"] if pl.source == hindsight.source and pl.lead_h == hindsight.lead_h][0]

    def same_path(plan):
        return (len(plan.lat_deg) == len(hind_path.lat_deg)
                and np.allclose(plan.lat_deg, hind_path.lat_deg) and np.allclose(plan.lon_deg, hind_path.lon_deg))

    for lead in cfg.leads_h:
        shown = lead == DEFAULT_LEAD_H
        at_lead = [pl for pl in p["plans"] if pl.source != TRUTH_SOURCE and pl.lead_h == lead]
        twins = [pl for pl in at_lead if same_path(pl)]
        hname = "Hindsight plan"
        if twins:
            hname += f" (= {_label(twins[0].source)}, {lead} h)"
        fig.add_trace(go.Scattergeo(
            lat=hindsight.lat_deg[::5].tolist(), lon=hindsight.lon_deg[::5].tolist(), mode="lines",
            line={"width": 7, "color": HINDSIGHT_COLOUR, "dash": "dot"}, opacity=0.5, name=hname,
            legendgroup="hindsight", showlegend=True,
            hovertext=f"{hname}; best plan in hindsight is {_label(hindsight.source)}, "
                      f"lead {hindsight.lead_h} h; shown with lead {lead} h",
            hoverinfo="text", visible=shown, meta={"kind": "plan", "source": "hindsight", "lead_h": lead}))
        for plan in at_lead:
            if plan.source == "persistence":  # white halo keeps the grey dashed line visible over the dark jet
                fig.add_trace(go.Scattergeo(
                    lat=list(plan.lat_deg), lon=list(plan.lon_deg), mode="lines",
                    line={"width": 6, "color": HALO_COLOUR}, legendgroup=plan.source, showlegend=False,
                    hoverinfo="skip", visible=shown, meta={"kind": "halo", "lead_h": lead}))
            fig.add_trace(go.Scattergeo(
                lat=list(plan.lat_deg), lon=list(plan.lon_deg), mode="lines",
                line={"width": 3 if plan.source == "persistence" else 2, "color": style.colour(plan.source),
                      **({"dash": "dash"} if plan.source == "persistence" else {})},
                name=_label(plan.source), legendgroup=plan.source, showlegend=True,
                hovertext=f"{_label(plan.source)} plan, lead {lead} h", hoverinfo="text",
                visible=shown, meta={"kind": "plan", "source": plan.source, "lead_h": lead}))

    buttons = []
    pad = [None] * (len(fig.data) - 1)  # a restyle array is per trace; only trace 0 (background) gets a value
    for lead in cfg.leads_h:
        vis = [(t.meta["kind"] == "background") or t.meta["lead_h"] == lead for t in fig.data]
        # slider steps change with the lead, so the background goes back to ERA5 (departure wind has no lead)
        restyle = {"visible": vis, "marker.color": [era5, *pad],
                   "marker.colorbar.title.text": [title_era5, *pad], "hovertemplate": [hover_era5, *pad]}
        buttons.append({"label": f"{lead} h", "method": "update",
                        "args": [restyle, {"sliders[0].steps": steps_for(lead), "sliders[0].active": 0}]})
    start = list(cfg.leads_h).index(DEFAULT_LEAD_H) if DEFAULT_LEAD_H in cfg.leads_h else 0
    fig.update_layout(
        title={"text": f"Plans for {_flight_label(flight)} over the 250 hPa wind at departure",
               "x": 0.0, "xanchor": "left", "y": 0.98, "yanchor": "top"},
        updatemenus=[{"type": "dropdown", "buttons": buttons, "active": start, "x": 0.14, "y": 1.01,
                      "xanchor": "left", "yanchor": "bottom", "showactive": True}],
        sliders=[{"active": 0, "steps": steps_for(cfg.leads_h[start]), "x": 0.05, "len": 0.9,
                  "y": -0.17, "yanchor": "top", "currentvalue": {"prefix": "Background: "}}],
        annotations=[{"text": "Lead time", "x": 0.0, "y": 1.01, "xref": "paper", "yref": "paper",
                      "showarrow": False, "xanchor": "left", "yanchor": "bottom"}],
        legend={"orientation": "h", "x": 0.0, "xanchor": "left", "y": -0.03, "yanchor": "top"},
        margin={"l": 10, "r": 10, "t": 110, "b": 150}, height=760,
        geo={"projection": {"type": "mercator"}, "showland": True, "landcolor": "#eeeeee",
             "showcoastlines": True, "showcountries": True,
             "lonaxis": {"range": [box.lon_min_deg, box.lon_max_deg]},
             "lataxis": {"range": [box.lat_min_deg, box.lat_max_deg]}},
    )
    return fig


def _flight_label(flight) -> str:
    """"JFK→LHR, 2020-02-09 00:00 UTC": origin→destination plus the departure time."""
    when = flight.departure_time
    return f"{flight.origin.code}→{flight.destination.code}, {when:%Y-%m-%d %H:%M} UTC"


def basemap_json() -> str:
    """The vendored plotly.js world topojson (src/regret/figures/geo/README.md)."""
    return resources.files("regret.figures").joinpath("geo", "world_110m.json").read_text(encoding="utf-8")


def geo_assets_html() -> str:
    """A <script> that hands plotly.js its basemap, so the map makes no network request."""
    return ("<script>window.PlotlyGeoAssets = window.PlotlyGeoAssets || {topojson: {}}; "
            f"window.PlotlyGeoAssets.topojson.{BASEMAP_KEY} = {basemap_json().strip()};</script>")


def write_html(fig: go.Figure, path) -> None:
    """Write a standalone page of the map: plotly.js and the basemap inlined, no network needed."""
    body = fig.to_html(full_html=False, include_plotlyjs=True, div_id=FIG_ID)
    Path(path).write_text(
        '<!doctype html>\n<html><head><meta charset="utf-8"></head><body>\n'
        f"{geo_assets_html()}\n{body}\n</body></html>\n", encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    t0 = _time.perf_counter()
    build_showcase_map(_config.get_config())
    log.info("elapsed_s=%.2f", _time.perf_counter() - t0)
