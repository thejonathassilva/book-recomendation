"""
DAG diária: pré-computa recomendações e grava no Redis (warm cache).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "bookstore-ml",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def precompute_recommendations(limit_users: int = 500, rec_limit: int = 50) -> None:
    from sqlalchemy.orm import Session

    from src.data.database import SessionLocal
    from src.data.models import User
    from src.recommendation.engine import EngineConfig, RecommendationEngine

    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        print("REDIS_URL not set; skip cache warm.")
        return
    import redis

    r = redis.from_url(url, decode_responses=True)
    db: Session = SessionLocal()
    try:
        users = db.query(User).order_by(User.user_id).limit(limit_users).all()
        engine = RecommendationEngine(db, EngineConfig())
        for u in users:
            pairs = engine.recommend(u.user_id, limit=rec_limit, use_cache=False)
            payload = {"items": [[b.book_id, float(s)] for b, s in pairs]}
            r.setex(f"rec:{u.user_id}:{rec_limit}", 3600, json.dumps(payload))
        print(f"Warm cache for {len(users)} users.")
    finally:
        db.close()


with DAG(
    dag_id="dag_compute_recommendations",
    default_args=default_args,
    description="Pré-computa top-N recomendações por usuário",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["recommendations", "redis"],
) as dag:
    PythonOperator(task_id="compute_recs", python_callable=precompute_recommendations)
