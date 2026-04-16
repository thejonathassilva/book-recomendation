"""
Promoção ao MLflow Model Registry (melhor run por métrica).

Encaixe com a API: depois de `mlflow.sklearn.log_model` / `pyfunc.log_model` no treino, o run passa a
ter artefato em `runs:/<id>/model` — aí `--promote-if-better` cria versão em *Production*.
A inferência online fica reservada em `src/recommendation/online_ranker_gateway.py` + flag
`USE_MLFLOW_ONLINE_RANKER` (hoje stub; a API segue no motor heurístico até implementar o load).

Exemplo: python -m src.training.register --metric precision_at_10
         python -m src.training.register --promote-if-better --metric precision_at_10
"""

from __future__ import annotations

import argparse
import os

from mlflow.tracking import MlflowClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seleciona melhor run do experimento e opcionalmente promove ao Model Registry.",
    )
    parser.add_argument("--promote-if-better", action="store_true")
    parser.add_argument("--metric", default="precision_at_10")
    parser.add_argument("--experiment", default="book-recommendation")
    parser.add_argument("--model-name", default="book-recommender")
    args = parser.parse_args()

    tracking = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    client = MlflowClient(tracking_uri=tracking)
    exp = client.get_experiment_by_name(args.experiment)
    if exp is None:
        print("Experiment not found:", args.experiment)
        return

    metric_key = f"metrics.{args.metric}"
    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=[f"{metric_key} DESC"],
        max_results=10,
    )
    if not runs:
        print("No runs found.")
        return

    best = runs[0]
    print("Best run:", best.info.run_id, best.data.metrics.get(args.metric))

    if not args.promote_if_better:
        return

    try:
        client.create_registered_model(args.model_name)
    except Exception:
        pass

    source = f"runs:/{best.info.run_id}/model"
    try:
        mv = client.create_model_version(name=args.model_name, source=source, run_id=best.info.run_id)
        client.transition_model_version_stage(
            name=args.model_name,
            version=mv.version,
            stage="Production",
            archive_existing_versions=True,
        )
        print("Promoted version", mv.version, "to Production")
    except Exception as e:
        print("Register skipped (no model artifact on run; log model in train).", e)


if __name__ == "__main__":
    main()
