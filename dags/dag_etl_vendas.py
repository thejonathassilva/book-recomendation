"""
DAG diária: ETL de vendas e agregados para feature store (placeholder chamando SQL).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "bookstore-ml",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def run_etl() -> None:
    import os

    from sqlalchemy import create_engine, text

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set; ETL skipped.")
        return
    eng = create_engine(url)
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("ETL vendas: conexão OK (estender com agregações em purchases).")


with DAG(
    dag_id="dag_etl_vendas",
    default_args=default_args,
    description="Extrai novas vendas e atualiza agregados",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "bookstore"],
) as dag:
    PythonOperator(task_id="etl_vendas_task", python_callable=run_etl)
