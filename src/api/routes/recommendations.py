import time
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.api.models.schemas import BookOut, RecommendationItem
from src.data.database import get_db
from src.data.models import User
from src.monitoring.metrics import (
    MODEL_PREDICTION_COUNT,
    RECOMMENDATION_LATENCY_MS,
)
from src.recommendation.engine import EngineConfig, RecommendationEngine
from src.recommendation.score_calibration import list_confidence_from_raw

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Confiança calibrada (0–1) relativa ao top-K da resposta; só entregamos itens acima deste corte.
MIN_RECOMMENDATION_CONFIDENCE = 0.6


def _book_out_from_pair(book, score: float, confidence: float) -> RecommendationItem:
    cn = book.category.name if book.category else None
    return RecommendationItem(
        book=BookOut(
            book_id=book.book_id,
            title=book.title,
            author=book.author,
            category_id=book.category_id,
            category_name=cn,
            price=book.price,
            cover_url=book.cover_url,
            description=(book.description or "")[:300] or None,
        ),
        score=float(score),
        confidence=float(confidence),
    )


@router.get("", response_model=list[RecommendationItem])
def get_recommendations(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 20,
) -> list[RecommendationItem]:
    t0 = time.perf_counter()
    engine = RecommendationEngine(db, EngineConfig())
    # Busca mais candidatos que o `limit` pedido para ainda preencher após filtrar por confiança.
    fetch_limit = min(50, max(limit * 3, limit))
    pairs = engine.recommend(current_user.user_id, limit=fetch_limit)
    raws = [float(s) for _, s in pairs]
    confs = list_confidence_from_raw(raws)
    ms = (time.perf_counter() - t0) * 1000.0
    RECOMMENDATION_LATENCY_MS.observe(ms)
    MODEL_PREDICTION_COUNT.inc()
    response.headers["X-Recommendation-Latency-Ms"] = f"{ms:.2f}"
    ranked = [
        _book_out_from_pair(b, s, c)
        for (b, s), c in zip(pairs, confs)
        if c >= MIN_RECOMMENDATION_CONFIDENCE
    ]
    return ranked[: min(limit, 50)]
