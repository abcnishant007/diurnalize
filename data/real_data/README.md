# Real Data Samples

This directory is reserved for local, uncommitted real-data samples used during development and smoke testing.

The repository does not ship real sensor or baseline data files. To obtain a comparable sample for an American city, contact `abcnishant007`, or assemble public/accessible datasets following the associated paper: a baseline product such as GHAP or a comparable gridded mean field, plus PurpleAir-style low-cost sensor observations with timestamps and coordinates.

Expected canonical package schemas are documented in the project README:

- observations: `sensor_id,lat,lon,timestamp_utc,value`
- baseline grid: `lat,lon,baseline`

Files placed under this directory are ignored by git.
