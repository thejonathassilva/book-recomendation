"""Testes de rotas de catálogo, health e admin."""

from src.api.settings import get_settings


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_catalog_book_by_id_and_404(client, db_session):
    from tests.test_api import seed_minimal

    seed_minimal(db_session)
    data = client.get("/api/v1/catalog/books").json()
    lst = data["items"]
    assert data["total"] >= 1
    bid = lst[0]["book_id"]
    r = client.get(f"/api/v1/catalog/books/{bid}")
    assert r.status_code == 200
    assert r.json()["book_id"] == bid
    r404 = client.get("/api/v1/catalog/books/999999")
    assert r404.status_code == 404


def test_catalog_categories(client, db_session):
    from tests.test_api import seed_minimal

    seed_minimal(db_session)
    r = client.get("/api/v1/catalog/categories")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1


def test_admin_category_weight_forbidden_and_ok(client, db_session, monkeypatch):
    from tests.test_api import seed_minimal

    monkeypatch.setenv("ADMIN_TOKEN", "admintok-test")
    get_settings.cache_clear()
    seed_minimal(db_session)
    cid = client.get("/api/v1/catalog/categories").json()[0]["category_id"]
    r = client.patch(
        f"/api/v1/catalog/categories/{cid}/weight",
        headers={"X-Admin-Token": "wrong"},
        json={"weight": 1.33},
    )
    assert r.status_code == 403
    r2 = client.patch(
        f"/api/v1/catalog/categories/{cid}/weight",
        headers={"X-Admin-Token": "admintok-test"},
        json={"weight": 1.33},
    )
    assert r2.status_code == 200
    assert r2.json()["weight"] == 1.33
    get_settings.cache_clear()


def test_catalog_books_filters_and_page_shape(client, db_session):
    from tests.test_api import seed_minimal

    seed_minimal(db_session)
    r = client.get("/api/v1/catalog/books?limit=1&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {"items", "total", "limit", "offset"}
    assert body["limit"] == 1
    assert len(body["items"]) <= 1
    cats = client.get("/api/v1/catalog/categories").json()
    cid = cats[0]["category_id"]
    r2 = client.get(f"/api/v1/catalog/books?category_id={cid}&limit=50")
    assert r2.status_code == 200
    for b in r2.json()["items"]:
        assert b["category_id"] == cid


def test_admin_category_not_found(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "tok2")
    get_settings.cache_clear()
    r = client.patch(
        "/api/v1/catalog/categories/999999/weight",
        headers={"X-Admin-Token": "tok2"},
        json={"weight": 1.0},
    )
    assert r.status_code == 404
    get_settings.cache_clear()
