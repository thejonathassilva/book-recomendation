"""pgvector helpers; no-ops when SQLite or table missing."""

from __future__ import annotations

import numpy as np
from sqlalchemy import bindparam, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.data.models import User

MODEL_ID = "paraphrase-multilingual-MiniLM-L12-v2"


def pgvector_enabled(db: Session) -> bool:
    cached = db.info.get("pgvector_enabled")
    if cached is not None:
        return cached
    if db.get_bind().dialect.name != "postgresql":
        db.info["pgvector_enabled"] = False
        return False
    try:
        with db.begin_nested():
            db.execute(text("SELECT 1 FROM book_embeddings LIMIT 1"))
    except (ProgrammingError, SQLAlchemyError):
        db.info["pgvector_enabled"] = False
        return False
    db.info["pgvector_enabled"] = True
    return True


def _parse_vector(raw: object) -> np.ndarray | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        return np.asarray(raw, dtype=np.float64)
    if isinstance(raw, np.ndarray):
        return raw.astype(np.float64)
    s = str(raw).strip()
    if s.startswith("[") and s.endswith("]"):
        import ast

        try:
            return np.asarray(ast.literal_eval(s), dtype=np.float64)
        except (ValueError, SyntaxError):
            pass
    return None


def get_book_embedding(db: Session, book_id: int) -> np.ndarray | None:
    if not pgvector_enabled(db):
        return None
    row = db.execute(
        text("SELECT embedding::text FROM book_embeddings WHERE book_id = :bid"),
        {"bid": book_id},
    ).scalar_one_or_none()
    if row is None:
        return None
    return _parse_vector(row)


def get_embeddings_map(db: Session, book_ids: list[int]) -> dict[int, np.ndarray]:
    if not book_ids or not pgvector_enabled(db):
        return {}
    stmt = text(
        "SELECT book_id, embedding::text FROM book_embeddings WHERE book_id IN :ids"
    ).bindparams(bindparam("ids", expanding=True))
    rows = db.execute(stmt, {"ids": book_ids}).all()
    out: dict[int, np.ndarray] = {}
    for bid, emb in rows:
        v = _parse_vector(emb)
        if v is not None:
            out[int(bid)] = v
    return out


def mean_embedding(vectors: list[np.ndarray]) -> np.ndarray | None:
    if not vectors:
        return None
    stacked = np.stack(vectors, axis=0)
    return np.mean(stacked, axis=0)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na <= 0 or nb <= 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def get_user_profile_embedding(db: Session, user_id: int, purchase_book_ids: list[int]) -> np.ndarray | None:
    if not purchase_book_ids:
        return None
    emap = get_embeddings_map(db, purchase_book_ids)
    if not emap:
        return None
    vecs = [emap[bid] for bid in purchase_book_ids if bid in emap]
    return mean_embedding(vecs)


def cold_start_profile_from_similar(
    db: Session,
    similar_users: list[tuple[User, float]],
    purchases_repo,
    max_users: int = 6,
    max_books_per_user: int = 8,
    max_total_books: int = 48,
) -> np.ndarray | None:
    if not pgvector_enabled(db):
        return None
    seen: set[int] = set()
    book_ids: list[int] = []
    for user, _ in similar_users[:max_users]:
        plist = purchases_repo.get_user_purchases(db, user.user_id)
        for p in plist[:max_books_per_user]:
            bid = int(p.book_id)
            if bid not in seen:
                seen.add(bid)
                book_ids.append(bid)
            if len(book_ids) >= max_total_books:
                break
        if len(book_ids) >= max_total_books:
            break
    if not book_ids:
        return None
    emap = get_embeddings_map(db, book_ids)
    vecs = [emap[bid] for bid in book_ids if bid in emap]
    return mean_embedding(vecs)
