from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def train_content_tfidf(books: pd.DataFrame) -> tuple[TfidfVectorizer, np.ndarray, list[int]]:
    corpus = (
        books["title"].fillna("")
        + " "
        + books["author"].fillna("")
        + " "
        + books["description"].fillna("").str.slice(0, 4000)
    )
    ids = books["book_id"].tolist()
    vec = TfidfVectorizer(max_features=5000, min_df=1, stop_words="english")
    mat = vec.fit_transform(corpus)
    return vec, mat, ids


def recommend_content(
    mat,
    book_id_to_row: dict[int, int],
    purchased_book_ids: list[int],
    book_ids: list[int],
    top_k: int,
) -> list[int]:
    if not purchased_book_ids:
        return book_ids[:top_k]
    row_idxs = [book_id_to_row[b] for b in purchased_book_ids if b in book_id_to_row]
    if not row_idxs:
        return book_ids[:top_k]
    prof = np.asarray(mat[row_idxs].mean(axis=0))
    sims = linear_kernel(prof, mat).ravel()
    order = np.argsort(-sims)
    out = []
    purchased = set(purchased_book_ids)
    for idx in order:
        bid = book_ids[int(idx)]
        if bid not in purchased:
            out.append(bid)
        if len(out) >= top_k:
            break
    return out
