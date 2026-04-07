from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD


def train_svd(purchases: pd.DataFrame, n_users: int, n_books: int, n_components: int = 64):
    rows, cols, data = [], [], []
    for row in purchases.itertuples(index=False):
        u, b = int(row.user_id), int(row.book_id)
        if 0 <= u < n_users and 0 <= b < n_books:
            rows.append(u)
            cols.append(b)
            data.append(1.0)
    mat = csr_matrix((data, (rows, cols)), shape=(n_users, n_books))
    svd = TruncatedSVD(n_components=min(n_components, min(n_users, n_books) - 1), random_state=42)
    user_factors = svd.fit_transform(mat)
    book_factors = svd.components_.T
    return svd, user_factors, book_factors, mat


def recommend_svd(
    user_id: int,
    user_factors: np.ndarray,
    book_factors: np.ndarray,
    purchased: set[int],
    top_k: int,
) -> list[int]:
    if user_id >= user_factors.shape[0]:
        return []
    scores = user_factors[user_id] @ book_factors.T
    order = np.argsort(-scores)
    out: list[int] = []
    for b in order:
        if int(b) not in purchased:
            out.append(int(b))
        if len(out) >= top_k:
            break
    return out
