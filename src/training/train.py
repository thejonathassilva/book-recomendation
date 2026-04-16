from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import yaml
from sqlalchemy import create_engine, text

from src.training.algorithms import collaborative as collab
from src.training.algorithms import content_based as cb
from src.training.algorithms import hybrid as hyb
from src.training.algorithms import matrix_factorization as mf
from src.training.algorithms import neural_mlp as ncf
from src.training.evaluate import evaluate_algorithm, holdout_per_user
from src.training.feature_engineering import build_interaction_sample


def _log_eval_metrics(
    algo_name: str,
    rec_fn,
    users_to_test: list[int],
    test_rel: dict,
    k_list: list[int],
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for k in k_list:
        m = evaluate_algorithm(algo_name, rec_fn, users_to_test, test_rel, k)
        metrics[f"precision_at_{k}"] = float(m[f"precision_at_{k}"])
        metrics[f"recall_at_{k}"] = float(m[f"recall_at_{k}"])
        metrics[f"ndcg_at_{k}"] = float(m[f"ndcg_at_{k}"])
    m_map = evaluate_algorithm(algo_name, rec_fn, users_to_test, test_rel, max(k_list))
    metrics["map"] = float(m_map["map"])
    mlflow.log_metrics(metrics)
    return metrics


def _print_presentation_summary(eval_export: dict[str, dict[str, float]], cfg: dict) -> None:
    if not eval_export:
        return
    pres = cfg.get("presentation") or {}
    k = int(pres.get("primary_k", 10))
    key = f"precision_at_{k}"
    k_list = cfg.get("evaluation", {}).get("k_list") or []
    if k_list and k not in k_list:
        print(
            f"\n[config] presentation.primary_k={k} not in evaluation.k_list {k_list}.",
            file=sys.stderr,
        )
    print(f"\n=== {key} (top-{k}) ===")
    print(f"Fraction of relevant items in top-{k} (0..1); offline ranking metric.\n")
    rows: list[tuple[str, float]] = []
    for algo, metrics in sorted(eval_export.items()):
        v = metrics.get(key)
        if v is not None:
            rows.append((algo, float(v)))
    if not rows:
        print(f"(Sem valores para {key}. Inclua {k} em evaluation.k_list.)")
        return
    w = max(len(a) for a, _ in rows)
    for algo, v in rows:
        print(f"  {algo.ljust(w)}  {v:.4f}")
    best = max(rows, key=lambda x: x[1])
    print(f"\nMelhor (por {key}): {best[0]} ({best[1]:.4f})")


def _write_train_metrics_export(path: Path, algorithms: dict[str, dict[str, float]]) -> None:
    if not algorithms:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    payload = {
        "generated_at": now.isoformat(),
        "generated_at_unix": now.timestamp(),
        "algorithms": algorithms,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Offline evaluation metrics exported to", path, "(scraped via API /metrics -> Prometheus)")


def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _remap(train_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, int], dict[int, int]]:
    u_ids = sorted(train_df["user_id"].unique())
    b_ids = sorted(train_df["book_id"].unique())
    u_map = {u: i for i, u in enumerate(u_ids)}
    b_map = {b: i for i, b in enumerate(b_ids)}
    out = train_df.copy()
    out["u_idx"] = out["user_id"].map(u_map)
    out["b_idx"] = out["book_id"].map(b_map)
    return out, u_map, b_map


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/train_config.yaml")
    parser.add_argument("--mock", action="store_true", help="Gera dados sintéticos mínimos se DB vazio")
    args = parser.parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        alt = Path(os.environ.get("CONFIG_DIR", "config")).parent / args.config
        if alt.is_file():
            cfg_path = alt
        else:
            cfg_path = Path("config/train_config.yaml")
    cfg = _load_config(str(cfg_path))

    url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://bookstore:bookstore@localhost:5432/bookstore")
    engine = create_engine(url)
    try:
        purchases = pd.read_sql_query(text("SELECT user_id, book_id, purchase_date, price_paid FROM purchases"), engine)
        books = pd.read_sql_query(text("SELECT * FROM books"), engine)
    except Exception as e:
        print("DB unavailable:", e, file=sys.stderr)
        purchases, books = pd.DataFrame(), pd.DataFrame()

    if purchases.empty and args.mock:
        rng = np.random.default_rng(0)
        books = pd.DataFrame(
            {
                "book_id": range(300),
                "title": [f"Book {i}" for i in range(300)],
                "author": [f"Author {i % 20}" for i in range(300)],
                "description": ["text " * 10 for _ in range(300)],
                "category_id": rng.integers(0, 10, size=300),
                "price": rng.uniform(10, 100, size=300),
            }
        )
        rows = []
        for u in range(200):
            picks = rng.choice(300, size=15, replace=False)
            for b in picks:
                rows.append({"user_id": u, "book_id": int(b), "price_paid": 50.0})
        purchases = pd.DataFrame(rows)

    if purchases.empty:
        print("No purchases to train; use --mock or seed the database.", file=sys.stderr)
        sys.exit(1)

    if books.empty and not purchases.empty:
        bids = sorted(purchases["book_id"].unique().tolist())
        books = pd.DataFrame(
            {
                "book_id": bids,
                "title": [f"Book {i}" for i in bids],
                "author": "Unknown",
                "description": "synthetic placeholder",
                "category_id": 0,
                "price": 29.9,
            }
        )

    train_df, test_rel = holdout_per_user(
        purchases,
        test_ratio=float(cfg["data"]["test_size"]),
        seed=int(cfg["data"]["random_state"]),
    )
    users_to_test = [u for u, rel in test_rel.items() if rel]
    k_list = cfg["evaluation"]["k_list"]
    k_eval = max(k_list)

    tracking = os.environ.get("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking)
    mlflow.set_experiment(cfg.get("mlflow", {}).get("experiment_name", "book-recommendation"))
    batch_tags = {"train_batch_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}

    eval_export: dict[str, dict[str, float]] = {}
    export_path = Path(os.environ.get("TRAIN_METRICS_EXPORT_PATH", "data/train_metrics_last.json"))

    train_r, u_map, b_map = _remap(train_df)
    inv_b = {i: b for b, i in b_map.items()}
    n_users, n_books = len(u_map), len(b_map)
    mat = collab.build_user_book_matrix(
        train_r.rename(columns={"u_idx": "user_id", "b_idx": "book_id"})[["user_id", "book_id"]],
        n_users,
        n_books,
    )

    # Content-based
    with mlflow.start_run(run_name="content_tfidf", tags=batch_tags):
        vec, mat_c, book_ids_c = cb.train_content_tfidf(books) if not books.empty else (None, None, [])
        row_map = {bid: i for i, bid in enumerate(book_ids_c)}

        def rec_content(uid: int) -> list[int]:
            bought = set(train_df[train_df["user_id"] == uid]["book_id"].tolist())
            if vec is None or not book_ids_c:
                return []
            return cb.recommend_content(mat_c, row_map, list(bought), book_ids_c, k_eval * 3)

        eval_export["content_tfidf"] = _log_eval_metrics(
            "content_tfidf", rec_content, users_to_test, test_rel, k_list
        )
        mlflow.log_params({"algo": "tfidf", "decay_rate": cfg["hybrid"]["decay_rate"]})

    # User-user CF
    with mlflow.start_run(run_name="collaborative_user_user", tags=batch_tags):
        def rec_cf(uid: int) -> list[int]:
            if uid not in u_map:
                return []
            uix = u_map[uid]
            bought = set(train_df[train_df["user_id"] == uid]["book_id"].tolist())
            idxs = collab.recommend_user_user(mat, uix, {b_map[b] for b in bought if b in b_map}, k_eval * 3)
            return [inv_b[i] for i in idxs if i in inv_b]

        eval_export["collaborative_user_user"] = _log_eval_metrics(
            "collaborative_user_user", rec_cf, users_to_test, test_rel, k_list
        )
        mlflow.log_params({"algo": "user_user_cf"})

    # SVD
    with mlflow.start_run(run_name="matrix_svd", tags=batch_tags):
        train_idx_df = train_r.rename(columns={"u_idx": "user_id", "b_idx": "book_id"})[["user_id", "book_id"]]
        _, uf, bf, _ = mf.train_svd(train_idx_df, n_users, n_books, n_components=64)

        def rec_svd(uid: int) -> list[int]:
            if uid not in u_map:
                return []
            uix = u_map[uid]
            bought = set(train_df[train_df["user_id"] == uid]["book_id"].tolist())
            idxs = mf.recommend_svd(uix, uf, bf, {b_map[b] for b in bought if b in b_map}, k_eval * 3)
            return [inv_b[i] for i in idxs if i in inv_b]

        eval_export["matrix_svd"] = _log_eval_metrics("matrix_svd", rec_svd, users_to_test, test_rel, k_list)
        mlflow.log_params({"algo": "truncated_svd", "n_factors": 64})

    # Hybrid XGBoost + Neural MLP on interaction sample (cap configurável para caber no case + seed padrão).
    raw_cap = (cfg.get("training") or {}).get("interaction_sample_max_users", 2000)
    max_users_sample: int | None = None if raw_cap is None else int(raw_cap)
    sample = build_interaction_sample(train_df, books, max_users=max_users_sample)
    if not sample.empty:
        xgb_model, meta = hyb.train_xgboost_ranker(sample)
        mlp_model, meta_mlp = ncf.train_mlp(sample)

        if xgb_model is not None and meta:
            feats = meta["features"]

            with mlflow.start_run(run_name="hybrid_xgboost", tags=batch_tags):

                def rec_xgb(uid: int) -> list[int]:
                    bought = set(train_df[train_df["user_id"] == uid]["book_id"].tolist())
                    return hyb.recommend_xgb(xgb_model, feats, uid, sample, bought, k_eval * 3)

                eval_export["hybrid_xgboost"] = _log_eval_metrics(
                    "hybrid_xgboost", rec_xgb, users_to_test, test_rel, k_list
                )
                mlflow.log_params({"algo": "xgboost", "user_weight": cfg["hybrid"]["user_history_weight"]})

        if mlp_model is not None and meta_mlp:
            feats2 = meta_mlp["features"]

            with mlflow.start_run(run_name="neural_mlp_cf", tags=batch_tags):

                def rec_mlp(uid: int) -> list[int]:
                    bought = set(train_df[train_df["user_id"] == uid]["book_id"].tolist())
                    return ncf.recommend_mlp(mlp_model, feats2, uid, sample, bought, k_eval * 3)

                eval_export["neural_mlp_cf"] = _log_eval_metrics(
                    "neural_mlp_cf", rec_mlp, users_to_test, test_rel, k_list
                )
                mlflow.log_params({"algo": "mlp_classifier"})

    _write_train_metrics_export(export_path, eval_export)
    _print_presentation_summary(eval_export, cfg)
    print("Training runs logged to MLflow at", tracking)


if __name__ == "__main__":
    main()
