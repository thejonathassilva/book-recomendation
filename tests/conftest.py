import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CONFIG_DIR", os.path.join(os.path.dirname(__file__), "..", "config"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.api.main import app
from src.data import models  # noqa: F401
from src.data.database import Base, get_db


@pytest.fixture
def engine_mem():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine_mem):
    Session = sessionmaker(bind=engine_mem)
    s = Session()
    yield s
    s.close()


def override_get_db(engine_mem):
    Session = sessionmaker(bind=engine_mem)

    def _gen():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    return _gen


@pytest.fixture
def client(engine_mem, db_session):
    app.dependency_overrides[get_db] = override_get_db(engine_mem)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
