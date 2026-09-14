# Pip Package Idea: Diurnalize

## Purpose

The package should provide a reusable implementation of mean-preserving diurnal disaggregation. A user provides sensor observations and, optionally, a spatial baseline or mean field. The package estimates local time-of-day multipliers, combines them with the baseline, and exports predictions, uncertainty, diagnostics, and validation artifacts in standard formats.

The public USP should be:

> A Bayesian model for mean-preserving diurnal disaggregation: it decomposes a pollutant or environmental variable into a spatial baseline level `B(x)` and a local time-of-day multiplier `S(x,k)`, where the daily mean of `S(x,k)` is 1. The diurnal shape borrows strength across sensors through low-rank spatial and temporal bases while estimating sensor bias, sensor noise, posterior uncertainty, and validation diagnostics.

The package should be pollutant-neutral in naming. PM2.5 should be the first-class documented example, and when the user declares the variable as PM2.5 the package can use PM2.5-specific labels and units in plots and reports. For other variables, units and display names should be explicit user parameters.

The README should include a citation note: if users find the package or methods useful, they should consider citing the associated paper. Paper reproduction should stay outside the package.

## Package Name

The package name is frozen as:

- `diurnalize`

The name is short, describes the central operation, and avoids tying the package to a single pollutant.

## Target Users

- Method developers who want structured outputs for comparison against kriging, random forest, GPs, or baseline-only models.

Useful built-in comparisons:

- Baseline-only: predict `B(x)` with no time-of-day variation.
- Global diurnal profile: estimate one mean-preserving `S(k)` shared by all locations.
- Sensor-nearest shape: assign each prediction location the observed normalized profile from the nearest sensor.
- Spatially smoothed shape: smooth observed normalized sensor profiles with inverse-distance weighting or RBF interpolation.
- Random forest or gradient boosting baseline: predict binned values from latitude, longitude, hour, and optional baseline.
- Gaussian process or kriging baseline: interpolate normalized shape residuals by time bin.

The first release should include the simple baselines. Random forest, Gaussian process, and kriging comparisons can be included later if they add too much dependency or runtime burden.

## Non-Goals For Version 0.1

- Do not package the full exposure pipeline.
- Do not require PurpleAir-specific columns.
- Do not require private GHAP, Replica, or paper-specific data.
- Do not force users into the current per-city script layout.
- Do not expose every PyMC tuning internals as top-level knobs.
- Do not promise continental-scale raster processing in memory.

## Core Model Contract

The package should expose the core mean-preserving model:

```text
Y(x,k) = B(x) * S(x,k)
```

where:

- `Y(x,k)` is the pollutant or environmental variable at location `x` and time bin `k`.
- `B(x)` is a positive baseline, mean field, or daily average level at location `x`, either provided by the user or estimated from sensors.
- `S(x,k)` is a mean-preserving time-of-day multiplier, constrained so the average over time bins is 1.
- `S(x,k)` is generated from a latent field:

```text
Z(x,k) = mu(k) + r(x,k)
r(x,k) = low-rank spatial basis crossed with wrapped temporal basis
S(x,k) = softmax_time(Z(x,k)) * K
```

At sensor locations, observations are modeled approximately as:

```text
log(y_i + offset) = log(B(x_s)) + log(S(x_s,k_i)) + b_s + eps_i
```

where:

- `b_s` is sensor-specific bias.
- `eps_i` uses sensor-specific noise.
- `mu(k)` captures the shared diurnal shape.
- `r(x,k)` captures spatial variation in the diurnal shape.

## Package Principles

1. Make the default path easy: CSV in, fitted model out, validation report out.
2. Keep public knobs meaningful and few.
3. Support synthetic data as a first-class workflow, not a hidden test.
4. Require CSV headers with exact canonical names, matched case-insensitively but with spaces and underscores treated as meaningful.
5. Export every important visual diagnostic as both a plot and machine-readable data.
6. Export map-friendly files that can be loaded in Kepler.gl or served by a simple Python local server.
7. Keep paper reproduction separate from the reusable package. This is a standalone pip package based on the core methods proposed in the paper.
8. Make data validation strict, helpful, and early.

## Public API Shape

The package should support both Python and CLI workflows.

### Python API

Proposed minimal API:

