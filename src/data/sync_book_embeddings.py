"""Sync rows in book_embeddings. CLI: python -m src.data.sync_book_embeddings [--batch-size N] [--limit N]."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import select, text

from src.data.database import SessionLocal
from src.data.models import Book
from src.recommendation.embedding_service import book_to_text, get_encoder
from src.recommendation.vector_store import MODEL_ID, pgvector_enabled


def sync_all(batch_size: int = 32, limit: int | None = None) -> int:
    session = SessionLocal()
    try:
        if not pgvector_enabled(session):
            print(
                "book_embeddings indisponível (use PostgreSQL + pgvector + init.sql). Nada a fazer.",
                file=sys.stderr,
            )
            return 1
        stmt = select(Book).order_by(Book.book_id)
        if limit is not None:
            stmt = stmt.limit(limit)
        books = list(session.scalars(stmt).all())
        if not books:
            print("Nenhum livro no catálogo.", file=sys.stderr)
            return 1
        enc = get_encoder()
        model_label = os.environ.get("EMBEDDING_MODEL", MODEL_ID)
        n = 0
        for i in range(0, len(books), batch_size):
            batch = books[i : i + batch_size]
            texts = [book_to_text(b.title, b.author, b.description) for b in batch]
            vectors = enc.encode(
                texts,
                normalize_embeddings=True,
                batch_size=min(batch_size, 32),
                show_progress_bar=False,
            )
            for b, vec in zip(batch, vectors, strict=True):
                lst = vec.tolist()
                s = "[" + ",".join(f"{x:.8f}" for x in lst) + "]"
                session.execute(
                    text(
                        """
                        INSERT INTO book_embeddings (book_id, embedding, model_id)
                        VALUES (:bid, CAST(:emb AS vector), :mid)
                        ON CONFLICT (book_id) DO UPDATE SET
                          embedding = EXCLUDED.embedding,
                          model_id = EXCLUDED.model_id,
                          updated_at = NOW()
                        """
                    ),
                    {"bid": b.book_id, "emb": s, "mid": model_label[:80]},
                )
                n += 1
            session.commit()
            print(f"Embeddings: {n}/{len(books)}")
        print(f"Concluído: {n} livros indexados ({model_label}).")
        return 0
    finally:
        session.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    raise SystemExit(sync_all(batch_size=args.batch_size, limit=args.limit))


if __name__ == "__main__":
    main()
