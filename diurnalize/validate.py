"""Validation metrics and artifact writing."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .plots import save_validation_plots


def validate(run_dir: str | Path, output_dir: str | Path) -> dict:
    run = Path(run_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dyn = pd.read_csv(run / "preprocessed_observations.csv")
    metrics = dyn.groupby("sensor_id").agg(n_bins=("time_bin", "nunique"), mean_value=("value", "mean"), sd_value=("value", "std")).reset_index()
    metrics.to_csv(out / "sensor_fit_metrics.csv", index=False)
    shape_metrics = []
    for sid, grp in dyn.groupby("sensor_id"):
        shape = grp["value"].to_numpy() / grp["value"].mean()
        shape_metrics.append({"sensor_id": sid, "shape_min": float(np.min(shape)), "shape_max": float(np.max(shape)), "shape_sd": float(np.std(shape))})
    pd.DataFrame(shape_metrics).to_csv(out / "shape_metrics_per_sensor.csv", index=False)
    plots = save_validation_plots(run, out)
    summary = {"n_sensors": int(dyn["sensor_id"].nunique()), "n_aggregated_observations": int(len(dyn)), "plots": [Path(p).name for p in plots]}
    with (out / "diagnostics_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    return summary
