"""Synthetic canonical data generation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def _mean_preserve(shape: np.ndarray) -> np.ndarray:
    return shape / shape.mean(axis=-1, keepdims=True)


def generate_demo(output: str | Path, scenario: str = "null_shape", n_sensors: int = 48, n_days: int = 20, grid_resolution: int = 40, random_seed: int = 42) -> None:
    if scenario not in {"null_shape", "east_west_peaks", "biased_sensors"}:
        raise ValueError("scenario must be one of: null_shape, east_west_peaks, biased_sensors")
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(random_seed)
    k = 48
    hours = np.arange(k) / 2

    lat0, lon0, size = 41.45, -81.75, 0.2
    sensors = pd.DataFrame(
        {
            "sensor_id": [f"s{i:03d}" for i in range(n_sensors)],
            "lat": lat0 + rng.uniform(0, size, n_sensors),
            "lon": lon0 + rng.uniform(0, size, n_sensors),
        }
    )
    gx, gy = np.meshgrid(np.linspace(0, size, grid_resolution), np.linspace(0, size, grid_resolution))
    grid = pd.DataFrame({"lat": lat0 + gy.ravel(), "lon": lon0 + gx.ravel()})
    grid["cell_id"] = [f"g{i:04d}" for i in range(len(grid))]
    grid["baseline"] = 10.0 + 3.0 * np.exp(-((grid["lat"] - (lat0 + 0.13)) ** 2 + (grid["lon"] - (lon0 + 0.07)) ** 2) / 0.004)

    base_shape = 1.0 + 0.18 * np.exp(-0.5 * ((hours - 8) / 2.0) ** 2) + 0.12 * np.exp(-0.5 * ((hours - 18) / 2.5) ** 2)
    base_shape = base_shape / base_shape.mean()
    true_shapes = np.zeros((n_sensors, k))
    lon_score = (sensors["lon"].to_numpy() - sensors["lon"].mean()) / max(sensors["lon"].max() - sensors["lon"].min(), 1e-9)
    for i in range(n_sensors):
        if scenario == "null_shape" or scenario == "biased_sensors":
            shape = base_shape.copy()
        else:
            shift = int(round(lon_score[i] * 8))
            morning = np.roll(np.exp(-0.5 * ((hours - 8) / 1.8) ** 2), shift)
            evening = np.roll(np.exp(-0.5 * ((hours - 18) / 2.0) ** 2), -shift)
            mix = np.clip(0.5 + lon_score[i], 0.05, 0.95)
            shape = 1.0 + 0.45 * ((1 - mix) * morning + mix * evening)
        true_shapes[i] = _mean_preserve(shape[None, :])[0]

    # Smooth synthetic baseline at sensors.
    sensor_baseline = 10.0 + 3.0 * np.exp(-((sensors["lat"] - (lat0 + 0.13)) ** 2 + (sensors["lon"] - (lon0 + 0.07)) ** 2) / 0.004)
    bias = rng.normal(0, 0.05 if scenario == "biased_sensors" else 0.02, n_sensors)
    rows = []
    start = pd.Timestamp("2023-01-02T00:00:00Z")
    for i, sensor in sensors.iterrows():
        for day in range(n_days):
            day_scale = rng.lognormal(0, 0.08)
            for tb in range(k):
                ts = start + pd.Timedelta(days=day, minutes=30 * tb)
                val = sensor_baseline[i] * true_shapes[i, tb] * day_scale
                val = rng.lognormal(np.log(max(val, 0.1)) + bias[i], 0.12)
                rows.append({"sensor_id": sensor["sensor_id"], "lat": sensor["lat"], "lon": sensor["lon"], "timestamp_utc": ts.isoformat(), "value": val})
    obs = pd.DataFrame(rows)
    obs.to_csv(out / "observations.csv", index=False)
    grid[["cell_id", "lat", "lon", "baseline"]].to_csv(out / "baseline_grid.csv", index=False)
    sensors.to_csv(out / "sensor_metadata.csv", index=False)
    truth_shape = []
    for i, sensor in sensors.iterrows():
        for tb in range(k):
            truth_shape.append({"sensor_id": sensor["sensor_id"], "lat": sensor["lat"], "lon": sensor["lon"], "time_bin": tb, "hour": hours[tb], "shape_true": true_shapes[i, tb]})
    pd.DataFrame(truth_shape).to_csv(out / "truth_shape.csv", index=False)
    truth_surface = []
    for _, cell in grid.iterrows():
        for tb in range(k):
            truth_surface.append({"cell_id": cell["cell_id"], "lat": cell["lat"], "lon": cell["lon"], "time_bin": tb, "hour": hours[tb], "baseline_true": cell["baseline"], "value_true": cell["baseline"] * base_shape[tb]})
    pd.DataFrame(truth_surface).to_csv(out / "truth_surface.csv", index=False)
    cfg = {
        "project": {"name": f"demo_{scenario}", "output_dir": str(out)},
        "data": {"observations": str(out / "observations.csv"), "baseline_grid": str(out / "baseline_grid.csv"), "timezone": "UTC", "variable_name": "PM2.5", "variable_units": "ug/m3"},
        "preprocess": {"time_bin_minutes": 30, "days_of_week": [0, 1, 2, 3, 4], "exclude_dates": [], "min_value": 0.5, "log_offset": 0.1, "min_days_per_sensor": 1, "min_bins_per_sensor": 8, "aggregation": "median"},
        "model": {"preset": "quick", "n_time_basis": 4, "n_spatial_basis": 3, "spatial_length_scale": 0.18, "random_seed": random_seed},
        "sampler": {"chains": 2, "draws": 25, "tune": 25, "cores": 1, "target_accept": 0.95, "max_treedepth": 12, "progressbar": False, "posterior_predict_samples": 40},
        "outputs": {"quantiles": [0.05, 0.25, 0.5, 0.75, 0.95], "formats": ["csv", "netcdf"], "plots": True, "plot_formats": ["png", "pdf"], "report": True},
    }
    with (out / "config.yaml").open("w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    manifest = {"scenario": scenario, "n_sensors": n_sensors, "n_days": n_days, "grid_resolution": grid_resolution, "files": ["observations.csv", "baseline_grid.csv", "sensor_metadata.csv", "truth_shape.csv", "truth_surface.csv", "config.yaml"]}
    with (out / "manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    (out / "README.md").write_text(f"# Diurnalize Demo\n\nScenario: `{scenario}`\n\nRun `diurnalize fit --config {out / 'config.yaml'} --output /tmp/diurnalize_run --preset quick`.\n")
