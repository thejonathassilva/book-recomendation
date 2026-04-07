"""Testes unitários dos algoritmos de treino (TF-IDF, CF, SVD, XGB, MLP)."""

import numpy as np
import pandas as pd
from src.training.algorithms.collaborative import build_user_book_matrix, recommend_user_user
from src.training.algorithms.content_based import recommend_content, train_content_tfidf
from src.training.algorithms.hybrid import recommend_xgb, train_xgboost_ranker
from src.training.algorithms.matrix_factorization import recommend_svd, train_svd
from src.training.algorithms.neural_mlp import recommend_mlp, train_mlp


def test_train_content_tfidf_and_recommend():
    books = pd.DataFrame(
        {
            "book_id": [1, 2, 3],
            "title": ["alpha story", "beta tale", "gamma novel"],
            "author": ["A", "A", "B"],
            "description": ["fantasy epic dragon", "sci fi space", "romance love"],
        }
    )
    vec, mat, ids = train_content_tfidf(books)
    assert mat.shape[0] == 3
    bid2row = {bid: i for i, bid in enumerate(ids)}
    out = recommend_content(mat, bid2row, [1], [1, 2, 3], top_k=2)
    assert len(out) <= 2


def test_recommend_content_empty_purchases():
    books = pd.DataFrame(
        {
            "book_id": [1, 2],
            "title": ["a", "b"],
            "author": ["x", "y"],
            "description": ["d1", "d2"],
        }
    )
    vec, mat, ids = train_content_tfidf(books)
    bid2row = {bid: i for i, bid in enumerate(ids)}
    out = recommend_content(mat, bid2row, [], [1, 2], top_k=1)
    assert out == [1]


def test_collaborative_matrix_and_recommend():
    p = pd.DataFrame({"user_id": [0, 0, 1], "book_id": [1, 2, 2]})
    mat = build_user_book_matrix(p, n_users=2, n_books=4)
    assert mat[0, 1] == 1.0
    out = recommend_user_user(mat, 0, purchased={1, 2}, top_k=2)
    assert isinstance(out, list)


def test_collaborative_user_out_of_range():
    p = pd.DataFrame({"user_id": [0], "book_id": [0]})
    mat = build_user_book_matrix(p, n_users=1, n_books=2)
    assert recommend_user_user(mat, 99, set(), top_k=5) == []


def test_svd_train_recommend():
    p = pd.DataFrame({"user_id": [0, 0, 1, 1], "book_id": [0, 1, 1, 2]})
    svd, uf, bf, _ = train_svd(p, n_users=2, n_books=3, n_components=2)
    assert uf.shape[0] == 2
    rec = recommend_svd(0, uf, bf, purchased={0}, top_k=2)
    assert isinstance(rec, list)


def test_svd_user_oob():
    p = pd.DataFrame({"user_id": [0, 1], "book_id": [0, 1]})
    _, uf, bf, _ = train_svd(p, n_users=2, n_books=3, n_components=1)
    assert recommend_svd(5, uf, bf, set(), top_k=3) == []


def test_xgboost_train_none_single_class():
    df = pd.DataFrame({"user_id": [1, 2], "book_id": [1, 2], "label": [1, 1], "f1": [0.0, 1.0]})
    model, meta = train_xgboost_ranker(df)
    assert model is None
    assert meta == {}


def test_xgboost_train_and_recommend():
    rows = []
    for i in range(60):
        rows.append(
            {
                "user_id": i % 5,
                "book_id": i,
                "label": i % 2,
                "feat_a": float(i % 3),
                "feat_b": float(i % 7),
            }
        )
    df = pd.DataFrame(rows)
    model, meta = train_xgboost_ranker(df, random_state=0)
    assert model is not None
    cand = df[df["user_id"] == 0].copy()
    out = recommend_xgb(model, meta["features"], 0, cand, purchased=set(), top_k=3)
    assert isinstance(out, list)


def test_xgboost_recommend_empty_sub():
    import xgboost as xgb

    model = xgb.XGBClassifier(n_estimators=2, max_depth=2)
    X = np.array([[0.0, 1.0], [1.0, 0.0]])
    y = np.array([0, 1])
    model.fit(X, y)
    empty = pd.DataFrame(columns=["user_id", "book_id", "f1"])
    assert recommend_xgb(model, ["f1"], 1, empty, set(), top_k=5) == []


def test_mlp_train_none():
    df = pd.DataFrame({"user_id": [1], "book_id": [1], "label": [1], "f": [1.0]})
    m, meta = train_mlp(df)
    assert m is None


def test_mlp_train_and_recommend(monkeypatch):
    import src.training.algorithms.neural_mlp as nm
    from sklearn.neural_network import MLPClassifier as SkMLP

    def fast_mlp(**kwargs):
        kwargs["max_iter"] = 25
        kwargs["early_stopping"] = False
        return SkMLP(**kwargs)

    monkeypatch.setattr(nm, "MLPClassifier", fast_mlp)
    rows = []
    for i in range(80):
        rows.append(
            {
                "user_id": i % 4,
                "book_id": i,
                "label": i % 2,
                "f1": float(i % 5),
                "f2": float(i % 3),
            }
        )
    df = pd.DataFrame(rows)
    model, meta = train_mlp(df, random_state=0)
    assert model is not None
    sub = df[df["user_id"] == 0]
    out = recommend_mlp(model, meta["features"], 0, sub, purchased=set(), top_k=2)
    assert isinstance(out, list)


def test_mlp_recommend_empty():
    from sklearn.neural_network import MLPClassifier

    m = MLPClassifier(max_iter=5)
    m.fit(np.array([[0.0], [1.0]]), np.array([0, 1]))
    empty = pd.DataFrame(columns=["user_id", "book_id", "f1"])
    assert recommend_mlp(m, ["f1"], 2, empty, set(), top_k=3) == []
