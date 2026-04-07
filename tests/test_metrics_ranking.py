"""Testes unitários de métricas de ranking offline."""

import numpy as np
from src.training.metrics_ranking import (
    average_precision,
    dcg_at_k,
    mean_average_precision,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_k_basic():
    assert precision_at_k([1, 2, 3], {1, 9}, 2) == 0.5
    assert precision_at_k([], {1}, 5) == 0.0
    assert precision_at_k([1], {1}, 0) == 0.0


def test_recall_at_k():
    assert recall_at_k([1, 2, 3], {1, 2}, 2) == 1.0
    assert recall_at_k([1], {1, 2}, 5) == 0.5
    assert recall_at_k([1], set(), 5) == 0.0


def test_dcg_at_k():
    assert dcg_at_k([], 5) == 0.0
    assert dcg_at_k([1.0, 0.0], 2) > 0.0


def test_ndcg_at_k():
    assert ndcg_at_k([1, 2, 3], {2}, 3) >= 0.0
    assert ndcg_at_k([9, 9, 9], {1}, 3) == 0.0


def test_average_precision_and_map():
    assert average_precision([1, 2, 3], {1}) > 0.0
    assert average_precision([9], set()) == 0.0
    assert mean_average_precision([], []) == 0.0
    assert mean_average_precision([[1, 2]], [{1}]) > 0.0


def test_dcg_log_weights():
    scores = [3.0, 2.0, 1.0]
    d = dcg_at_k(scores, 3)
    assert isinstance(d, float)
    assert np.isfinite(d)