```python
import diurnalize as dz

data = dz.load_sensor_csv(
    "sensors.csv",
    timezone="America/New_York",
    variable_name="PM2.5",
    variable_units="ug/m3",
)

baseline = dz.load_baseline_csv(
    "baseline_grid.csv",
    variable_name="PM2.5",
    variable_units="ug/m3",
)

fit = dz.fit(
    observations=data,
    baseline=baseline,
    time_bin_minutes=30,
    model="hierarchical_shape",
    preset="balanced",
    random_seed=42,
)

surface = fit.predict_grid(grid=baseline.grid, quantiles=[0.05, 0.5, 0.95])
report = dz.validate(fit, output_dir="outputs/validation")
```

### CLI

Proposed commands:

```bash
diurnalize init-config --output config.yaml
diurnalize generate-demo --output demo_data --scenario east_west_peaks --n-sensors 48 --n-days 20
diurnalize validate-inputs --config config.yaml
diurnalize fit --config config.yaml --output run_001
diurnalize predict --run run_001 --grid baseline_grid.csv --output run_001/predictions
diurnalize validate --run run_001 --output run_001/validation
diurnalize report --run run_001 --output run_001/report.html
```

## Input Data Requirements

### Required Sensor Observation CSV

Long format should be the primary contract. CSV files must have headers. Required headers use exact canonical names after case folding only: `Sensor_ID` should match `sensor_id`, but `sensor id`, `sensor-id`, and `sensor__id` should not. This keeps user errors visible and avoids ambiguous automatic column matching.

Required columns:

| Concept | Example column | Type | Notes |
|---|---:|---|---|
| Sensor ID | `sensor_id` | string/int | Stable across rows |
| Latitude | `lat` | float | WGS84 decimal degrees |
| Longitude | `lon` | float | WGS84 decimal degrees |
| Timestamp | `timestamp_utc` | datetime | UTC preferred; timezone accepted if specified |
| Measurement | `value` | float | Positive pollutant or environmental value |

Optional columns:

| Concept | Example column | Use |
|---|---:|---|
| Sensor quality flag | `quality_flag` | Filter bad rows |
| Sensor type | `sensor_type` | Group diagnostics |
| Units | `units` | Validation and plot labels |
| Calibration group | `calibration_group` | Future bias hierarchy |
| Existing baseline at sensor | `baseline` | Skip nearest-grid baseline lookup |

The loader should not silently guess columns. If users have noncanonical headers, they should rename columns before loading.

### Optional Baseline Grid CSV

Required if users want gridded predictions or baseline-informed disaggregation.

Required columns:

| Concept | Example column | Type |
|---|---:|---|
| Latitude | `lat` | float |
| Longitude | `lon` | float |
| Baseline value | `baseline` | positive float |

Optional columns:

| Concept | Example column | Use |
|---|---:|---|
| Grid cell ID | `cell_id` | Stable output key |
| Region ID | `region_id` | Group summaries |
| Area weight | `area_weight` | Aggregation |

### Optional Prediction Locations CSV

Allow predictions at arbitrary points, not only a baseline grid:

```text
location_id,lat,lon,baseline
```

`baseline` must be present and positive for every prediction location. Locations or grid cells with missing baseline values are excluded from the study and reported in the preprocessing summary.

## Preprocessing Knobs

These should be exposed because they materially change the data going into the model.

| Knob | Default | Why it matters |
|---|---:|---|
| `timezone` | infer/UTC | Determines local time-of-day bins |
| `time_bin_minutes` | 30 | Current paper model uses 48 bins/day |
| `days_of_week` | weekdays | Paper workflow filters weekdays; users may need all days |
| `exclude_dates` | empty | Holidays, wildfire events, outages |
| `min_value` | 0.5 for PM2.5 | Removes artifacts before log transform |
| `log_offset` | 0.1 | Stabilizes `log(value + offset)` |
| `min_days_per_sensor` | 10 | Sensor inclusion threshold |
| `min_bins_per_sensor` | half of daily bins | Ensures diurnal coverage |
| `aggregation` | median by sensor x bin | Robust to spikes and matches current scripts |
| `outlier_policy` | none/winsorize/drop | Needed for noisy low-cost sensors |
| `missing_bin_policy` | keep missing | Avoid fake smoothing before model |

