"""Command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import DataConfig, FitConfig, write_config
from .fit import fit as fit_run
from .predict import predict_grid
from .report import write_report
from .synthetic import generate_demo as generate_demo_data
from .validate import validate as validate_run

app = typer.Typer(no_args_is_help=True)


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
    fit_run(config, output, preset)


@app.command("predict")
def predict(run: Path = typer.Option(..., "--run"), grid: Path = typer.Option(..., "--grid"), output: Path = typer.Option(..., "--output")):
    predict_grid(run, grid, output)


@app.command("validate")
def validate(run: Path = typer.Option(..., "--run"), output: Path = typer.Option(..., "--output")):
    validate_run(run, output)


@app.command("report")
def report(run: Path = typer.Option(..., "--run"), output: Path = typer.Option(..., "--output")):
    write_report(run, output)


if __name__ == "__main__":
    app()
