from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from src.monitoring.offline_metrics import apply_offline_metrics_from_file

RECOMMENDATION_LATENCY_MS = Histogram(
    "recommendation_latency_ms",
    "Latência do endpoint de recomendações (ms)",
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)

MODEL_PREDICTION_COUNT = Counter(
    "model_prediction_count",
    "Total de respostas de recomendação geradas",
)

RECOMMENDATION_CLICK_RATE = Gauge(
    "recommendation_click_rate",
    "Taxa de clique em recomendações (atualizada por job/batch)",
)

MODEL_DRIFT_SCORE = Gauge(
    "model_drift_score",
    "Score de drift (ex.: PSI)",
)

FEATURE_MISSING_RATE = Gauge(
    "feature_missing_rate",
    "Taxa de features ausentes nas requisições",
)

API_ERROR_COUNT = Counter(
    "api_error_count",
    "Erros HTTP na API",
    ["endpoint", "code"],
)

CACHE_HIT_RATE = Gauge(
    "cache_hit_rate",
    "Taxa de cache hit Redis para recomendações",
)


def metrics_response() -> tuple[bytes, str]:
    apply_offline_metrics_from_file()
    return generate_latest(), CONTENT_TYPE_LATEST
