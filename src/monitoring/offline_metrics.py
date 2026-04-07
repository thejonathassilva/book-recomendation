"""Expose last training metrics to Prometheus (reads TRAIN_METRICS_EXPORT_PATH JSON)."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from prometheus_client import Gauge

OFFLINE_EVALUATION = Gauge(
    "bookstore_offline_evaluation",
    "Métricas de avaliação offline do último treino (por algoritmo)",
    ["algorithm", "metric", "k"],
)

OFFLINE_METRICS_LAST_REFRESH = Gauge(
    "bookstore_offline_metrics_last_refresh_unixtime",
    "Epoch (segundos) da última leitura bem-sucedida de train_metrics_last.json",
)


def _default_export_path() -> Path:
    raw = os.environ.get("TRAIN_METRICS_EXPORT_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path("data/train_metrics_last.json")


def _parse_mlflow_style_key(key: str) -> tuple[str, str]:
    if key == "map":
        return "map", ""
    for prefix, name in (
        ("precision_at_", "precision"),
        ("recall_at_", "recall"),
        ("ndcg_at_", "ndcg"),
    ):
        if key.startswith(prefix):
            return name, key[len(prefix) :]
    return key, ""


_cached_mtime: float | None = None
_cached_payload: dict | None = None


def apply_offline_metrics_from_file() -> None:
    global _cached_mtime, _cached_payload
    path = _default_export_path()
    if not path.is_file():
        return
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return
    if _cached_payload is None or mtime != _cached_mtime:
        try:
            _cached_payload = json.loads(path.read_text(encoding="utf-8"))
            _cached_mtime = mtime
        except (OSError, json.JSONDecodeError):
            return

    data = _cached_payload
    if not isinstance(data, dict):
        return

    algos = data.get("algorithms")
    if not isinstance(algos, dict):
        return

    for algo, metrics in algos.items():
        if not isinstance(metrics, dict):
            continue
        for key, val in metrics.items():
            if isinstance(val, float) and math.isnan(val):
                continue
            if not isinstance(val, (int, float)):
                continue
            metric, k = _parse_mlflow_style_key(str(key))
            OFFLINE_EVALUATION.labels(algorithm=str(algo), metric=metric, k=k).set(float(val))

    ts = data.get("generated_at_unix")
    if isinstance(ts, (int, float)):
        OFFLINE_METRICS_LAST_REFRESH.set(float(ts))
    else:
        OFFLINE_METRICS_LAST_REFRESH.set(mtime)
