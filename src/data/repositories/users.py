from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.data.models import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def list_active_with_purchases(db: Session) -> list[User]:
    stmt = select(User).options(joinedload(User.purchases)).where(User.user_id > 0)
    return list(db.execute(stmt).unique().scalars().all())
