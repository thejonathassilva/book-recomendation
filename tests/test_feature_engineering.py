"""Testes de feature engineering (sem depender de Postgres)."""

from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
from src.api.security import hash_password
from src.data.models import Book, Category, Purchase, User
from src.training.feature_engineering import (
    age_group,
    build_interaction_sample,
    build_user_features,
    load_raw_frames,
)


def test_age_group_datetime_and_timestamp():
    assert age_group(datetime(2000, 3, 1)) in ("26-35", "18-25", "36-45")
    assert age_group(pd.Timestamp("2012-06-01")) == "under_18"
    assert age_group(date(1960, 1, 1)) == "60+"


def test_build_user_features_empty():
    users = pd.DataFrame({"user_id": [1], "region": ["SP"], "gender": ["M"], "birth_date": [date(1990, 1, 1)]})
    assert build_user_features(users, pd.DataFrame(), pd.DataFrame()).empty


def test_build_user_features_non_empty(db_session, monkeypatch):
    cat = Category(name="CatA", weight=1.0)
    db_session.add(cat)
    db_session.flush()
    u = User(
        name="U",
        email="u@fe.test",
        password_hash=hash_password("x"),
        birth_date=date(1992, 1, 1),
        gender="F",
        region="RJ",
    )
    db_session.add(u)
    db_session.flush()
    b1 = Book(title="B1", author="A", category_id=cat.category_id, price=Decimal("20"), description="d")
    b2 = Book(title="B2", author="A", category_id=cat.category_id, price=Decimal("25"), description="d")
    db_session.add_all([b1, b2])
    db_session.flush()
    pd1 = datetime(2024, 1, 1, tzinfo=None)
    pd2 = datetime(2024, 6, 1, tzinfo=None)
    db_session.add(
        Purchase(user_id=u.user_id, book_id=b1.book_id, purchase_date=pd1, price_paid=Decimal("20"))
    )
    db_session.add(
        Purchase(user_id=u.user_id, book_id=b2.book_id, purchase_date=pd2, price_paid=Decimal("25"))
    )
    db_session.commit()

    # pd.Timestamp.utcnow() pode ser tz-aware; last_purchase vindo do SQLite é naive.
    monkeypatch.setattr(
        "src.training.feature_engineering.pd.Timestamp.utcnow",
        lambda: pd.Timestamp("2025-01-15 12:00:00"),
    )

    users = pd.read_sql_query("SELECT * FROM users", db_session.bind, parse_dates=["birth_date"])
    books = pd.read_sql_query("SELECT * FROM books", db_session.bind)
    purchases = pd.read_sql_query("SELECT * FROM purchases", db_session.bind, parse_dates=["purchase_date"])
    out = build_user_features(users, purchases, books)
    assert not out.empty
    assert "age_group" in out.columns
    assert "purchase_frequency" in out.columns


def test_load_raw_frames(engine_mem, db_session):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine_mem)
    s = Session()
    try:
        cat = Category(name="LFE", weight=1.0)
        s.add(cat)
        s.flush()
        u = User(
            name="Lu",
            email="lu@load.test",
            password_hash=hash_password("p"),
            birth_date=date(1991, 1, 1),
            gender="M",
            region="SP",
        )
        s.add(u)
        s.flush()
        b = Book(title="T", author="A", category_id=cat.category_id, price=Decimal("10"), description="x")
        s.add(b)
        s.flush()
        s.add(
            Purchase(
                user_id=u.user_id,
                book_id=b.book_id,
                purchase_date=datetime(2024, 1, 1),
                price_paid=Decimal("10"),
            )
        )
        s.commit()
    finally:
        s.close()

    udf, bdf, pdf, cdf = load_raw_frames(engine_mem)
    assert len(udf) >= 1 and len(bdf) >= 1 and len(pdf) >= 1 and len(cdf) >= 1


def test_build_interaction_sample_basic(db_session):
    cat = Category(name="IX", weight=1.0)
    db_session.add(cat)
    db_session.flush()
    u = User(
        name="Ix",
        email="ix@test.com",
        password_hash=hash_password("x"),
        birth_date=date(1990, 1, 1),
        gender="M",
        region="SP",
    )
    db_session.add(u)
    db_session.flush()
    books = []
    for i in range(3):
        books.append(
            Book(
                title=f"Bi{i}",
                author="Auth",
                category_id=cat.category_id,
                price=Decimal("15"),
                description="d",
            )
        )
    db_session.add_all(books)
    db_session.flush()
    db_session.add(
        Purchase(
            user_id=u.user_id,
            book_id=books[0].book_id,
            purchase_date=datetime(2024, 1, 1),
            price_paid=Decimal("15"),
        )
    )
    db_session.commit()
    purchases = pd.read_sql_query("SELECT * FROM purchases", db_session.bind)
    bdf = pd.read_sql_query("SELECT * FROM books", db_session.bind)
    out = build_interaction_sample(purchases, bdf, max_users=None)
    assert not out.empty
    assert "label" in out.columns


def test_build_interaction_sample_no_price_paid_column():
    books = pd.DataFrame(
        {
            "book_id": [1, 2],
            "category_id": [1, 1],
            "author": ["a", "b"],
            "price": [10.0, 12.0],
        }
    )
    purchases = pd.DataFrame(
        {
            "user_id": [1, 1],
            "book_id": [1, 2],
            "purchase_date": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
        }
    )
    out = build_interaction_sample(purchases, books, max_users=5)
    assert not out.empty


def test_build_interaction_sample_max_users():
    rng = np.random.default_rng(0)
    n_users = 20
    rows = []
    for uid in range(1, n_users + 1):
        for _ in range(2):
            rows.append(
                {
                    "user_id": uid,
                    "book_id": int(rng.integers(1, 50)),
                    "purchase_date": datetime(2024, 1, 1),
                    "price_paid": 10.0,
                }
            )
    purchases = pd.DataFrame(rows)
    books = pd.DataFrame(
        {
            "book_id": np.arange(1, 51),
            "category_id": [1] * 50,
            "author": ["a"] * 50,
            "price": [10.0] * 50,
        }
    )
    out = build_interaction_sample(purchases, books, max_users=5)
    assert not out.empty


def test_build_interaction_sample_empty():
    assert build_interaction_sample(pd.DataFrame(), pd.DataFrame()).empty
