from __future__ import annotations

import argparse
import json
import os
import random
from collections import defaultdict

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from src.training.metrics_ranking import mean_average_precision, ndcg_at_k, precision_at_k, recall_at_k


def _remap_ids(purchases: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, int], dict[int, int]]:
    u_ids = sorted(purchases["user_id"].unique())
    b_ids = sorted(purchases["book_id"].unique())
    u_map = {u: i for i, u in enumerate(u_ids)}
    b_map = {b: i for i, b in enumerate(b_ids)}
    p = purchases.copy()
    p["u_idx"] = p["user_id"].map(u_map)
    p["b_idx"] = p["book_id"].map(b_map)
    return p, u_map, b_map


def holdout_per_user(
    purchases: pd.DataFrame, test_ratio: float = 0.2, seed: int = 42
) -> tuple[pd.DataFrame, dict[int, set[int]]]:
    rng = random.Random(seed)
    train_purchases: list[tuple[int, int]] = []
    test_relevant: dict[int, set[int]] = defaultdict(set)
    for uid, g in purchases.groupby("user_id"):
        books = g["book_id"].tolist()
        rng.shuffle(books)
        n_test = max(1, int(len(books) * test_ratio)) if len(books) > 1 else 0
        test_books = set(books[:n_test]) if n_test else set()
        train_books = books[n_test:] if n_test else books
        for b in train_books:
            train_purchases.append((uid, b))
        for b in test_books:
            test_relevant[uid].add(b)
    train_df = pd.DataFrame(train_purchases, columns=["user_id", "book_id"])
    return train_df, dict(test_relevant)


def evaluate_algorithm(name: str, recommend_fn, users_to_test: list[int], test_relevant: dict, k: int) -> dict:
    precs, recalls, ndcgs, rec_lists, rel_lists = [], [], [], [], []
    for uid in users_to_test:
        rel = test_relevant.get(uid, set())
        if not rel:
            continue
        rec = recommend_fn(uid)
        precs.append(precision_at_k(rec, rel, k))
        recalls.append(recall_at_k(rec, rel, k))
        ndcgs.append(ndcg_at_k(rec, rel, k))
        rec_lists.append(rec)
        rel_lists.append(rel)
    return {
        f"precision_at_{k}": float(np.mean(precs)) if precs else 0.0,
        f"recall_at_{k}": float(np.mean(recalls)) if recalls else 0.0,
        f"ndcg_at_{k}": float(np.mean(ndcgs)) if ndcgs else 0.0,
        "map": mean_average_precision(rec_lists, rel_lists) if rec_lists else 0.0,
        "algo": name,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-version", default="latest")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://bookstore:bookstore@localhost:5432/bookstore")
    engine = create_engine(url)
    purchases = pd.read_sql_query(text("SELECT user_id, book_id FROM purchases"), engine)
    if purchases.empty:
        print(json.dumps({"error": "no purchases"}))
        return
    train_df, test_rel = holdout_per_user(purchases)
    users_to_test = [u for u, rel in test_rel.items() if rel]

    # Baseline popular
    pop = train_df["book_id"].value_counts().index.tolist()

    def popular_recommend(uid: int) -> list[int]:
        bought = set(train_df[train_df["user_id"] == uid]["book_id"].tolist())
        out = []
        for b in pop:
            if b not in bought:
                out.append(int(b))
            if len(out) >= args.k * 3:
                break
        return out

    metrics = evaluate_algorithm("popular_baseline", popular_recommend, users_to_test, test_rel, args.k)
    metrics["model_version"] = args.model_version
    print(json.dumps(metrics, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)


if __name__ == "__main__":
    main()
