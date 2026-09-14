import pandas as pd
import pytest

from diurnalize.data import load_sensor_csv


def test_sensor_schema_rejects_spaces(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"sensor id": ["a"], "lat": [1], "lon": [2], "timestamp_utc": ["2023-01-01T00:00:00Z"], "value": [1]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="sensor_id"):
        load_sensor_csv(path)


def test_sensor_schema_accepts_case_fold(tmp_path):
    path = tmp_path / "ok.csv"
    pd.DataFrame({"Sensor_ID": ["a"], "LAT": [1], "LON": [2], "TIMESTAMP_UTC": ["2023-01-01T00:00:00Z"], "VALUE": [1]}).to_csv(path, index=False)
    df = load_sensor_csv(path)
    assert list(df.columns[:5]) == ["sensor_id", "lat", "lon", "timestamp_utc", "value"]