Recommendation: use a `PreprocessConfig` object and write the post-filter row/sensor counts to JSON.

## Model Knobs

The package should expose model knobs in two layers: presets for most users and advanced settings for method users.

### Presets

Recommended presets:

| Preset | Intended use |
|---|---|
| `quick` | synthetic demos, CI tests, small examples |
| `balanced` | default real-data run |
| `publication` | slower, stronger diagnostics, more posterior samples |
| `shape_only` | no external baseline; learn normalized `S(x,k)` behavior only |

### Core User-Facing Knobs

| Knob | Default | Notes |
|---|---:|---|
| `n_time_basis` | 12 | Wrapped temporal basis count |
| `n_spatial_basis` | min(9, sensors) | Controls spatial complexity |
| `spatial_length_scale` | auto or 0.1 deg | Kernel bandwidth; should support distance units later |
| `n_chains` | 4 | MCMC quality |
| `draws` | 1000 | Posterior draws |
| `tune` | 1000 | Warmup |
| `target_accept` | 0.95 | Divergence control |
| `max_treedepth` | 12 | NUTS control |
| `random_seed` | 42 | Reproducibility |
| `posterior_predict_samples` | 200 | Prediction/export cost |
| `quantiles` | 0.05, 0.25, 0.5, 0.75, 0.95 | Output uncertainty bands |

### Prior Knobs

Expose only with clear names:

| Knob | Current analogue | Suggested default |
|---|---|---:|
| `global_shape_prior_sd` | `mu_raw sigma` | 0.15 |
| `interaction_scale_prior_sd` | `w_scale HalfNormal sigma` | 1.5 |
| `baseline_prior_sd` | `mu_baseline sigma` | 0.2 |
| `sensor_bias_prior_sd` | `b sigma` | 0.05 |
| `sensor_noise_floor` | `lambda_s minimum` | 0.05 |
| `sensor_noise_method` | MAD | `mad` |

### Basis Knobs

Expose:

- `time_basis="wrapped_gaussian"` initially.
- `spatial_basis="rbf_kmeans_qr"` initially.
- `spatial_basis_centers="kmeans"` or user-provided centers.
- `distance_metric="degrees"` initially, later `projected_meters`.
- `center_spatial_residual=True`.
- `mean_preserving_shape=True`, always true for the main model.

Recommendation: do not let users disable mean preservation in the main public model. If needed, make it a separate experimental model class.

## Data Generation Requirements

Synthetic data should be a major feature because the paper data are not public.

### Generator Goals

The generator should produce:

- Sensor observation CSV.
- Sensor metadata CSV, if separate.
- Baseline grid CSV.
- Prediction grid CSV.
- Ground-truth `S(x,k)` CSV/NetCDF.
- Ground-truth PM surface CSV/NetCDF.
- A config file that can run immediately.
- A README describing the generated scenario.

### Synthetic Scenarios

Minimum scenarios:

| Scenario | Purpose |
|---|---|
| `east_west_peaks` | Current synthetic idea: morning/evening shape shifts across longitude |
| `hotspot_baseline` | Baseline varies spatially but diurnal shape is nearly global |
| `shape_hotspot` | Mean baseline fixed, local time-of-day anomaly varies spatially |
| `sparse_network` | Few sensors, uneven placement |
| `missingness` | Missing bins/days and irregular reporting |
| `biased_sensors` | Sensor-specific bias and noise stress test |
| `null_shape` | No spatial shape variation; checks false positives |

### Generator Knobs

| Knob | Default |
|---|---:|
| `n_sensors` | 48 |
| `n_days` | 20 |
| `domain_bbox` | synthetic square |
| `grid_resolution` | 40 x 40 |
| `time_bin_minutes` | 30 |
| `baseline_mean` | 12 |
| `baseline_spatial_sd` | configurable |
| `shape_amplitude` | configurable |
| `measurement_noise_sd` | 0.2 log-scale |
| `sensor_bias_sd` | 0.05 log-scale |
| `missing_rate` | 0 |
| `outlier_rate` | 0 |
| `random_seed` | 42 |

### Synthetic Ground Truth Exports

Every synthetic run should write:

