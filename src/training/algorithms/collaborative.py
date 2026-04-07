from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def build_user_book_matrix(purchases: pd.DataFrame, n_users: int, n_books: int) -> np.ndarray:
    mat = np.zeros((n_users, n_books), dtype=np.float32)
    for row in purchases.itertuples(index=False):
        u, b = int(row.user_id), int(row.book_id)
        if 0 <= u < n_users and 0 <= b < n_books:
            mat[u, b] += 1.0
    return mat


def recommend_user_user(
    mat: np.ndarray,
    user_id: int,
    purchased: set[int],
    top_k: int,
) -> list[int]:
    if user_id >= mat.shape[0]:
        return []
    sims = cosine_similarity(mat[user_id : user_id + 1], mat).ravel()
    sims[user_id] = 0.0
    neigh = np.argsort(-sims)[:50]
    scores = mat[neigh].sum(axis=0)
    order = np.argsort(-scores)
    out: list[int] = []
    for b in order:
        if int(b) not in purchased and scores[b] > 0:
            out.append(int(b))
        if len(out) >= top_k:
            break
    return out
