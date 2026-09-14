"""Fit orchestration and run persistence."""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict
from pathlib import Path

import arviz as az
import numpy as np
import pymc as pm

from .basis import fit_spatial_basis, wrapped_gaussian_temporal_basis
from .config import FitConfig, apply_preset, load_config
from .data import load_baseline_csv, load_sensor_csv
from .model import ModelInputs, build_model, empirical_background, mad_noise_scales
from .preprocess import preprocess_observations


def fit(config: FitConfig | str | Path, output_dir: str | Path, preset: str | None = None):
    if not isinstance(config, FitConfig):
        config = load_config(config)
    config = apply_preset(config, preset)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    obs = load_sensor_csv(config.data.observations, config.data.timezone, config.data.variable_name, config.data.variable_units)
    baseline = load_baseline_csv(config.data.baseline_grid, config.data.variable_name, config.data.variable_units) if config.data.baseline_grid else None
    dynamic, sensors, prep_summary = preprocess_observations(obs, baseline, config.preprocess)
    k = 1440 // config.preprocess.time_bin_minutes
    temporal = wrapped_gaussian_temporal_basis(k, config.model.n_time_basis)
    spatial = fit_spatial_basis(sensors[["lat", "lon"]].to_numpy(), config.model.n_spatial_basis, config.model.spatial_length_scale, config.model.random_seed)
    log_s_bg = empirical_background(dynamic, len(sensors), k)
    lambda_s = mad_noise_scales(dynamic, len(sensors), config.model.sensor_noise_floor)

    inputs = ModelInputs(dynamic, sensors, temporal, spatial, log_s_bg, lambda_s, k)
    model = build_model(inputs, config.model)
    with model:
        trace = pm.sample(
            draws=config.sampler.draws,
            tune=config.sampler.tune,
            chains=config.sampler.chains,
            cores=config.sampler.cores or config.sampler.chains,
            target_accept=config.sampler.target_accept,
            nuts_sampler_kwargs={"max_treedepth": config.sampler.max_treedepth},
            random_seed=config.model.random_seed,
            return_inferencedata=True,
            progressbar=config.sampler.progressbar,
            discard_tuned_samples=False,
        )

    trace_path = out / "trace.nc"
    trace.to_netcdf(trace_path)
    dynamic.to_csv(out / "preprocessed_observations.csv", index=False)
    sensors.to_csv(out / "sensors.csv", index=False)
    with (out / "basis.pkl").open("wb") as f:
        pickle.dump({"spatial": spatial, "temporal": temporal, "k": k, "log_s_bg": log_s_bg}, f)
    with (out / "config_resolved.json").open("w") as f:
        json.dump(asdict(config), f, indent=2)
    with (out / "preprocessing_summary.json").open("w") as f:
        json.dump(prep_summary, f, indent=2)

    try:
        summary = az.summary(trace, var_names=["mu", "w", "w_scale", "mu_baseline"], hdi_prob=0.95)
    except TypeError:
        summary = az.summary(trace, var_names=["mu", "w", "w_scale", "mu_baseline"])
    summary.to_csv(out / "convergence_summary.csv")
    diagnostics = {
        "max_r_hat": float(np.nanmax(summary["r_hat"].to_numpy())) if "r_hat" in summary else None,
        "min_ess_bulk": float(np.nanmin(summary["ess_bulk"].to_numpy())) if "ess_bulk" in summary else None,
        "divergences": int(trace.sample_stats["diverging"].values.sum()) if "diverging" in trace.sample_stats else 0,
        "trace": str(trace_path),
    }
    with (out / "diagnostics_summary.json").open("w") as f:
        json.dump(diagnostics, f, indent=2)
    manifest = {"diurnalize_version": "0.1.0", "trace": "trace.nc", "config": "config_resolved.json", "preprocessing_summary": "preprocessing_summary.json"}
    with (out / "manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    return trace
