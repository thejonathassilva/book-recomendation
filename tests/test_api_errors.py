"""Formato padronizado de erros JSON e regressão de recomendações."""


def test_unauthorized_returns_error_envelope(client):
    r = client.get("/api/v1/recommendations")
    assert r.status_code == 401
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "message" in data["error"]


def test_validation_error_returns_envelope(client):
    r = client.post("/api/v1/auth/register", json={"email": "not-an-email"})
    assert r.status_code == 422
    data = r.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]


def test_new_user_recommendations_ok(client, db_session):
    from src.data.models import Book, Category, CategoryWeight

    cat = Category(name="ErrCat", weight=1.0)
    db_session.add(cat)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=cat.category_id, weight=1.0))
    db_session.add(
        Book(title="Livro X", author="A", category_id=cat.category_id, price=10, description="d")
    )
    db_session.commit()

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Novo User",
            "email": "novo_err_test@example.com",
            "password": "senha123",
            "birth_date": "1998-05-05",
            "gender": "F",
            "region": "SP",
        },
    )
    assert reg.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "novo_err_test@example.com", "password": "senha123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    rec = client.get("/api/v1/recommendations?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert rec.status_code == 200
    assert isinstance(rec.json(), list)
