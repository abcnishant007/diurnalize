"""Prediction exports for sensor/grid locations."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
import xarray as xr

from .basis import project_spatial_basis, softmax_time
from .data import load_baseline_csv


def _flat(arr: np.ndarray) -> np.ndarray:
    s = arr.shape
    return arr.reshape(s[0] * s[1], *s[2:])


def _q_label(q: float) -> str:
    return f"value_q{int(round(q * 100)):03d}"


def predict_grid(run_dir: str | Path, grid: str | Path, output_dir: str | Path) -> pd.DataFrame:
    run = Path(run_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (run / "config_resolved.json").open() as f:
        config = json.load(f)
    with (run / "basis.pkl").open("rb") as f:
        basis_data = pickle.load(f)
    trace = az.from_netcdf(run / "trace.nc")
    df_grid = load_baseline_csv(grid, config["data"]["variable_name"], config["data"]["variable_units"])
    input_rows = len(df_grid)
    df_grid = df_grid.dropna(subset=["baseline"]).copy()
    df_grid = df_grid[df_grid["baseline"] > 0].reset_index(drop=True)
    if df_grid.empty:
        raise ValueError("Prediction grid has no rows with positive baseline.")
    if "cell_id" not in df_grid.columns:
        df_grid["cell_id"] = np.arange(len(df_grid)).astype(str)

    spatial = basis_data["spatial"]
    temporal = basis_data["temporal"]
    k = int(basis_data["k"])
    phi_grid = project_spatial_basis(df_grid[["lat", "lon"]].to_numpy(), spatial)
    phi_sensors = spatial.phi_sensors

    post = trace.posterior
    mu_all = _flat(post["mu"].values)
    w_all = _flat(post["w"].values)
    n_total = len(mu_all)
    n_samples = min(int(config["sampler"]["posterior_predict_samples"]), n_total)
    rng = np.random.default_rng(int(config["model"]["random_seed"]))
    sel = np.sort(rng.choice(n_total, size=n_samples, replace=False))
    mu = mu_all[sel]
    w = w_all[sel]

    a_grid = np.einsum("pij,xj->pix", w, phi_grid)
    r_grid = np.einsum("pix,ki->pxk", a_grid, temporal)
    a_sens = np.einsum("pij,sj->pis", w, phi_sensors)
    r_sens = np.einsum("pis,ki->psk", a_sens, temporal)
    r_centered = r_grid - r_sens.mean(axis=1)[:, None, :]
    z = mu[:, None, :] + r_centered
    shape = softmax_time(z)
    values = df_grid["baseline"].to_numpy()[None, :, None] * shape

    quantiles = config.get("quantiles", [0.05, 0.25, 0.5, 0.75, 0.95])
    value_mean = values.mean(axis=0)
    qs = np.quantile(values, quantiles, axis=0)
    rows = []
    hours = np.arange(k) * (1440 / k) / 60
    for i, row in df_grid.iterrows():
        for tb in range(k):
            rec = {
                "location_id": row["cell_id"],
                "latitude": row["lat"],
                "longitude": row["lon"],
                "time_bin": tb,
                "hour": hours[tb],
                "baseline": row["baseline"],
                "value_mean": value_mean[i, tb],
            }
            for qi, q in enumerate(quantiles):
                rec[_q_label(q)] = qs[qi, i, tb]
            rows.append(rec)
    pred = pd.DataFrame(rows)
    pred.to_csv(out / "predictions_long.csv", index=False)

    ds = xr.Dataset(
        data_vars={"value_mean": (["grid_cell", "time_bin"], value_mean.astype("float32"))},
        coords={
            "latitude": (["grid_cell"], df_grid["lat"].to_numpy(dtype="float32")),
            "longitude": (["grid_cell"], df_grid["lon"].to_numpy(dtype="float32")),
            "baseline": (["grid_cell"], df_grid["baseline"].to_numpy(dtype="float32")),
            "time_bin": np.arange(k, dtype="int16"),
            "hour": (["time_bin"], hours.astype("float32")),
        },
        attrs={"model": "Y(x,k)=B(x)*S(x,k); S is time-softmax mean-preserving", "n_posterior_samples": n_samples},
    )
    for qi, q in enumerate(quantiles):
        ds[_q_label(q)] = (["grid_cell", "time_bin"], qs[qi].astype("float32"))
    ds.to_netcdf(out / "predictions.nc")

    daily = value_mean.mean(axis=1)
    mp = pd.DataFrame({"location_id": df_grid["cell_id"], "baseline": df_grid["baseline"], "daily_mean_value": daily, "abs_error": np.abs(daily - df_grid["baseline"])})
    mp.to_csv(out / "mean_preserving_check.csv", index=False)
    summary = {
        "input_rows": int(input_rows),
        "predicted_locations": int(len(df_grid)),
        "excluded_missing_or_nonpositive_baseline": int(input_rows - len(df_grid)),
        "time_bins": int(k),
        "max_mean_preserving_abs_error": float(mp["abs_error"].max()),
    }
    with (out / "prediction_grid_summary.csv").open("w") as f:
        pd.DataFrame([summary]).to_csv(f, index=False)
    with (out / "manifest.json").open("w") as f:
        json.dump({"predictions_long": "predictions_long.csv", "netcdf": "predictions.nc", "mean_preserving_check": "mean_preserving_check.csv"}, f, indent=2)
    return pred
