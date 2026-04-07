"""
DAG semanal: treina múltiplos algoritmos e registra métricas no MLflow.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "bookstore-ml",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def run_train() -> None:
    import subprocess
    import sys

    r = subprocess.run([sys.executable, "-m", "src.training.train"], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        raise RuntimeError("train failed")


with DAG(
    dag_id="dag_train_model",
    default_args=default_args,
    description="Treina modelos comparáveis e envia runs ao MLflow",
    schedule_interval="@weekly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ml", "training"],
) as dag:
    PythonOperator(task_id="train_models", python_callable=run_train)
