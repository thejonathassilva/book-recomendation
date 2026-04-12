from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from src.data.models import Book, Purchase, User


def list_all_admin(db: Session, *, limit: int, offset: int) -> tuple[list[Purchase], int]:
    total = int(db.execute(select(func.count()).select_from(Purchase)).scalar_one() or 0)
    stmt = (
        select(Purchase)
        .options(joinedload(Purchase.user), joinedload(Purchase.book))
        .order_by(Purchase.purchase_date.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list(db.execute(stmt).unique().scalars().all())
    return rows, total


def get_user_purchases(db: Session, user_id: int) -> list[Purchase]:
    stmt = (
        select(Purchase)
        .options(joinedload(Purchase.book).joinedload(Book.category))
        .where(Purchase.user_id == user_id)
        .order_by(Purchase.purchase_date.desc())
    )
    return list(db.execute(stmt).unique().scalars().all())


def user_purchased_book_ids(db: Session, user_id: int) -> set[int]:
    rows = db.execute(select(Purchase.book_id).where(Purchase.user_id == user_id)).all()
    return {r[0] for r in rows}


def purchases_for_book_by_user(db: Session, user_id: int, book_id: int) -> list[Purchase]:
    stmt = (
        select(Purchase)
        .options(joinedload(Purchase.book).joinedload(Book.category))
        .where(Purchase.user_id == user_id, Purchase.book_id == book_id)
    )
    return list(db.execute(stmt).unique().scalars().all())


def purchases_for_book_by_users(db: Session, user_ids: list[int], book_id: int) -> list[Purchase]:
    if not user_ids:
        return []
    stmt = (
        select(Purchase)
        .options(joinedload(Purchase.book).joinedload(Book.category))
        .where(Purchase.book_id == book_id, Purchase.user_id.in_(user_ids))
    )
    return list(db.execute(stmt).unique().scalars().all())


def user_category_counts(db: Session) -> dict[int, dict[int, float]]:
    stmt = (
        select(Purchase.user_id, Book.category_id, func.count().label("c"))
        .join(Book, Purchase.book_id == Book.book_id)
        .group_by(Purchase.user_id, Book.category_id)
    )
    out: dict[int, dict[int, float]] = defaultdict(dict)
    for uid, cid, c in db.execute(stmt):
        if cid is not None:
            out[uid][cid] = float(c)
    return dict(out)


def all_users_minimal(db: Session) -> list[User]:
    return list(db.execute(select(User)).scalars().all())


def create(
    db: Session,
    user_id: int,
    book_id: int,
    *,
    quantity: int = 1,
    price_paid: Decimal | None = None,
) -> Purchase:
    p = Purchase(
        user_id=user_id,
        book_id=book_id,
        purchase_date=datetime.now(timezone.utc),
        price_paid=price_paid,
        quantity=max(1, quantity),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def book_popularity_recent(db: Session, since: datetime) -> dict[int, int]:
    stmt = (
        select(Purchase.book_id, func.count().label("c"))
        .where(Purchase.purchase_date >= since)
        .group_by(Purchase.book_id)
    )
    return {bid: int(c) for bid, c in db.execute(stmt)}
