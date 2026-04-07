from __future__ import annotations

import os

from src.recommendation.vector_store import MODEL_ID as DEFAULT_MODEL_ID

_model = None


def get_encoder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        mid = os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL_ID)
        _model = SentenceTransformer(mid)
    return _model


def book_to_text(title: str, author: str | None, description: str | None) -> str:
    parts = [title or "", author or "", (description or "")[:4000]]
    return ". ".join(p for p in parts if p).strip() or title or "book"
