"""Preprocessing for canonical observation inputs."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .config import PreprocessConfig


def preprocess_observations(observations: pd.DataFrame, baseline_grid: pd.DataFrame | None, config: PreprocessConfig) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    df = observations.copy()
    initial_rows = len(df)
    if config.time_bin_minutes <= 0 or 1440 % config.time_bin_minutes != 0:
        raise ValueError("time_bin_minutes must be a positive divisor of 1440.")
    k = 1440 // config.time_bin_minutes
    min_bins = config.min_bins_per_sensor if config.min_bins_per_sensor is not None else k // 2

    local = df["timestamp_utc"].dt.tz_convert(config.timezone)
    df["local_date"] = local.dt.date
    df["weekday"] = local.dt.weekday
    df["time_bin"] = ((local.dt.hour * 60 + local.dt.minute) // config.time_bin_minutes).astype(int)
    df = df[df["weekday"].isin(config.days_of_week)].copy()
    if config.exclude_dates:
        excluded = {pd.to_datetime(d).date() for d in config.exclude_dates}
        df = df[~df["local_date"].isin(excluded)].copy()
    df = df[df["value"] >= config.min_value].copy()

    coverage = df.groupby("sensor_id").agg(n_days=("local_date", "nunique"), n_bins=("time_bin", "nunique")).reset_index()
    good = coverage[(coverage["n_days"] >= config.min_days_per_sensor) & (coverage["n_bins"] >= min_bins)]["sensor_id"]
    df = df[df["sensor_id"].isin(good)].copy()
    if df["sensor_id"].nunique() < 2:
        raise ValueError("Too few sensors remain after preprocessing; need at least 2.")

    agg_func = "median" if config.aggregation == "median" else "mean"
    dynamic = df.groupby(["sensor_id", "time_bin"], as_index=False).agg(value=("value", agg_func))
    dynamic["log_value"] = np.log(dynamic["value"] + config.log_offset)

    sensors = df.groupby("sensor_id", as_index=False).agg(lat=("lat", "first"), lon=("lon", "first"))
    if baseline_grid is not None:
        valid_baseline = baseline_grid.dropna(subset=["baseline"]).copy()
        valid_baseline = valid_baseline[valid_baseline["baseline"] > 0].copy()
        if valid_baseline.empty:
            raise ValueError("baseline_grid contains no positive baseline rows.")
        tree = cKDTree(valid_baseline[["lat", "lon"]].to_numpy())
        _, idx = tree.query(sensors[["lat", "lon"]].to_numpy())
        sensors["baseline"] = valid_baseline.iloc[idx]["baseline"].to_numpy()
    elif "baseline" in observations.columns:
        sensors["baseline"] = df.groupby("sensor_id")["baseline"].median().reindex(sensors["sensor_id"]).to_numpy()
    else:
        sensor_mean = dynamic.groupby("sensor_id")["value"].mean()
        sensors["baseline"] = sensors["sensor_id"].map(sensor_mean)

    sensors = sensors.sort_values("sensor_id").reset_index(drop=True)
    sensor_to_idx = {sid: i for i, sid in enumerate(sensors["sensor_id"])}
    dynamic["sensor_idx"] = dynamic["sensor_id"].map(sensor_to_idx).astype(int)
    dynamic = dynamic.sort_values(["sensor_idx", "time_bin"]).reset_index(drop=True)

    summary = {
        "config": asdict(config),
        "initial_rows": int(initial_rows),
        "rows_after_filters": int(len(df)),
        "aggregated_rows": int(len(dynamic)),
        "sensors_after_filters": int(len(sensors)),
        "time_bins": int(k),
        "min_bins_per_sensor": int(min_bins),
    }
    return dynamic, sensors, summary


def write_preprocessing_summary(summary: dict[str, Any], path: str | Path) -> None:
    import json

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w") as f:
        json.dump(summary, f, indent=2)
