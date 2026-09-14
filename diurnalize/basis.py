"""Basis construction for the mean-preserving shape model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import qr
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans


@dataclass
class SpatialBasis:
    centers: np.ndarray
    phi_sensors: np.ndarray
    r_matrix: np.ndarray
    length_scale: float


def wrapped_gaussian_temporal_basis(k: int, n_basis: int) -> np.ndarray:
    """Wrapped Gaussian temporal basis from the Cleveland reference model."""
    centers = np.arange(n_basis) * (k / n_basis)
    time_scale = k / (n_basis * 1.65)
    k_idx = np.arange(k)[:, None]
    dist = np.abs(k_idx - centers[None, :])
    dist_wrapped = np.minimum(dist, k - dist)
    basis = np.exp(-0.5 * (dist_wrapped / time_scale) ** 2)
    return basis / basis.sum(axis=0, keepdims=True)


def fit_spatial_basis(sensor_coords: np.ndarray, n_basis: int, length_scale: float, random_seed: int = 42) -> SpatialBasis:
    n_basis_eff = min(int(n_basis), len(sensor_coords))
    if len(sensor_coords) > n_basis_eff:
        centers = KMeans(n_clusters=n_basis_eff, random_state=random_seed, n_init=10).fit(sensor_coords).cluster_centers_
    else:
        centers = sensor_coords[:n_basis_eff].copy()
    dist = cdist(sensor_coords, centers, metric="euclidean")
    phi_raw = np.exp(-0.5 * (dist / length_scale) ** 2)
    q, r = qr(phi_raw, mode="economic")
    return SpatialBasis(centers=centers, phi_sensors=q, r_matrix=r, length_scale=length_scale)


def project_spatial_basis(coords: np.ndarray, basis: SpatialBasis) -> np.ndarray:
    """Project new points into the training QR basis convention."""
    dist = cdist(coords, basis.centers, metric="euclidean")
    phi_raw = np.exp(-0.5 * (dist / basis.length_scale) ** 2)
    return phi_raw @ np.linalg.inv(basis.r_matrix)


def softmax_time(z: np.ndarray) -> np.ndarray:
    zmax = z.max(axis=-1, keepdims=True)
    logsum = np.log(np.exp(z - zmax).sum(axis=-1, keepdims=True)) + zmax
    return np.exp(z - logsum + np.log(z.shape[-1]))
