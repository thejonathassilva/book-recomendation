"""Testes do motor de recomendação (cache Redis, config)."""

import json
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from sqlalchemy import select
from src.api.security import hash_password
from src.data.models import Book, Category, CategoryWeight, Purchase, User
from src.recommendation.engine import (
    EngineConfig,
    RecommendationEngine,
    invalidate_recommendation_cache_for_user,
)


def test_engine_config_reads_env(monkeypatch):
    monkeypatch.setenv("REC_W_OWN", "0.2")
    monkeypatch.setenv("REC_W_SIM", "0.3")
    monkeypatch.setenv("REC_W_VEC", "0.5")
    cfg = EngineConfig()
    assert cfg.user_history_weight == 0.2
    assert cfg.similar_users_weight == 0.3
    assert cfg.vector_weight == 0.5
    monkeypatch.delenv("REC_W_OWN", raising=False)
    monkeypatch.delenv("REC_W_SIM", raising=False)
    monkeypatch.delenv("REC_W_VEC", raising=False)


def test_invalidate_recommendation_cache(monkeypatch):
    r = MagicMock()
    r.scan_iter.return_value = iter(["rec:7:k1", "rec:7:k2"])
    monkeypatch.setattr("src.recommendation.engine._redis_client", lambda: r)
    invalidate_recommendation_cache_for_user(7)
    assert r.delete.call_count == 2


def test_invalidate_when_no_redis(monkeypatch):
    monkeypatch.setattr("src.recommendation.engine._redis_client", lambda: None)
    invalidate_recommendation_cache_for_user(1)


def test_recommend_hits_redis_cache(db_session, monkeypatch):
    cat = Category(name="ECat", weight=1.0)
    db_session.add(cat)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=cat.category_id, weight=1.0))
    u = User(
        name="RedisU",
        email="redis_u@test.com",
        password_hash=hash_password("x"),
        birth_date=date(1991, 1, 1),
        gender="M",
        region="SP",
    )
    db_session.add(u)
    db_session.flush()
    b = Book(title="RB", author="A", category_id=cat.category_id, price=20, description="d")
    db_session.add(b)
    db_session.flush()
    db_session.commit()
    bid = b.book_id
    uid = u.user_id

    r = MagicMock()
    r.get.return_value = json.dumps({"items": [[bid, 0.95]]})
    monkeypatch.setattr("src.recommendation.engine._redis_client", lambda: r)
    eng = RecommendationEngine(db_session)
    eng._redis = r
    out = eng.recommend(uid, limit=5, use_cache=True, cache_ttl=60)
    assert len(out) >= 1
    assert out[0][0].book_id == bid
    r.setex.assert_not_called()


def test_recommend_subsample_candidates(db_session, monkeypatch):
    cat = Category(name="Many", weight=1.0)
    db_session.add(cat)
    db_session.flush()
    u = User(
        name="Mu",
        email="mu@test.com",
        password_hash=hash_password("x"),
        birth_date=date(1990, 1, 1),
        gender="F",
        region="RJ",
    )
    db_session.add(u)
    db_session.flush()
    for i in range(30):
        db_session.add(
            Book(title=f"T{i}", author="A", category_id=cat.category_id, price=10 + i, description="x")
        )
    db_session.flush()
    first_book = db_session.execute(select(Book).limit(1)).scalar_one()
    db_session.add(
        Purchase(
            user_id=u.user_id,
            book_id=first_book.book_id,
            purchase_date=datetime.now(timezone.utc),
            price_paid=10,
        )
    )
    db_session.commit()
    monkeypatch.setattr("src.recommendation.engine._redis_client", lambda: None)
    eng = RecommendationEngine(db_session, EngineConfig(max_candidates=10, similar_users_top_k=3))
    out = eng.recommend(u.user_id, limit=3, use_cache=False)
    assert isinstance(out, list)
