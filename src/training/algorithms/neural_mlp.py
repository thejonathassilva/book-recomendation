from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier


def train_mlp(df: pd.DataFrame, random_state: int = 42):
    if df.empty or df["label"].nunique() < 2:
        return None, {}
    feature_cols = [c for c in df.columns if c not in ("label", "user_id", "book_id")]
    X = df[feature_cols].astype(float)
    y = df["label"].astype(int)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=random_state)
    mlp = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        max_iter=200,
        random_state=random_state,
        early_stopping=True,
        validation_fraction=0.1,
    )
    mlp.fit(X_train, y_train)
    return mlp, {"features": feature_cols}


def recommend_mlp(
    model: MLPClassifier,
    feature_cols: list[str],
    user_id: int,
    candidate_books_df: pd.DataFrame,
    purchased: set[int],
    top_k: int,
) -> list[int]:
    sub = candidate_books_df[candidate_books_df["user_id"] == user_id]
    if sub.empty:
        return []
    X = sub[feature_cols].astype(float)
    prob = model.predict_proba(X)[:, 1]
    order = np.argsort(-prob)
    out: list[int] = []
    for i in order:
        bid = int(sub.iloc[int(i)]["book_id"])
        if bid not in purchased:
            out.append(bid)
        if len(out) >= top_k:
            break
    return out
