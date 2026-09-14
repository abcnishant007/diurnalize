# Diurnalize

Diurnalize provides a reusable implementation of mean-preserving diurnal disaggregation. It decomposes a positive environmental variable into a spatial baseline level `B(x)` and a local time-of-day multiplier `S(x,k)`:

```text
Y(x,k) = B(x) * S(x,k)
```

The hierarchical shape model uses wrapped Gaussian temporal bases, low-rank spatial RBF bases with k-means centers and QR projection, sensor-specific bias, sensor-specific noise, and a time softmax so each predicted daily shape has mean 1.

## Quick Start

```bash
pip install -e .
diurnalize generate-demo --output /tmp/diurnalize_demo --scenario null_shape --n-sensors 6 --n-days 2 --grid-resolution 5
diurnalize fit --config /tmp/diurnalize_demo/config.yaml --output /tmp/diurnalize_run --preset quick
diurnalize predict --run /tmp/diurnalize_run --grid /tmp/diurnalize_demo/baseline_grid.csv --output /tmp/diurnalize_run/predictions
diurnalize validate --run /tmp/diurnalize_run --output /tmp/diurnalize_run/validation
diurnalize report --run /tmp/diurnalize_run --output /tmp/diurnalize_run/report.html
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

## Citation

If you find this package or the associated methods useful, please consider citing the associated paper. Paper reproduction workflows are intentionally kept outside this package.
