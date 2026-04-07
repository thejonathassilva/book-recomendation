"""
DAG pós-treino: avaliação offline e decisão de promoção (integração com MLflow).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "bookstore-ml",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def run_evaluate() -> None:
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "-m", "src.training.evaluate", "--k", "10"],
        capture_output=True,
        text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)


with DAG(
    dag_id="dag_evaluate_model",
    default_args=default_args,
    description="Avalia métricas offline após treino",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ml", "evaluation"],
) as dag:
    PythonOperator(task_id="evaluate_offline", python_callable=run_evaluate)
