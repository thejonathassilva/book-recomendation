import numpy as np
from src.monitoring.drift_detection import psi


def test_psi_empty():
    assert psi(np.array([]), np.array([1.0])) == 0.0
    assert psi(np.array([1.0]), np.array([])) == 0.0


def test_psi_stable():
    x = np.random.default_rng(0).normal(size=500)
    v = float(psi(x, x))
    assert v >= 0.0
    assert np.isfinite(v)


def test_psi_single_bin_edge():
    x = np.ones(20)
    y = np.ones(20) * 2
    v = float(psi(x, y))
    assert np.isfinite(v)
