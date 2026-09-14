"""Strict canonical CSV loaders."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OBS_REQUIRED = ["sensor_id", "lat", "lon", "timestamp_utc", "value"]
BASELINE_REQUIRED = ["lat", "lon", "baseline"]


def _canonicalize_columns(df: pd.DataFrame, required: list[str], path: str | Path) -> pd.DataFrame:
    mapping: dict[str, str] = {}
    lower_to_actual = {str(col).lower(): col for col in df.columns}
    missing = []
    for col in required:
        actual = lower_to_actual.get(col.lower())
        if actual is None:
            missing.append(col)
        else:
            mapping[actual] = col
    if missing:
        raise ValueError(f"{path} is missing required column(s): {missing}. Headers are canonical with case-insensitive matching only.")
    return df.rename(columns=mapping)


def load_sensor_csv(path: str | Path, timezone: str = "UTC", variable_name: str = "value", variable_units: str = "") -> pd.DataFrame:
    df = _canonicalize_columns(pd.read_csv(path), OBS_REQUIRED, path)
    df["sensor_id"] = df["sensor_id"].astype(str)
    df["lat"] = pd.to_numeric(df["lat"], errors="raise")
    df["lon"] = pd.to_numeric(df["lon"], errors="raise")
    df["value"] = pd.to_numeric(df["value"], errors="raise")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="raise")
    bad = df["value"] <= 0
    if bool(bad.any()):
        raise ValueError(f"{path} contains {int(bad.sum())} nonpositive value rows; values must be positive.")
    coords = df.groupby("sensor_id")[["lat", "lon"]].nunique()
    conflicts = coords[(coords["lat"] > 1) | (coords["lon"] > 1)]
    if not conflicts.empty:
        raise ValueError(f"{path} has sensor_id values with conflicting coordinates: {list(conflicts.index[:5])}")
    df.attrs.update({"timezone": timezone, "variable_name": variable_name, "variable_units": variable_units})
    return df


def load_baseline_csv(path: str | Path, variable_name: str = "value", variable_units: str = "") -> pd.DataFrame:
    df = _canonicalize_columns(pd.read_csv(path), BASELINE_REQUIRED, path)
    df["lat"] = pd.to_numeric(df["lat"], errors="raise")
    df["lon"] = pd.to_numeric(df["lon"], errors="raise")
    df["baseline"] = pd.to_numeric(df["baseline"], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    df.attrs.update({"variable_name": variable_name, "variable_units": variable_units})
    return df
