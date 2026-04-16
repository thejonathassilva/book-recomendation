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
    data = rec.json()
    assert isinstance(data, list)
    assert rec.headers.get("X-MLflow-Online-Ranker") is None
    if data:
        assert "confidence" in data[0]
        assert 0.6 <= data[0]["confidence"] <= 1
        assert all(0.6 <= item["confidence"] <= 1 for item in data)


def test_recommendations_mlflow_stub_header(client, db_session, monkeypatch):
    monkeypatch.setenv("USE_MLFLOW_ONLINE_RANKER", "1")
    from src.data.models import Book, Category, CategoryWeight

    cat = Category(name="StubCat", weight=1.0)
    db_session.add(cat)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=cat.category_id, weight=1.0))
    db_session.add(
        Book(title="Livro Stub", author="A", category_id=cat.category_id, price=10, description="d")
    )
    db_session.commit()

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Stub User",
            "email": "stub_mlflow_flag@example.com",
            "password": "senha123",
            "birth_date": "1998-05-05",
            "gender": "F",
            "region": "SP",
        },
    )
    assert reg.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "stub_mlflow_flag@example.com", "password": "senha123"},
    )
    token = login.json()["access_token"]
    rec = client.get("/api/v1/recommendations?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert rec.status_code == 200
    assert rec.headers.get("X-MLflow-Online-Ranker") == "stub-fallback-heuristic"
    data = rec.json()
    assert isinstance(data, list)
    if data:
        assert "confidence" in data[0]
        assert 0.6 <= data[0]["confidence"] <= 1
