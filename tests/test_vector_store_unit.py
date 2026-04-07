"""Funções puras de vector_store (sem PostgreSQL)."""

import numpy as np
from src.recommendation import vector_store as vs
from src.recommendation.vector_store import (
    cosine_similarity,
    mean_embedding,
)


def test_parse_vector_variants():
    assert vs._parse_vector(None) is None
    assert vs._parse_vector([1.0, 2.0]) is not None
    assert vs._parse_vector(np.array([1.0, 2.0])) is not None
    assert vs._parse_vector("[0.5, 0.5]") is not None
    assert vs._parse_vector("not a vector") is None


def test_mean_embedding_and_cosine():
    assert mean_embedding([]) is None
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    m = mean_embedding([a, b])
    assert m is not None
    assert cosine_similarity(a, b) == 1.0
    assert cosine_similarity(np.zeros(3), np.ones(3)) == 0.0
