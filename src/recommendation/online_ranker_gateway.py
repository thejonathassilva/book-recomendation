"""
Esqueleto para ranker online alimentado pelo MLflow Model Registry.

Hoje: com USE_MLFLOW_ONLINE_RANKER ligado, a API continua servindo o RecommendationEngine;
try_mlflow_online_recommendations devolve sempre None até existir log_model + artefato carregável.

Encaixe planejado: train.py grava modelo → register.py --promote-if-better → URI em MLFLOW_MODEL_URI
→ este módulo carrega e ranqueia → lista (Book, score) ou None em falha (fallback para o engine).
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.data.models import Book

log = logging.getLogger(__name__)


def mlflow_online_ranker_enabled() -> bool:
    v = os.environ.get("USE_MLFLOW_ONLINE_RANKER", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def public_ranker_status() -> dict[str, str]:
    """Exposto em GET /health para observabilidade e para alinhar README/slides."""
    if not mlflow_online_ranker_enabled():
        return {
            "backend": "heuristic",
            "mlflow_online_ranker": "off",
        }
    return {
        "backend": "heuristic",
        "mlflow_online_ranker": "stub",
        "next_step": "log_model no treino; register.py --promote-if-better; inferir aqui ou fallback",
    }


def try_mlflow_online_recommendations(
    db: Any,
    user_id: int,
    limit: int,
) -> list[tuple["Book", float]] | None:
    """
    Retorna lista (Book, score) se o ranker MLflow estiver implementado e saudável; senão None.

    None → a rota de recomendações usa RecommendationEngine (comportamento atual).
    """
    if not mlflow_online_ranker_enabled():
        return None
    # Reservado: MLFLOW_MODEL_URI / models: URI + mesmas features do train em tempo de inferência.
    log.info(
        "USE_MLFLOW_ONLINE_RANKER set; online MLflow ranker not implemented yet — using heuristic engine (user_id=%s)",
        user_id,
    )
    return None
