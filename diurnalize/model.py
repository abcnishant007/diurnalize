"""PyMC model construction preserving the Cleveland algorithm invariants."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pymc as pm

from .basis import SpatialBasis
from .config import ModelConfig


@dataclass
class ModelInputs:
    dynamic: object
    sensors: object
    temporal_basis: np.ndarray
    spatial_basis: SpatialBasis
    log_s_bg: np.ndarray
    lambda_s: np.ndarray
    k: int


def empirical_background(dynamic, n_sensors: int, k: int) -> np.ndarray:
    s_all = np.full((n_sensors, k), np.nan)
    for s_idx in range(n_sensors):
        prof = np.full(k, np.nan)
        rows = dynamic[dynamic["sensor_idx"] == s_idx]
        for _, row in rows.iterrows():
            prof[int(row["time_bin"])] = row["value"]
        if np.isfinite(prof).sum() > 0:
            mean = np.nanmean(prof)
            if mean > 0:
                prof = prof / mean
        s_all[s_idx] = prof
    with np.errstate(all="ignore"):
        bg = np.nanmedian(s_all, axis=0)
    bg = np.where(np.isnan(bg), 1.0, bg)
    return np.log(np.maximum(bg, 1e-6))


def mad_noise_scales(dynamic, n_sensors: int, floor: float) -> np.ndarray:
    out = np.zeros(n_sensors)
    for s_idx in range(n_sensors):
        y = dynamic[dynamic["sensor_idx"] == s_idx]["log_value"].to_numpy()
        if len(y) > 10:
            out[s_idx] = 1.4826 * np.median(np.abs(y - np.median(y)))
        else:
            out[s_idx] = 0.5
    return np.maximum(out, floor)


def build_model(inputs: ModelInputs, config: ModelConfig) -> pm.Model:
    dynamic = inputs.dynamic
    sensors = inputs.sensors
    y_obs = dynamic["log_value"].to_numpy()
    sensor_idx = dynamic["sensor_idx"].to_numpy(dtype=int)
    bin_idx = dynamic["time_bin"].to_numpy(dtype=int)
    baseline = sensors["baseline"].to_numpy()
    log_baseline = np.log(baseline)
    phi = inputs.spatial_basis.phi_sensors
    temporal_basis = inputs.temporal_basis
    n_sensors = len(sensors)
    n_time_basis = temporal_basis.shape[1]
    n_spatial_basis = phi.shape[1]

    # Ported from pm25_01_fusion.py: same priors, low-rank interaction,
    # centering constraints, sensor bias/noise, and time-softmax likelihood.
    with pm.Model() as model:
        mu_raw = pm.Normal("mu_raw", mu=inputs.log_s_bg, sigma=config.global_shape_prior_sd, shape=inputs.k)
        mu = pm.Deterministic("mu", mu_raw - pm.math.mean(mu_raw))

        w_scale = pm.HalfNormal("w_scale", sigma=config.interaction_scale_prior_sd)
        w_raw = pm.Normal("w_raw", mu=0, sigma=1, shape=(n_time_basis, n_spatial_basis))
        w = pm.Deterministic("w", w_raw * w_scale)

        r_by_time_basis = pm.math.dot(w, phi.T)
        r_raw = pm.math.dot(temporal_basis, r_by_time_basis).T
        r_centered = r_raw - pm.math.mean(r_raw, axis=0, keepdims=True)

        mu_baseline = pm.Normal("mu_baseline", mu=log_baseline, sigma=config.baseline_prior_sd, shape=n_sensors)
        b = pm.Normal("b", mu=0, sigma=config.sensor_bias_prior_sd, shape=n_sensors)
        sigma_s = pm.HalfNormal("sigma_s", sigma=inputs.lambda_s, shape=n_sensors)

        z = mu[None, :] + r_centered
        log_s = pm.Deterministic("log_S", z - pm.math.logsumexp(z, axis=1, keepdims=True) + np.log(inputs.k))
        mu_obs = mu_baseline[sensor_idx] + log_s[sensor_idx, bin_idx] + b[sensor_idx]
        pm.Normal("y_obs", mu=mu_obs, sigma=sigma_s[sensor_idx], observed=y_obs)
    return model
