"""Rotas /api/v1/admin/* (utilizador is_admin)."""

from datetime import date
from decimal import Decimal

from src.api.security import hash_password
from src.data.models import Book, Category, CategoryWeight, Purchase, User


def _seed_admin_catalog(db_session):
    c = Category(name="TestCat", weight=1.0)
    db_session.add(c)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=c.category_id, weight=1.0))
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash=hash_password("pw12345"),
        birth_date=date(1980, 1, 1),
        gender="M",
        region="SP",
        is_admin=True,
    )
    user = User(
        name="User",
        email="u@test.com",
        password_hash=hash_password("pw12345"),
        birth_date=date(1990, 1, 1),
        gender="F",
        region="RJ",
        is_admin=False,
    )
    db_session.add_all([admin, user])
    db_session.flush()
    b = Book(title="Seed Book", author="A", category_id=c.category_id, price=Decimal("20.00"))
    db_session.add(b)
    db_session.flush()
    db_session.add(Purchase(user_id=user.user_id, book_id=b.book_id, price_paid=Decimal("20.00")))
    db_session.commit()
    return admin, user, c.category_id, b.book_id


def test_admin_purchases_forbidden_for_normal_user(client, db_session):
    _seed_admin_catalog(db_session)
    r = client.post("/api/v1/auth/login", json={"email": "u@test.com", "password": "pw12345"})
    token = r.json()["access_token"]
    assert r.json().get("is_admin") is False
    p = client.get("/api/v1/admin/purchases", headers={"Authorization": f"Bearer {token}"})
    assert p.status_code == 403


def test_admin_purchases_and_books(client, db_session):
    admin, _u, cat_id, _bid = _seed_admin_catalog(db_session)
    r = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "pw12345"})
    assert r.status_code == 200
    assert r.json().get("is_admin") is True
    token = r.json()["access_token"]

    p = client.get("/api/v1/admin/purchases", headers={"Authorization": f"Bearer {token}"})
    assert p.status_code == 200
    body = p.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
    assert "user_email" in body["items"][0]

    nb = client.post(
        "/api/v1/admin/books",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "title": "Novo título",
            "author": "Autor Novo",
            "category_id": cat_id,
            "price": "42.50",
        },
    )
    assert nb.status_code == 200
    new_id = nb.json()["book_id"]
    assert nb.json()["title"] == "Novo título"

    up = client.patch(
        f"/api/v1/admin/books/{new_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"title": "Atualizado"},
    )
    assert up.status_code == 200
    assert up.json()["title"] == "Atualizado"
