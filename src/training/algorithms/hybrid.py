from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split


def train_xgboost_ranker(df: pd.DataFrame, random_state: int = 42):
    if df.empty or df["label"].nunique() < 2:
        return None, {}
    feature_cols = [c for c in df.columns if c not in ("label", "user_id", "book_id")]
    X = df[feature_cols].astype(float)
    y = df["label"].astype(int)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=random_state)
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=random_state,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model, {"features": feature_cols}


def recommend_xgb(
    model: xgb.XGBClassifier,
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
