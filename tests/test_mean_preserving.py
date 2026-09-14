import numpy as np

from diurnalize.basis import softmax_time


def test_shape_mean_is_one_for_each_location():
    z = np.array([[[0.0, 1.0, 2.0], [2.0, 1.0, 0.0]]])
    s = softmax_time(z)
    np.testing.assert_allclose(s.mean(axis=-1), [[1.0, 1.0]])
