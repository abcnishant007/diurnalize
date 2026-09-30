"""Command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import DataConfig, FitConfig, write_config
from .synthetic import generate_demo as generate_demo_data

app = typer.Typer(no_args_is_help=True)


def _missing_extra(command: str, exc: ModuleNotFoundError) -> None:
    raise typer.BadParameter(
        f"{command} requires optional modeling dependencies. Install with `pip install 'diurnalize[model]'`."
    ) from exc


@app.command("init-config")
def init_config(output: Path = typer.Option(..., "--output")):
    write_config(FitConfig(data=DataConfig(observations="observations.csv")), output)


@app.command("generate-demo")
def generate_demo(
    output: Path = typer.Option(..., "--output"),
    scenario: str = typer.Option("null_shape", "--scenario"),
    n_sensors: int = typer.Option(48, "--n-sensors"),
    n_days: int = typer.Option(20, "--n-days"),
    grid_resolution: int = typer.Option(40, "--grid-resolution"),
    random_seed: int = typer.Option(42, "--random-seed"),
):
    generate_demo_data(output, scenario, n_sensors, n_days, grid_resolution, random_seed)


@app.command("fit")
def fit(config: Path = typer.Option(..., "--config"), output: Path = typer.Option(..., "--output"), preset: str | None = typer.Option(None, "--preset")):
    try:
        from .fit import fit as fit_run
    except ModuleNotFoundError as exc:
        _missing_extra("fit", exc)
    fit_run(config, output, preset)


@app.command("predict")
def predict(run: Path = typer.Option(..., "--run"), grid: Path = typer.Option(..., "--grid"), output: Path = typer.Option(..., "--output")):
    try:
        from .predict import predict_grid
    except ModuleNotFoundError as exc:
        _missing_extra("predict", exc)
    predict_grid(run, grid, output)


@app.command("validate")
def validate(run: Path = typer.Option(..., "--run"), output: Path = typer.Option(..., "--output")):
    try:
        from .validate import validate as validate_run
    except ModuleNotFoundError as exc:
        _missing_extra("validate", exc)
    validate_run(run, output)


@app.command("report")
def report(run: Path = typer.Option(..., "--run"), output: Path = typer.Option(..., "--output")):
    try:
        from .report import write_report
    except ModuleNotFoundError as exc:
        _missing_extra("report", exc)
    write_report(run, output)


if __name__ == "__main__":
    app()
