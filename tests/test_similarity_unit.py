"""Testes do módulo recommendation.similarity."""

from datetime import date, datetime, timezone

import numpy as np
from src.data.models import Book, User
from src.recommendation.similarity import (
    BookTfidfSimilarity,
    category_author_similarity,
    combined_book_similarity,
    cosine_vec,
    demographic_similarity,
    jaccard_category_sets,
    time_decay_weight,
    user_age,
)


def test_user_age_and_demographic():
    ref = date(2025, 6, 1)
    assert user_age(date(2000, 1, 1), ref) >= 0
    u1 = User(
        name="a",
        email="a@t.com",
        password_hash="x",
        birth_date=date(1990, 1, 1),
        gender="M",
        region="SP",
    )
    u2 = User(
        name="b",
        email="b@t.com",
        password_hash="x",
        birth_date=date(1991, 1, 1),
        gender="M",
        region="SP",
    )
    assert demographic_similarity(u1, u2, ref) > 0.5


def test_jaccard_and_cosine_vec():
    assert jaccard_category_sets(set(), set()) == 0.0
    assert jaccard_category_sets({1, 2}, {2, 3}) > 0.0
    a = np.array([1.0, 0.0])
    b = np.array([1.0, 0.0])
    assert cosine_vec(a, b) == 1.0
    assert cosine_vec(np.zeros(2), np.ones(2)) == 0.0


def test_book_tfidf_similarity():
    b1 = Book(title="python machine learning", author="A", category_id=1, description="data science")
    b1.book_id = 1
    b2 = Book(title="python data analysis", author="B", category_id=1, description="pandas tutorial")
    b2.book_id = 2
    tfidf = BookTfidfSimilarity([b1, b2])
    assert tfidf.book_index(99) is None
    assert tfidf.similarity(1, 2) >= 0.0
    assert tfidf.similarity_to_candidate([], 1) == 0.0
    assert tfidf.similarity_to_candidate([1], 2) >= 0.0


def test_category_and_combined():
    p = Book(title="p", author="Same", category_id=5, description="")
    p.book_id = 1
    c = Book(title="c", author="Same", category_id=5, description="")
    c.book_id = 2
    assert category_author_similarity(p, c) >= 0.65
    assert combined_book_similarity(None, p, c) == category_author_similarity(p, c)


def test_time_decay():
    now = datetime(2025, 1, 10, tzinfo=timezone.utc)
    past = datetime(2025, 1, 1, tzinfo=timezone.utc)
    w = time_decay_weight(past, now, decay_rate=0.1)
    assert 0.0 < w <= 1.0
