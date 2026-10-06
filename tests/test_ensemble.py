"""Ensemble robust plan choice (SPEC 1.3 item 1, reduced method 1.5)."""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from regret import cli, ensemble
from regret.config import get_config, matched_flights
from regret.figures import headline, style
from regret.figures.ensemble import FIG_ID, build_ensemble
from tests.test_neuralgcm import figure_table

FIXTURE = get_config("fixture")
LEADS = (24,)
COLUMNS = [
    "flight_id", "direction", "lead_h", "choice", "members", "fuel_kg", "time_min", "co2_kg",
    "regret_fuel_kg", "beats_hindsight",
]


# --- choice rule on a 3-member synthetic ensemble ---

# cost[j, k]: plan j (planned on member j) replayed through member k
COST = np.array([
    [ 9.0,  9.0, 13.0],   # mean 10.33, p90 12.2
    [ 6.0,  6.0, 17.0],   # mean 9.67, p90 14.8  -> lowest mean
    [ 8.0, 11.0, 11.0],   # mean 10, p90 11      -> lowest p90
])


def test_mean_and_p90_robust_have_lowest_statistics():
    mean_j, p90_j = ensemble.choose_robust(COST)
    assert mean_j == COST.mean(axis=1).argmin() == 1
    assert p90_j == np.percentile(COST, 90, axis=1).argmin() == 2


def test_ties_go_to_the_lowest_member_index():
    assert ensemble.choose_robust(np.full((3, 3), 5.0)) == (0, 0)


def test_floored_regret_and_beats_hindsight():
    assert ensemble.floored_regret(105.0, 100.0) == 5.0
    assert ensemble.floored_regret(95.0, 100.0) == 0.0
    assert ensemble.beats_hindsight(95.0, 100.0) is True
    assert ensemble.beats_hindsight(100.0, 100.0) is False
    assert ensemble.beats_hindsight(105.0, 100.0) is False


# --- run on a synthetic 3-member cache ---

@pytest.fixture(scope="module")
def cfg(tmp_path_factory):
    d = tmp_path_factory.mktemp("cache")
    for name in ("era5", "hres", "graphcast", "pangu"):
        (d / f"{name}.zarr").symlink_to((FIXTURE.cache_dir / f"{name}.zarr").resolve())
    base = xr.open_zarr(FIXTURE.cache_dir / "hres.zarr").load()
    members = [base * s for s in (1.0, 1.15, 0.85)]
    xr.concat(members, dim="member").assign_coords(member=[0, 1, 2]).to_zarr(d / "neuralgcm_ens.zarr")
    return dataclasses.replace(FIXTURE, cache_dir=d, results_path=d / "out" / "regret.parquet")


@pytest.fixture(scope="module")
def flights(cfg):
    return matched_flights(cfg, "neuralgcm")[:2]


@pytest.fixture(scope="module")
def result(cfg, flights):
    return ensemble.run(cfg, flights=flights[:1], leads_h=LEADS, members=3, workers=1, hindsight=None)


def test_cli_dispatches_ensemble():
    assert "ensemble" in cli.COMMANDS


def test_schema_and_rows(result):
    assert list(result.columns) == COLUMNS
    assert list(result["choice"]) == ["mean_robust", "p90_robust"]
    assert (result["members"] == 3).all()
    assert result["beats_hindsight"].dtype == bool
    assert (result["regret_fuel_kg"] >= 0).all()


def test_default_hindsight_floors_against_own_cost(result):
    # no add-on hindsight given: it is the cheaper of the two choices, so one regret is 0
    assert result["regret_fuel_kg"].min() == 0.0


def test_explicit_hindsight(cfg, flights):
    f = flights[0]
    big = ensemble.run(cfg, flights=[f], leads_h=LEADS, members=3, workers=1, hindsight={f.flight_id: 1e9})
    assert big["beats_hindsight"].all() and (big["regret_fuel_kg"] == 0).all()
    tiny = ensemble.run(cfg, flights=[f], leads_h=LEADS, members=3, workers=1, hindsight={f.flight_id: 1.0})
    assert not tiny["beats_hindsight"].any()
    assert np.allclose(tiny["regret_fuel_kg"], tiny["fuel_kg"] - 1.0)


def test_workers_identical_on_one_flight_slice(cfg, flights):
    f = flights[:1]
    a = ensemble.run(cfg, flights=f, leads_h=LEADS, members=3, workers=1, hindsight={f[0].flight_id: 1e9})
    b = ensemble.run(cfg, flights=f, leads_h=LEADS, members=3, workers=2, hindsight={f[0].flight_id: 1e9})
    pd.testing.assert_frame_equal(a, b)


def test_main_writes_parquet_and_logs_elapsed(cfg, flights, monkeypatch, caplog):
    real = ensemble.run
    monkeypatch.setattr(ensemble, "get_config", lambda *a, **k: cfg)
    monkeypatch.setattr(
        ensemble, "run",
        lambda c, **kw: real(c, flights=flights[:1], leads_h=LEADS, members=3, workers=1, hindsight=None),
    )
    with caplog.at_level("INFO"):
        assert ensemble.main([]) == 0
    out = pd.read_parquet(cfg.results_path.parent / "ensemble_regret.parquet")
    assert list(out.columns) == COLUMNS
    assert "elapsed_s=" in caplog.text


# --- figure ---

def ens_table() -> pd.DataFrame:
    rows = []
    for fid in ("F1", "F2", "F3", "F4"):
        for lead in (6, 12):
            for i, choice in enumerate(("mean_robust", "p90_robust")):
                rows.append(dict(
                    flight_id=fid, direction="eastbound", lead_h=lead, choice=choice, members=20,
                    fuel_kg=1000.0, time_min=400.0, co2_kg=3160.0,
                    regret_fuel_kg=float(lead + i), beats_hindsight=bool(i),
                ))
    return pd.DataFrame(rows)


def test_fig_id_and_html():
    assert FIG_ID == "fig-ensemble"
    fig = build_ensemble(ens_table(), figure_table())
    assert f'id="{FIG_ID}"' in fig.to_html(div_id=FIG_ID)


def test_four_lines_title_and_structure():
    fig = build_ensemble(ens_table(), figure_table())
    lines = [t for t in fig.data if t.fill != "toself"]
    names = {t.name for t in lines}
    assert {"Mean-robust plan", "p90-robust plan", headline.SOURCE_LABELS["neuralgcm"]} <= names
    assert len(lines) == 4  # + best core source
    assert fig.layout.title.text.startswith("Ensemble robust plans (M = 20 members)")
    assert "4 flights, 12-hourly planning" in fig.layout.title.text
    assert fig.layout.height and not fig.layout.width
    assert fig.layout.legend.orientation == "h"
    assert list(fig.layout.xaxis.tickvals) == [6, 12]
    assert any("90% CI" in a.text for a in fig.layout.annotations)


def test_hover_is_x_unified_with_ci_and_bands_skipped():
    fig = build_ensemble(ens_table(), figure_table())
    assert fig.layout.hovermode == "x unified"
    bands = [t for t in fig.data if t.fill == "toself"]
    assert bands and all(t.hoverinfo == "skip" for t in bands)
    for t in (t for t in fig.data if t.fill != "toself"):
        assert t.hovertemplate.startswith(t.name) and "[%{customdata[0]" in t.hovertemplate and "kg" in t.hovertemplate
        assert len(t.customdata) == len(t.x)
        assert all(lo <= m <= hi for (lo, hi), m in zip(t.customdata, t.y))
