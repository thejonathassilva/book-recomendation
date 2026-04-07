from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.api.models.schemas import PurchaseCreate, PurchaseListItem, PurchaseOut
from src.data.database import get_db
from src.data.models import User
from src.data.repositories import books as books_repo
from src.data.repositories import purchases as purchases_repo
from src.recommendation.engine import invalidate_recommendation_cache_for_user

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("/me", response_model=list[PurchaseListItem])
def list_my_purchases(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 100,
) -> list[PurchaseListItem]:
    rows = purchases_repo.get_user_purchases(db, current_user.user_id)
    sliced = rows[: min(limit, 200)]
    out: list[PurchaseListItem] = []
    for p in sliced:
        b = p.book
        out.append(
            PurchaseListItem(
                purchase_id=p.purchase_id,
                user_id=p.user_id,
                book_id=p.book_id,
                purchase_date=p.purchase_date,
                price_paid=p.price_paid,
                quantity=p.quantity,
                book_title=b.title if b else None,
                book_author=b.author if b else None,
            )
        )
    return out


@router.post("", response_model=PurchaseOut, status_code=201)
def create_purchase(
    body: PurchaseCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    book = books_repo.get_by_id(db, body.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado.")

    qty = body.quantity
    price_paid = None
    if book.price is not None:
        price_paid = book.price * qty

    purchase = purchases_repo.create(
        db,
        current_user.user_id,
        book.book_id,
        quantity=qty,
        price_paid=price_paid,
    )
    invalidate_recommendation_cache_for_user(current_user.user_id)
    return purchase
