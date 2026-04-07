from datetime import date, datetime, timezone

from src.api.security import hash_password
from src.data.models import Book, Category, CategoryWeight, Purchase, User
from src.recommendation.engine import EngineConfig, RecommendationEngine


def test_hybrid_scores(db_session):
    c = Category(name="Ficcao", weight=1.0)
    db_session.add(c)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=c.category_id, weight=1.2))
    u1 = User(
        name="U1",
        email="u1@test.com",
        password_hash=hash_password("x"),
        birth_date=date(1992, 1, 1),
        gender="M",
        region="SP",
    )
    u2 = User(
        name="U2",
        email="u2@test.com",
        password_hash=hash_password("x"),
        birth_date=date(1993, 2, 2),
        gender="M",
        region="SP",
    )
    db_session.add_all([u1, u2])
    db_session.flush()
    books = []
    for i in range(5):
        books.append(
            Book(
                title=f"T{i}",
                author="A1",
                category_id=c.category_id,
                price=20 + i,
                description="fiction text " * 5,
            )
        )
    db_session.add_all(books)
    db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add(Purchase(user_id=u1.user_id, book_id=books[0].book_id, purchase_date=now))
    db_session.add(Purchase(user_id=u2.user_id, book_id=books[1].book_id, purchase_date=now))
    db_session.commit()

    eng = RecommendationEngine(db_session, EngineConfig(max_candidates=20, similar_users_top_k=5))
    s = eng.final_score(u1.user_id, books[2])
    assert s >= 0.0

    # Usuário sem compras: scores de "usuários similares" devem variar (não ser todos 0.4 por bug).
    u3 = User(
        name="Cold",
        email="cold@test.com",
        password_hash=hash_password("x"),
        birth_date=date(1995, 1, 1),
        gender="M",
        region="SP",
    )
    db_session.add(u3)
    db_session.commit()
    eng2 = RecommendationEngine(db_session, EngineConfig(max_candidates=20, similar_users_top_k=5))
    s_b0 = eng2.final_score(u3.user_id, books[0])
    s_b2 = eng2.final_score(u3.user_id, books[2])
    # books[0] foi comprado por u1 (similar demográfico); books[2] por ninguém no seed mínimo
    assert s_b0 > s_b2
