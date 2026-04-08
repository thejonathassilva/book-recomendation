from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.models.schemas import BookListPage, BookOut, CategoryWeightUpdate
from src.api.settings import get_settings
from src.data.database import get_db
from src.data.models import Book, Category, CategoryWeight
from src.data.repositories import books as books_repo

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


@router.get("/books", response_model=BookListPage)
def list_books(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category_id: int | None = Query(None, description="Filtrar por categoria"),
    q: str | None = Query(None, description="Texto no título (contém, sem diferenciar maiúsculas)"),
    author: str | None = Query(None, description="Texto no autor (contém)"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort: str = Query("book_id", description="book_id | title | price_asc | price_desc"),
    db: Session = Depends(get_db),
) -> BookListPage:
    allowed_sort = {"book_id", "title", "price_asc", "price_desc"}
    if sort not in allowed_sort:
        sort = "book_id"
    min_d = Decimal(str(min_price)) if min_price is not None else None
    max_d = Decimal(str(max_price)) if max_price is not None else None
    if min_d is not None and max_d is not None and min_d > max_d:
        min_d, max_d = max_d, min_d
    rows, total = books_repo.catalog_search(
        db,
        limit=limit,
        offset=offset,
        category_id=category_id,
        q=q,
        author=author,
        min_price=min_d,
        max_price=max_d,
        sort=sort,
    )
    return BookListPage(
        items=[_book_out(b) for b in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


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
