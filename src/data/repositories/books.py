from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.data.models import Book


def get_by_id(db: Session, book_id: int) -> Book | None:
    return (
        db.execute(
            select(Book).options(joinedload(Book.category)).where(Book.book_id == book_id)
        )
        .unique()
        .scalar_one_or_none()
    )


def list_all(db: Session, limit: int | None = None, offset: int = 0) -> list[Book]:
    stmt = select(Book).options(joinedload(Book.category)).order_by(Book.book_id).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).unique().scalars().all())


def list_ids_excluding(db: Session, exclude_ids: set[int]) -> list[Book]:
    stmt = select(Book).options(joinedload(Book.category)).order_by(Book.book_id)
    if exclude_ids:
        stmt = stmt.where(Book.book_id.not_in(exclude_ids))
    return list(db.execute(stmt).unique().scalars().all())
