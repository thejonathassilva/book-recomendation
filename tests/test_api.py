from datetime import date

from src.api.security import hash_password
from src.data.models import Book, Category, CategoryWeight, Purchase, User


def seed_minimal(db_session):
    c = Category(name="Ficcao", weight=1.0)
    db_session.add(c)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=c.category_id, weight=1.0))
    u = User(
        name="Test",
        email="t@test.com",
        password_hash=hash_password("secret12"),
        birth_date=date(1990, 5, 5),
        gender="M",
        region="SP",
    )
    db_session.add(u)
    db_session.flush()
    b1 = Book(title="Livro A", author="Autor X", category_id=c.category_id, price=30, description="foo bar")
    b2 = Book(title="Livro B", author="Autor X", category_id=c.category_id, price=35, description="foo similar")
    db_session.add_all([b1, b2])
    db_session.flush()
    db_session.add(Purchase(user_id=u.user_id, book_id=b1.book_id, price_paid=30))
    db_session.commit()
    return u


def test_register_login_recommendations(client, db_session):
    seed_minimal(db_session)
    r = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Novo",
            "email": "n@test.com",
            "password": "senha123",
            "birth_date": "1995-01-01",
            "gender": "F",
            "region": "RJ",
        },
    )
    assert r.status_code == 200
    r2 = client.post("/api/v1/auth/login", json={"email": "t@test.com", "password": "secret12"})
    assert r2.status_code == 200
    token = r2.json()["access_token"]
    books = client.get("/api/v1/catalog/books")
    assert books.status_code == 200
    assert len(books.json()["items"]) >= 1
    rec = client.get("/api/v1/recommendations?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert rec.status_code == 200
    data = rec.json()
    assert isinstance(data, list)

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "t@test.com"

    patch = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"region": "MG", "gender": "M"},
    )
    assert patch.status_code == 200
    assert patch.json()["region"] == "MG"

    book_list = books.json()["items"]
    b2_id = next(b["book_id"] for b in book_list if b["title"] == "Livro B")
    buy = client.post(
        "/api/v1/purchases",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"book_id": b2_id, "quantity": 1},
    )
    assert buy.status_code == 201
    assert buy.json()["book_id"] == b2_id
    mine = client.get("/api/v1/purchases/me", headers={"Authorization": f"Bearer {token}"})
    assert mine.status_code == 200
    assert len(mine.json()) >= 2

    missing = client.post(
        "/api/v1/purchases",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"book_id": 999_999, "quantity": 1},
    )
    assert missing.status_code == 404