- `observations.csv`
- `baseline_grid.csv`
- `sensor_metadata.csv`
- `truth_shape.csv`: `sensor_id,lat,lon,time_bin,hour,shape_true`
- `truth_surface.csv`: `cell_id,lat,lon,time_bin,hour,baseline_true,pm_true`
- `config.yaml`
- `manifest.json`

## Validation Outputs

Validation must be a package feature, not a side script.

### Machine-Readable Outputs

Write these by default:

- `diagnostics_summary.json`
- `preprocessing_summary.json`
- `convergence_summary.csv`
- `sensor_fit_metrics.csv`
- `holdout_sensor_metrics.csv`, if holdouts are used
- `shape_metrics_per_sensor.csv`
- `prediction_grid_summary.csv`
- `uncertainty_summary.csv`
- `mean_preserving_check.csv`
- `synthetic_recovery_metrics.csv`, when truth is available
- `kepler_prediction_points.csv` or `.geojson`, for point maps
- `kepler_prediction_grid.geojson`, when polygon/grid geometry is available
- `benchmark_metrics.csv`, when benchmark models are run

The map-friendly outputs should be loadable directly into Kepler.gl. For dense grids, the package can document a simple local Python server pattern that generates per-location or per-pixel figures on demand. No caching is required for version 0.1.

### Plot Outputs

Write PNG and PDF for all static images. SVG can be optional when the plotting backend supports it cleanly.

- Trace plots for key model parameters: selected `mu[k]`, `w_scale`, selected `w[i,j]`.
- R-hat/ESS summary plot.
- Observed versus predicted sensor scatter.
- Residuals by sensor and by time bin.
- In-sample selected sensor profiles.
- Holdout sensor profiles.
- Shape-only profile validation: observed normalized shape versus posterior shape.
- Sensor bias distribution.
- Sensor noise distribution.
- Spatial map of sensors and held-out sensors.
- Prediction maps for selected time bins.
- Uncertainty maps: `p95 - p05`, optionally `p75 - p25`.
- Mean-preserving check: average predicted value versus baseline.
- Synthetic truth versus recovered shape, when truth exists.
- Benchmark comparison plots, when benchmark models are run.

### Report Output

Generate one summary report:

- `report.html` for human review.
- Optional `report.md`.

The report should include:

- Data summary.
- Model configuration.
- Convergence status.
- Key validation plots.
- Key metric tables.
- Warnings and failed checks.
- Paths to machine-readable exports.

## Prediction Outputs

Support four output formats:

1. Long CSV for interoperability.
2. NetCDF for dense gridded spatiotemporal output.
3. Parquet for scalable analytics.
4. GeoJSON for Kepler.gl and browser-based map review.

Recommended long prediction schema:

```text
location_id,latitude,longitude,time_bin,hour,timestamp,baseline,
value_mean,value_q005,value_q025,value_q050,value_q075,value_q095
```

Core outputs should use pollutant-neutral `value_*` names. PM2.5-specific language belongs in plot titles, report text, and metadata-driven labels, not output column names.

## Holdout And Cross-Validation

Holdout support should be built in:

| Knob | Default | Notes |
|---|---:|---|
| `holdout_fraction` | 0 | Disabled unless requested |
| `holdout_n_sensors` | null | Alternative to fraction |
| `holdout_strategy` | spatial_kmeans | Spatially representative holdouts |
| `holdout_seed` | 42 | Reproducible |
| `refit_for_holdout` | true | Honest validation; no-refit interpolation can be an advanced faster mode |

Validation should support:

- In-sample fit.
- True out-of-sample sensor holdout with refit.
- No-refit spatial interpolation diagnostic, clearly labeled as weaker.
- Synthetic recovery against known truth.

## Configuration File

Use YAML as the main CLI config.

Example:

