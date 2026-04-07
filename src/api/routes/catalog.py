from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.models.schemas import BookOut, CategoryWeightUpdate
from src.api.settings import get_settings
from src.data.database import get_db
from src.data.models import Book, Category, CategoryWeight

router = APIRouter(prefix="/catalog", tags=["catalog"])


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
        description=(b.description or "")[:500] or None,
    )


@router.get("/books", response_model=list[BookOut])
def list_books(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)) -> list[BookOut]:
    from sqlalchemy.orm import joinedload

    stmt = (
        select(Book)
        .options(joinedload(Book.category))
        .order_by(Book.book_id)
        .offset(offset)
        .limit(min(limit, 200))
    )
    books = list(db.execute(stmt).unique().scalars().all())
    return [_book_out(b) for b in books]


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookOut:
    from sqlalchemy.orm import joinedload

    stmt = select(Book).options(joinedload(Book.category)).where(Book.book_id == book_id)
    b = db.execute(stmt).unique().scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Book not found")
    return _book_out(b)


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Category).order_by(Category.name)).scalars().all()
    cw = {r.category_id: r.weight for r in db.execute(select(CategoryWeight)).scalars().all()}
    out = []
    for c in rows:
        w = cw.get(c.category_id, c.weight)
        out.append({"category_id": c.category_id, "name": c.name, "weight": float(w)})
    return out


@router.patch("/categories/{category_id}/weight")
def update_category_weight(
    category_id: int,
    body: CategoryWeightUpdate,
    db: Session = Depends(get_db),
    x_admin_token: Annotated[str | None, Header()] = None,
) -> dict:
    s = get_settings()
    if not s.admin_token or x_admin_token != s.admin_token:
        raise HTTPException(status_code=403, detail="Admin token required")
    c = db.get(Category, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    row = db.get(CategoryWeight, category_id)
    if row is None:
        row = CategoryWeight(category_id=category_id, weight=body.weight)
        db.add(row)
    else:
        row.weight = body.weight
    db.commit()
    return {"category_id": category_id, "weight": body.weight}
