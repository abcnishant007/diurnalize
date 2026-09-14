import numpy as np

from diurnalize.basis import fit_spatial_basis, project_spatial_basis, softmax_time, wrapped_gaussian_temporal_basis


def test_temporal_basis_wraps_and_normalizes():
    basis = wrapped_gaussian_temporal_basis(48, 4)
    assert basis.shape == (48, 4)
    np.testing.assert_allclose(basis.sum(axis=0), np.ones(4))
    assert basis[0, 0] > basis[24, 0]


def test_spatial_projection_shapes():
    coords = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    basis = fit_spatial_basis(coords, 3, 0.5, 42)
    assert basis.phi_sensors.shape == (4, 3)
    assert project_spatial_basis(coords[:2], basis).shape == (2, 3)


def test_softmax_time_is_mean_preserving():
    z = np.random.default_rng(1).normal(size=(3, 5, 48))
    s = softmax_time(z)
    np.testing.assert_allclose(s.mean(axis=-1), np.ones((3, 5)), rtol=1e-10)