```yaml
project:
  name: demo_east_west
  output_dir: runs/demo_east_west

data:
  observations: demo_data/observations.csv
  baseline_grid: demo_data/baseline_grid.csv
  timezone: America/New_York
  variable_name: PM2.5
  variable_units: ug/m3

preprocess:
  time_bin_minutes: 30
  days_of_week: [0, 1, 2, 3, 4]
  exclude_dates: []
  min_value: 0.5
  log_offset: 0.1
  min_days_per_sensor: 10
  min_bins_per_sensor: 24
  aggregation: median

model:
  preset: balanced
  n_time_basis: 12
  n_spatial_basis: 9
  spatial_length_scale: auto
  random_seed: 42

sampler:
  chains: 4
  draws: 1000
  tune: 1000
  target_accept: 0.95
  max_treedepth: 12

outputs:
  quantiles: [0.05, 0.25, 0.5, 0.75, 0.95]
  formats: [csv, netcdf, parquet, geojson]
  plots: true
  plot_formats: [png, pdf]
  report: true
```

## Architecture Recommendation

Suggested package layout:

```text
diurnalize/
  __init__.py
  config.py
  data.py
  preprocess.py
  basis.py
  model.py
  fit.py
  predict.py
  validate.py
  plots.py
  synthetic.py
  report.py
  cli.py
```

Responsibilities:

- `data.py`: CSV loaders, schema validation, canonical header checks.
- `preprocess.py`: filtering, local time bins, aggregation, sensor inclusion.
- `basis.py`: wrapped temporal basis, spatial RBF basis, QR projection, k-means centers.
- `model.py`: PyMC model construction.
- `fit.py`: sampler wrapper, trace writing, metadata writing.
- `predict.py`: sensor/grid prediction, quantiles, NetCDF/CSV/Parquet export.
- `validate.py`: metrics and validation tables.
- `plots.py`: all validation and diagnostic plots.
- `synthetic.py`: demo data and known-truth scenarios.
- `report.py`: HTML/Markdown report assembly.
- `cli.py`: command-line interface.

## Dependencies

The package should install one complete dependency set. A normal install should support default and advanced workflows, including NetCDF, Parquet, reports, CLI use, and geospatial review. This keeps user setup simple and forces CI to test the real package surface.

Required dependencies:

- `numpy`
- `pandas`
- `scipy`
- `scikit-learn`
- `pymc`
- `arviz`
- `xarray`
- `matplotlib`
- `pyyaml`
- `netcdf4`
- `pyarrow`
- `geopandas`
- `contextily`
- `plotly`
- `typer`
- `flask`, if the Kepler/local figure server is implemented with the existing server pattern
- `jinja2` for reports
- `pydantic` for config validation

Developer and CI dependencies can be separate, but runtime features should not depend on pip extras.

CI should include a tiny end-to-end pipeline test:

```bash
diurnalize generate-demo --output /tmp/diurnalize_demo --scenario null_shape --n-sensors 6 --n-days 2
diurnalize fit --config /tmp/diurnalize_demo/config.yaml --output /tmp/diurnalize_run --preset quick
diurnalize validate --run /tmp/diurnalize_run --output /tmp/diurnalize_run/validation
diurnalize predict --run /tmp/diurnalize_run --grid /tmp/diurnalize_demo/baseline_grid.csv --output /tmp/diurnalize_run/predictions
diurnalize report --run /tmp/diurnalize_run --output /tmp/diurnalize_run/report.html
```

This test should use a deliberately tiny dummy model so the package requirements stay relevant without making CI slow.

## Usability Requirements

The first public release should include:

- A working `generate-demo -> fit -> validate -> predict -> report` path.
- A small synthetic example that finishes in minutes.
- A larger synthetic example that demonstrates recovery quality.
- Clear CSV schemas.
- Clear error messages for missing columns, invalid timestamps, nonpositive values, duplicate sensor IDs with conflicting coordinates, and too few sensors.
- Main equations documented clearly.
- Versioned output manifests so runs are reproducible.

## Minimum Viable Version

Version 0.1 should include:

1. Long sensor CSV input.
2. Baseline grid CSV input.
3. Synthetic data generation with at least `east_west_peaks`, `biased_sensors`, and `null_shape`.
4. Preprocessing and sensor quality filtering.
5. Hierarchical shape model with mean-preserving softmax.
6. Fit with PyMC.
7. Predict at sensor locations and grid locations.
8. CSV and NetCDF prediction exports.
9. Core validation metrics as JSON/CSV.
10. Core validation plots as PNG/PDF.
11. CLI and Python API.
12. HTML or Markdown report.
13. At least baseline-only and global-diurnal benchmark comparisons.
14. Kepler-friendly CSV or GeoJSON outputs.

