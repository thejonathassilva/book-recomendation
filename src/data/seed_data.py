"""Synthetic seed data. CLI: python -m src.data.seed_data --users N --books N --purchases N."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import yaml
from faker import Faker
from sqlalchemy import delete, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from src.api.security import hash_password
from src.data.database import SessionLocal
from src.data.models import Book, Category, CategoryWeight, Purchase, Rating, User

fake = Faker("pt_BR")
Faker.seed(42)


def load_category_defaults(config_dir: str) -> dict[str, float]:
    path = Path(config_dir) / "category_weights.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return dict(data.get("defaults") or {})


def reset_tables(session: Session) -> None:
    try:
        session.execute(text("DELETE FROM book_embeddings"))
        session.commit()
    except (ProgrammingError, OperationalError):
        session.rollback()
    session.execute(delete(Rating))
    session.execute(delete(Purchase))
    session.execute(delete(Book))
    session.execute(delete(CategoryWeight))
    session.execute(delete(Category))
    session.execute(delete(User))
    session.commit()


def seed_categories(session: Session, config_dir: str) -> dict[str, int]:
    defaults = load_category_defaults(config_dir)
    name_to_id: dict[str, int] = {}
    for name, w in defaults.items():
        c = Category(name=name, weight=float(w))
        session.add(c)
        session.flush()
        name_to_id[name] = c.category_id
        session.add(CategoryWeight(category_id=c.category_id, weight=float(w)))
    session.commit()
    return name_to_id


def age_from_birth(b: date) -> int:
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def seed_users(session: Session, n: int) -> list[User]:
    regions = ["SP", "RJ", "MG", "RS", "PR", "BA", "PE", "CE", "DF", "AM"]
    genders = ["M", "F", "Outro"]
    users: list[User] = []
    admin = User(
        name="Administrador",
        email="admin@bookstore.com",
        password_hash=hash_password("admin123"),
        birth_date=date(1985, 1, 1),
        gender="Outro",
        region="DF",
        is_admin=True,
    )
    users.append(admin)
    session.add(admin)
    session.flush()
    demo = User(
        name="Usuário Demo",
        email="demo@bookstore.com",
        password_hash=hash_password("demo123"),
        birth_date=date(1990, 6, 15),
        gender="F",
        region="SP",
        is_admin=False,
    )
    users.append(demo)
    session.add(demo)
    session.flush()
    synthetic: list[User] = []
    for i in range(max(0, n - 2)):
        birth = fake.date_of_birth(minimum_age=16, maximum_age=75)
        u = User(
            name=fake.name(),
            email=f"user{i}_{fake.uuid4()[:8]}@demo.bookstore",
            password_hash=hash_password("demo123"),
            birth_date=birth,
            gender=np.random.choice(genders, p=[0.48, 0.48, 0.04]),
            region=np.random.choice(regions),
            is_admin=False,
        )
        synthetic.append(u)
        users.append(u)
    session.add_all(synthetic)
    session.commit()
    for u in users:
        session.refresh(u)
    return users


def seed_books(session: Session, n: int, name_to_cat: dict[str, int]) -> list[Book]:
    cat_names = list(name_to_cat.keys())
    books: list[Book] = []
    for i in range(n):
        cat = str(np.random.choice(cat_names, p=np.ones(len(cat_names)) / len(cat_names)))
        cid = name_to_cat[cat]
        title = fake.catch_phrase() + f" — Vol {i}"
        author = fake.name()
        desc = fake.text(max_nb_chars=800)
        price = Decimal(str(round(np.random.uniform(15, 120), 2)))
        b = Book(
            title=title[:500],
            author=author[:300],
            isbn=f"{np.random.randint(10**12, 10**13)}",
            category_id=cid,
            price=price,
            description=desc,
            cover_url=f"https://picsum.photos/seed/{i}/200/300",
        )
        books.append(b)
    session.add_all(books)
    session.commit()
    for b in books:
        session.refresh(b)
    return books


def category_affinity_for_user(u: User, book_category_names: list[str], name_to_cat: dict[str, int]) -> np.ndarray:
    age = age_from_birth(u.birth_date)
    weights = np.ones(len(book_category_names), dtype=float)
    for i, nm in enumerate(book_category_names):
        if nm == "Infantil" and age > 14:
            weights[i] *= 0.2
        if nm == "Infantil" and age <= 12:
            weights[i] *= 2.5
        if nm == "Academico" and 18 <= age <= 30:
            weights[i] *= 1.4
        if nm == "Tecnologia" and u.region in ("SP", "DF", "PR"):
            weights[i] *= 1.3
        if nm == "Romance" and u.gender == "F":
            weights[i] *= 1.15
    weights /= weights.sum()
    return weights


def seed_purchases(
    session: Session,
    users: list[User],
    books: list[Book],
    name_to_cat: dict[str, int],
    total: int,
    batch: int = 5000,
) -> None:
    book_ids = np.array([b.book_id for b in books])
    book_cat = np.array([b.category_id for b in books])
    books_by_id = {b.book_id: b for b in books}
    cat_names = list(name_to_cat.keys())

    start = datetime.now() - timedelta(days=730)
    rng = np.random.default_rng(123)

    rows_since_commit = 0
    generated = 0
    while generated < total:
        u = users[int(rng.integers(0, len(users)))]
        aff = category_affinity_for_user(u, cat_names, name_to_cat)
        cat_i = int(rng.choice(len(cat_names), p=aff))
        cid = name_to_cat[cat_names[cat_i]]
        mask = book_cat == cid
        eligible = book_ids[mask]
        if eligible.size == 0:
            eligible = book_ids
        b_id = int(rng.choice(eligible))
        day_offset = rng.integers(0, 730)
        ts = start + timedelta(days=int(day_offset), hours=int(rng.integers(0, 24)))
        book = books_by_id[b_id]
        price = book.price or Decimal("29.90")
        p = Purchase(
            user_id=u.user_id,
            book_id=b_id,
            purchase_date=ts,
            price_paid=price,
            quantity=1,
        )
        session.add(p)
        rows_since_commit += 1
        generated += 1
        if rows_since_commit >= batch:
            session.commit()
            rows_since_commit = 0
    if rows_since_commit:
        session.commit()


def seed_ratings_sample(session: Session, users: list[User], books: list[Book], n: int) -> None:
    rng = np.random.default_rng(7)
    pairs = set()
    while len(pairs) < min(n, len(users) * len(books)):
        u = users[int(rng.integers(0, len(users)))].user_id
        b = books[int(rng.integers(0, len(books)))].book_id
        if (u, b) in pairs:
            continue
        pairs.add((u, b))
        session.add(Rating(user_id=u, book_id=b, score=int(rng.integers(3, 6))))
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=2000)
    parser.add_argument("--books", type=int, default=1500)
    parser.add_argument("--purchases", type=int, default=48000)
    parser.add_argument("--ratings", type=int, default=4000)
    parser.add_argument("--config-dir", default=os.environ.get("CONFIG_DIR", "config"))
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Após o seed, gera embeddings pgvector (PostgreSQL; pode demorar; requer torch/sentence-transformers).",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        if not args.no_reset:
            reset_tables(session)
        name_to_cat = seed_categories(session, args.config_dir)
        users = seed_users(session, args.users)
        books = seed_books(session, args.books, name_to_cat)
        seed_purchases(session, users, books, name_to_cat, args.purchases)
        seed_ratings_sample(session, users, books, args.ratings)
        print(f"Seeded {len(users)} users, {len(books)} books, {args.purchases} purchases, ratings sample.")
        if args.embed:
            try:
                from src.data.sync_book_embeddings import sync_all

                rc = sync_all(batch_size=32, limit=None)
                if rc != 0:
                    print("Aviso: embeddings não gerados (ver pgvector e dependências).", file=sys.stderr)
            except Exception as e:
                print(f"Aviso: falha ao gerar embeddings: {e}", file=sys.stderr)
    finally:
        session.close()


if __name__ == "__main__":
    main()
