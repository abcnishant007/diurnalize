from diurnalize.synthetic import generate_demo


def test_generate_demo_outputs(tmp_path):
    generate_demo(tmp_path, scenario="null_shape", n_sensors=6, n_days=2, grid_resolution=5)
    assert (tmp_path / "observations.csv").exists()
    assert (tmp_path / "baseline_grid.csv").exists()
    assert (tmp_path / "config.yaml").exists()