## Key Decisions To Freeze Before Coding

1. Baseline `B(x)` is optional, with a shape-only mode for users without a baseline grid.
2. The package is pollutant-neutral, with PM2.5 as the main example.
3. Exact CSV schemas use canonical headers with case-insensitive matching only.
4. Output variable names use `value_*`; PM2.5-specific plot labels come from user metadata.
5. Default preset values for quick, balanced, and publication runs.
6. Whether version 0.1 includes honest refit holdout or only no-refit interpolation diagnostics.
7. Whether reports are HTML first, Markdown first, or both.
8. Whether geospatial plotting stays simple lat/lon scatter in 0.1 or includes map overlays.
9. Which basic benchmarks are required in version 0.1.

## Recommended Next Step

Before implementation, write a short package specification that freezes:

- The `observations.csv`, `baseline_grid.csv`, and prediction output schemas.
- The `quick`, `balanced`, and `publication` presets.
- The exact CLI commands.
- The minimum validation artifacts for version 0.1.
- The minimum benchmark comparisons for version 0.1.
- The README citation note for the associated paper.

## Codex Implementation Brief

This section is written for the next Codex agent that will implement the package.

### Working Directory

Start in the new package repository:

```bash
cd /Users/nishant/Documents/GitHub/diurnalize
```

The old research repository is available as a read-only source of algorithms and patterns:

```bash
/Users/nishant/Documents/GitHub/replica-process
```

Do not implement inside `replica-process`. Copy or adapt only the relevant method code into `diurnalize`.

### Source Code To Inspect And Port From

Use one representative city folder as the main reference, because the city folders are mostly repeated copies. Cleveland is a good reference:

```text
/Users/nishant/Documents/GitHub/replica-process/bayesian_fusion/bayesian_fusion_Cleveland/
```

Inspect these files first:

- `pm25_01_fusion.py`: core PyMC model, temporal basis, spatial basis, priors, likelihood, trace writing.
- `pm25_02_predict_grid.py`: grid projection, posterior prediction, mean-preserving check, NetCDF output pattern.
- `pm25_data_loader.py`: preprocessing rules, local time bins, weekday/holiday filtering, sensor inclusion, median aggregation.
- `pm25_config.py`: current defaults for `K`, basis counts, length scale, posterior prediction samples.
- `synthetic.py`: known-truth synthetic shape generation and recovery validation.
- `pm25_04_diagnostics.py`, `pm25_05_ppc_check.py`, `pm25_06_sensor_Shape_easy_validate.py`, `pm25_07_sensor_Shape_hard_validate.py`, `pm25_09_posterior_viz.py`, `pm25_10_W_viz.py`: diagnostics and plots to port selectively.
- `pm25_02a_quantilebands.py`, `pm25_03_nc_to_csv.py`: long CSV and quantile-band export ideas.
- `serve_quantile_tiles.py`: local server pattern for Kepler/browser tooltips with on-demand temporal profile figures.

There are also docs in:

```text
/Users/nishant/Documents/GitHub/replica-process/docs/bayesian_fusion.rst
/Users/nishant/Documents/GitHub/replica-process/docs/bayesian_fusion_api.rst
/Users/nishant/Documents/GitHub/replica-process/docs/bayesian_fusion_runbook.rst
```

Use these to understand the method, but the new package should have its own README and API docs.

### Non-Negotiable Algorithm Invariants

The main algorithm cannot change. Refactor the code, rename variables, generalize I/O, and expose knobs through config, but preserve the mathematical model.

Required model structure:

```text
Y(x,k) = B(x) * S(x,k)
Z(x,k) = mu(k) + r(x,k)
S(x,k) = softmax_time(Z(x,k)) * K
```

The following implementation details must be preserved unless the user explicitly approves a methodological change:

- Use wrapped Gaussian temporal basis functions for time-of-day.
- Use low-rank spatial RBF basis functions with k-means centers.
- Use QR projection/orthonormalization for the spatial basis.
- Use spatial-temporal interaction weights `w` crossed with temporal and spatial bases.
- Center the spatial residual over sensor locations for each time bin.
- Center the global temporal profile `mu` for identifiability.
- Enforce mean preservation with the time softmax: `log_S = Z - logsumexp(Z over time) + log(K)`.
- Include sensor-specific bias `b_s`.
- Include sensor-specific noise `sigma_s`, with MAD-based scales and a noise floor.
- Use the observation model on the log scale with `log(value + offset)`.
- Prediction at grid locations must rebuild/reuse the same basis convention as training, including the QR projection from sensor sites.
- Mean-preserving checks must be emitted for every fit/prediction run.

