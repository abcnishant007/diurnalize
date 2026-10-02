# Diurnalize

Diurnalize turns a daily mean environmental surface into time-of-day estimates
using sensor observations. It is designed for workflows where you have:

- sensor readings with timestamps and locations
- a gridded baseline mean field
- a need for hourly or sub-hourly predictions that preserve the daily mean

The command line tools cover demo data generation, model fitting, grid
prediction, validation, and HTML report creation.

## Install

For the full modeling workflow:

```bash
pip install "diurnalize[model]"
```

For only data loading, configuration, synthetic demo generation, and CLI
discovery:

```bash
pip install diurnalize
```

## Quick Start

Run a complete toy workflow:

```bash
diurnalize generate-demo --output /tmp/diurnalize_demo --scenario null_shape --n-sensors 6 --n-days 2 --grid-resolution 5
diurnalize fit --config /tmp/diurnalize_demo/config.yaml --output /tmp/diurnalize_run --preset quick
diurnalize predict --run /tmp/diurnalize_run --grid /tmp/diurnalize_demo/baseline_grid.csv --output /tmp/diurnalize_run/predictions
diurnalize validate --run /tmp/diurnalize_run --output /tmp/diurnalize_run/validation
diurnalize report --run /tmp/diurnalize_run --output /tmp/diurnalize_run/report.html
```

The demo creates canonical input files, fits a small model, exports gridded
predictions, runs validation checks, and writes an HTML report.

## Use Your Own Data

Create a starter config:

```bash
diurnalize init-config --output config.yaml
```

Edit `config.yaml` so `data.observations` points to your observation CSV and,
if available, `data.baseline_grid` points to your baseline grid CSV. Then run:

```bash
diurnalize fit --config config.yaml --output run --preset quick
diurnalize predict --run run --grid baseline_grid.csv --output run/predictions
diurnalize validate --run run --output run/validation
diurnalize report --run run --output run/report.html
```

## CSV Schemas

Observation CSVs require canonical headers matched case-insensitively only:

```text
sensor_id,lat,lon,timestamp_utc,value
```

Baseline grids require:

```text
lat,lon,baseline
```

Optional baseline columns include `cell_id`, `region_id`, and `area_weight`.

## Outputs

`diurnalize predict` writes:

- `predictions_long.csv`: one row per location and time bin
- `predictions.nc`: NetCDF prediction cube
- `mean_preserving_check.csv`: daily mean preservation check
- `prediction_grid_summary.csv`: prediction summary

`diurnalize validate` writes validation summaries and plots. `diurnalize report`
combines run metadata, diagnostics, and validation plots into a single HTML
file.

## Method

Diurnalize decomposes a positive environmental variable into a spatial baseline
level `B(x)` and a local time-of-day multiplier `S(x,k)`:

```text
Y(x,k) = B(x) * S(x,k)
```

The shape model uses temporal basis functions, low-rank spatial RBF bases,
sensor-specific bias, sensor-specific noise, and a time softmax so each
predicted daily shape has mean 1.

## Development

```bash
pip install -e ".[dev]"
pytest
```
