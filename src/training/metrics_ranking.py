from __future__ import annotations

import numpy as np


def precision_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    rec = recommended[:k]
    if not rec or k <= 0:
        return 0.0
    hits = len(set(rec) & relevant)
    return hits / k


def recall_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    rec = set(recommended[:k])
    return len(rec & relevant) / len(relevant)


def dcg_at_k(scores: list[float], k: int) -> float:
    s = np.asarray(scores[:k], dtype=float)
    if s.size == 0:
        return 0.0
    return float(np.sum(s / np.log2(np.arange(2, s.size + 2))))


def ndcg_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    gains = [1.0 if i in relevant else 0.0 for i in recommended[:k]]
    ideal = sorted(gains, reverse=True)
    dcg = dcg_at_k(gains, k)
    idcg = dcg_at_k(ideal, k)
    return float(dcg / idcg) if idcg > 0 else 0.0


def average_precision(recommended: list[int], relevant: set[int]) -> float:
    if not relevant:
        return 0.0
    hits = 0
    prec_sum = 0.0
    for i, item in enumerate(recommended, start=1):
        if item in relevant:
            hits += 1
            prec_sum += hits / i
    return prec_sum / len(relevant)


def mean_average_precision(all_recommended: list[list[int]], all_relevant: list[set[int]]) -> float:
    if not all_recommended:
        return 0.0
    return float(
        np.mean([average_precision(rec, rel) for rec, rel in zip(all_recommended, all_relevant)])
    )