### What Can Change

These parts should change for the pip package:

- Replace city-specific filenames with config-driven paths.
- Replace PM2.5-specific column names with canonical neutral names: `sensor_id`, `lat`, `lon`, `timestamp_utc`, `value`, and `baseline`.
- Keep PM2.5 only as a documented example controlled by `variable_name` and `variable_units`.
- Replace script-level globals with typed config objects.
- Replace print-only diagnostics with JSON/CSV/PNG/PDF/HTML artifacts.
- Replace per-city scripts with importable modules and a CLI.
- Expose only meaningful knobs through presets and config.
- Make all outputs deterministic when `random_seed` is fixed.
- Make synthetic data independent of private data.

### Suggested Implementation Order

1. Create package skeleton with `pyproject.toml`, `diurnalize/`, `tests/`, and a README.
2. Implement config models and canonical CSV validation.
3. Implement synthetic data generation first, including `null_shape` and `east_west_peaks`.
4. Port basis construction into `basis.py` with unit tests for shapes, circular wrapping, QR projection, and deterministic centers.
5. Port preprocessing into `preprocess.py`, using canonical inputs and strict summaries.
6. Port the PyMC model into `model.py`/`fit.py`, preserving the invariants above.
7. Implement prediction in `predict.py`, preserving the training-grid projection logic and mean-preserving check.
8. Add baseline benchmark models: baseline-only and global diurnal profile.
9. Add validation outputs and static plots.
10. Add report generation.
11. Add Kepler-friendly long CSV/GeoJSON and, optionally, the local temporal-profile server.
12. Add CI with the tiny end-to-end synthetic pipeline.

### Initial Package Skeleton

Create this structure:

```text
diurnalize/
  __init__.py
  basis.py
  benchmarks.py
  cli.py
  config.py
  data.py
  fit.py
  model.py
  plots.py
  predict.py
  preprocess.py
  report.py
  server.py
  synthetic.py
  validate.py
tests/
  test_basis.py
  test_data_schema.py
  test_synthetic_pipeline.py
  test_mean_preserving.py
```

The existing `pip_idea.md` is a planning document, not package documentation. Keep it during development, but create a real `README.md` for users.

### First Milestone Definition Of Done

The first implementation milestone is complete when this works from a fresh checkout:

```bash
pip install -e .
diurnalize generate-demo --output /tmp/diurnalize_demo --scenario null_shape --n-sensors 6 --n-days 2 --grid-resolution 5
diurnalize fit --config /tmp/diurnalize_demo/config.yaml --output /tmp/diurnalize_run --preset quick
diurnalize predict --run /tmp/diurnalize_run --grid /tmp/diurnalize_demo/baseline_grid.csv --output /tmp/diurnalize_run/predictions
diurnalize validate --run /tmp/diurnalize_run --output /tmp/diurnalize_run/validation
diurnalize report --run /tmp/diurnalize_run --output /tmp/diurnalize_run/report.html
```

The run should produce:

- `manifest.json`
- `preprocessing_summary.json`
- `diagnostics_summary.json`
- `convergence_summary.csv`
- `prediction_grid_summary.csv`
- `mean_preserving_check.csv`
- long prediction CSV with `value_*` columns
- NetCDF prediction output
- PNG and PDF validation plots
- `report.html`

### Guardrails For The Implementing Agent

- Do not silently alter the main algorithm to make tests pass faster.
- Do not keep any dependency on private city data, GHAP data, Replica data, or PurpleAir-specific columns.
- Do not preserve PM2.5-specific names in core output columns.
- Do not fill missing baseline values for prediction locations; exclude and report them.
- Do not add column guessing. Headers are canonical with case-insensitive matching only.
- Do not implement a large refactor of the old repository. This is a new clean package.
- When porting code, keep a short comment naming the old source file if that helps future auditing.
