"""Rotas exclusivas de utilizadores com flag is_admin (consola de gestão)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_admin
from src.api.models.schemas import (
    AdminPurchasePage,
    AdminPurchaseRow,
    BookCreateAdmin,
    BookOut,
    BookUpdateAdmin,
)
from src.data.database import get_db
from src.data.models import Book, User
from src.data.repositories import books as books_repo
from src.data.repositories import purchases as purchases_repo

router = APIRouter(prefix="/admin", tags=["admin-console"])


def _book_out(b: Book) -> BookOut:
    cn = b.category.name if b.category else None
    return BookOut(
        book_id=b.book_id,
        title=b.title,
        author=b.author,
        category_id=b.category_id,
        category_name=cn,
        price=b.price,
        cover_url=b.cover_url,
        description=(b.description or "")[:2000] or None,
    )


@router.get("/purchases", response_model=AdminPurchasePage)
def list_all_purchases(
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AdminPurchasePage:
    rows, total = purchases_repo.list_all_admin(db, limit=limit, offset=offset)
    items: list[AdminPurchaseRow] = []
    for p in rows:
        u = p.user
        b = p.book
        items.append(
            AdminPurchaseRow(
                purchase_id=p.purchase_id,
                user_id=p.user_id,
                user_email=u.email if u else "",
                book_id=p.book_id,
                book_title=b.title if b else None,
                purchase_date=p.purchase_date,
                price_paid=p.price_paid,
                quantity=p.quantity,
            )
        )
    return AdminPurchasePage(items=items, total=total, limit=limit, offset=offset)


@router.post("/books", response_model=BookOut)
def create_book(
    body: BookCreateAdmin,
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Session = Depends(get_db),
) -> BookOut:
    if body.category_id is not None and not books_repo.category_exists(db, body.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    b = books_repo.create(
        db,
        title=body.title.strip(),
        author=body.author.strip() if body.author else None,
        isbn=body.isbn.strip() if body.isbn else None,
        category_id=body.category_id,
        price=body.price,
        description=body.description,
        cover_url=body.cover_url.strip() if body.cover_url else None,
    )
    b = books_repo.get_by_id(db, b.book_id)
    assert b is not None
    return _book_out(b)


@router.patch("/books/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    body: BookUpdateAdmin,
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Session = Depends(get_db),
) -> BookOut:
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        data["title"] = str(data["title"]).strip()
    if "author" in data and data["author"] is not None:
        data["author"] = str(data["author"]).strip()
    if "isbn" in data and data["isbn"] is not None:
        data["isbn"] = str(data["isbn"]).strip()
    if "cover_url" in data and data["cover_url"] is not None:
        data["cover_url"] = str(data["cover_url"]).strip()
    if "category_id" in data:
        cid = data["category_id"]
        if cid is not None and not books_repo.category_exists(db, cid):
            raise HTTPException(status_code=404, detail="Category not found")
    b = books_repo.update_fields(db, book_id, data)
    if not b:
        raise HTTPException(status_code=404, detail="Book not found")
    b = books_repo.get_by_id(db, book_id)
    assert b is not None
    return _book_out(b)
