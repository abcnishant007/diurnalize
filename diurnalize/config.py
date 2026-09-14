"""Configuration objects and YAML helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PreprocessConfig:
    timezone: str = "UTC"
    time_bin_minutes: int = 30
    days_of_week: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    exclude_dates: list[str] = field(default_factory=list)
    min_value: float = 0.5
    log_offset: float = 0.1
    min_days_per_sensor: int = 10
    min_bins_per_sensor: int | None = None
    aggregation: str = "median"


@dataclass
class ModelConfig:
    preset: str = "balanced"
    n_time_basis: int = 12
    n_spatial_basis: int = 9
    spatial_length_scale: float = 0.1
    global_shape_prior_sd: float = 0.15
    interaction_scale_prior_sd: float = 1.5
    baseline_prior_sd: float = 0.2
    sensor_bias_prior_sd: float = 0.05
    sensor_noise_floor: float = 0.05
    random_seed: int = 42


@dataclass
class SamplerConfig:
    chains: int = 4
    draws: int = 1000
    tune: int = 1000
    cores: int | None = None
    target_accept: float = 0.95
    max_treedepth: int = 12
    progressbar: bool = True
    posterior_predict_samples: int = 200


@dataclass
class DataConfig:
    observations: str
    baseline_grid: str | None = None
    timezone: str = "UTC"
    variable_name: str = "value"
    variable_units: str = ""


@dataclass
class FitConfig:
    data: DataConfig
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    sampler: SamplerConfig = field(default_factory=SamplerConfig)
    quantiles: list[float] = field(default_factory=lambda: [0.05, 0.25, 0.5, 0.75, 0.95])


PRESETS: dict[str, dict[str, Any]] = {
    "quick": {
        "model": {"n_time_basis": 4, "n_spatial_basis": 3, "spatial_length_scale": 0.18},
        "sampler": {"chains": 2, "draws": 25, "tune": 25, "cores": 1, "progressbar": False, "posterior_predict_samples": 40},
        "preprocess": {"min_days_per_sensor": 1, "min_bins_per_sensor": 8},
    },
    "balanced": {},
    "publication": {"sampler": {"draws": 2000, "tune": 2000, "posterior_predict_samples": 500}},
}


def apply_preset(config: FitConfig, preset: str | None) -> FitConfig:
    name = preset or config.model.preset
    if name not in PRESETS:
        raise ValueError(f"Unknown preset {name!r}; expected one of {sorted(PRESETS)}")
    config.model.preset = name
    updates = PRESETS[name]
    for section, values in updates.items():
        obj = getattr(config, section)
        for key, value in values.items():
            setattr(obj, key, value)
    return config


def config_from_dict(raw: dict[str, Any]) -> FitConfig:
    data_raw = raw.get("data", {})
    preprocess_raw = raw.get("preprocess", {})
    model_raw = raw.get("model", {})
    sampler_raw = raw.get("sampler", {})
    outputs_raw = raw.get("outputs", {})
    data = DataConfig(
        observations=str(data_raw["observations"]),
        baseline_grid=data_raw.get("baseline_grid"),
        timezone=data_raw.get("timezone", "UTC"),
        variable_name=data_raw.get("variable_name", "value"),
        variable_units=data_raw.get("variable_units", ""),
    )
    preprocess = PreprocessConfig(**{k: v for k, v in preprocess_raw.items() if k in PreprocessConfig.__dataclass_fields__})
    preprocess.timezone = data.timezone
    model = ModelConfig(**{k: v for k, v in model_raw.items() if k in ModelConfig.__dataclass_fields__})
    sampler = SamplerConfig(**{k: v for k, v in sampler_raw.items() if k in SamplerConfig.__dataclass_fields__})
    return FitConfig(data=data, preprocess=preprocess, model=model, sampler=sampler, quantiles=outputs_raw.get("quantiles", [0.05, 0.25, 0.5, 0.75, 0.95]))


def load_config(path: str | Path) -> FitConfig:
    with Path(path).open() as f:
        return config_from_dict(yaml.safe_load(f))


def write_config(config: FitConfig, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w") as f:
        yaml.safe_dump(asdict(config), f, sort_keys=False)
