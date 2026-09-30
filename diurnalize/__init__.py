"""Public API for diurnalize."""

from .config import FitConfig, ModelConfig, PreprocessConfig, SamplerConfig
from .data import load_baseline_csv, load_sensor_csv

__all__ = [
    "FitConfig",
    "ModelConfig",
    "PreprocessConfig",
    "SamplerConfig",
    "fit",
    "load_baseline_csv",
    "load_sensor_csv",
    "predict_grid",
    "validate",
]


def __getattr__(name: str):
    if name == "fit":
        from .fit import fit

        return fit
    if name == "predict_grid":
        from .predict import predict_grid

        return predict_grid
    if name == "validate":
        from .validate import validate

        return validate
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
