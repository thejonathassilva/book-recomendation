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

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _book_out_from_pair(book, score: float) -> RecommendationItem:
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
    pairs = engine.recommend(current_user.user_id, limit=min(limit, 50))
    ms = (time.perf_counter() - t0) * 1000.0
    RECOMMENDATION_LATENCY_MS.observe(ms)
    MODEL_PREDICTION_COUNT.inc()
    response.headers["X-Recommendation-Latency-Ms"] = f"{ms:.2f}"
    return [_book_out_from_pair(b, s) for b, s in pairs]
