"""Core static validation plots."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def save_validation_plots(run_dir: str | Path, output_dir: str | Path) -> list[str]:
    run = Path(run_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    made: list[str] = []
    sensors = pd.read_csv(run / "sensors.csv")
    dyn = pd.read_csv(run / "preprocessed_observations.csv")

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(sensors["lon"], sensors["lat"], c=sensors["baseline"], s=45, cmap="viridis")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Sensors")
    for ext in ["png", "pdf"]:
        path = out / f"sensor_map.{ext}"
        fig.savefig(path, dpi=180, bbox_inches="tight")
        made.append(str(path))
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for sid, grp in dyn.groupby("sensor_id"):
        ax.plot(grp["time_bin"], grp["value"] / grp["value"].mean(), alpha=0.7, lw=1, label=str(sid))
    ax.set_xlabel("Time bin")
    ax.set_ylabel("Observed normalized shape")
    ax.set_title("Sensor Profiles")
    for ext in ["png", "pdf"]:
        path = out / f"sensor_profiles.{ext}"
        fig.savefig(path, dpi=180, bbox_inches="tight")
        made.append(str(path))
    plt.close(fig)
    return made
