from decimal import Decimal

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload

from src.data.models import Book, Purchase


def _escape_like_fragment(s: str, max_len: int = 200) -> str:
    t = (s or "").strip()[:max_len]
    return t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_by_id(db: Session, book_id: int) -> Book | None:
    return (
        db.execute(
            select(Book).options(joinedload(Book.category)).where(Book.book_id == book_id)
        )
        .unique()
        .scalar_one_or_none()
    )


def catalog_search(
    db: Session,
    *,
    limit: int,
    offset: int,
    category_id: int | None = None,
    q: str | None = None,
    author: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    sort: str = "book_id",
) -> tuple[list[Book], int]:
    conds: list = []
    if category_id is not None:
        conds.append(Book.category_id == category_id)
    if q:
        frag = _escape_like_fragment(q)
        if frag:
            conds.append(Book.title.ilike(f"%{frag}%", escape="\\"))
    if author:
        frag = _escape_like_fragment(author)
        if frag:
            conds.append(Book.author.isnot(None))
            conds.append(Book.author.ilike(f"%{frag}%", escape="\\"))
    if min_price is not None:
        conds.append(Book.price.isnot(None))
        conds.append(Book.price >= min_price)
    if max_price is not None:
        conds.append(Book.price.isnot(None))
        conds.append(Book.price <= max_price)

    count_stmt = select(func.count()).select_from(Book)
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = int(db.execute(count_stmt).scalar_one() or 0)

    stmt = select(Book).options(joinedload(Book.category))
    for c in conds:
        stmt = stmt.where(c)
    if sort == "title":
        stmt = stmt.order_by(asc(Book.title), asc(Book.book_id))
    elif sort == "price_asc":
        stmt = stmt.order_by(asc(Book.price).nulls_last(), asc(Book.book_id))
    elif sort == "price_desc":
        stmt = stmt.order_by(desc(Book.price).nulls_last(), asc(Book.book_id))
    else:
        stmt = stmt.order_by(asc(Book.book_id))
    stmt = stmt.offset(offset).limit(limit)
    books = list(db.execute(stmt).unique().scalars().all())
    return books, total


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


def sample_books_not_purchased_by_user(db: Session, user_id: int, k: int) -> list[Book]:
    """Random sample of up to k books the user has not bought (avoids loading the full catalog)."""
    if k <= 0:
        return []
    purchased = select(Purchase.book_id).where(Purchase.user_id == user_id).distinct()
    stmt = (
        select(Book)
        .options(joinedload(Book.category))
        .where(~Book.book_id.in_(purchased))
        .order_by(func.random())
        .limit(k)
    )
    return list(db.execute(stmt).unique().scalars().all())
