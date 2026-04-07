from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

if TYPE_CHECKING:
    from src.data.models import Book, User


def user_age(birth: date, ref: date | None = None) -> int:
    ref = ref or date.today()
    y = ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))
    return max(y, 0)


def demographic_similarity(u: User, v: User, ref: date | None = None) -> float:
    score = 0.0
    if u.region == v.region:
        score += 0.3
    au, av = user_age(u.birth_date, ref), user_age(v.birth_date, ref)
    if abs(au - av) <= 5:
        score += 0.4
    if u.gender == v.gender:
        score += 0.3
    return min(score, 1.0)


def jaccard_category_sets(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cosine_vec(va: np.ndarray, vb: np.ndarray) -> float:
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


class BookTfidfSimilarity:
    def __init__(self, books: list[Book]) -> None:
        self._book_ids: list[int] = []
        corpus: list[str] = []
        for b in books:
            self._book_ids.append(b.book_id)
            text = " ".join(
                filter(
                    None,
                    [
                        b.title or "",
                        b.author or "",
                        (b.description or "")[:2000],
                    ],
                )
            )
            corpus.append(text or "empty")
        self._vectorizer = TfidfVectorizer(max_features=4096, min_df=1, stop_words="english")
        self._matrix = self._vectorizer.fit_transform(corpus)

    def book_index(self, book_id: int) -> int | None:
        try:
            return self._book_ids.index(book_id)
        except ValueError:
            return None

    def similarity(self, book_id_a: int, book_id_b: int) -> float:
        ia, ib = self.book_index(book_id_a), self.book_index(book_id_b)
        if ia is None or ib is None:
            return 0.0
        sim = cosine_similarity(self._matrix[ia], self._matrix[ib])
        return float(sim[0, 0])

    def similarity_to_candidate(self, purchased_book_ids: list[int], candidate_id: int) -> float:
        ic = self.book_index(candidate_id)
        if ic is None or not purchased_book_ids:
            return 0.0
        scores: list[float] = []
        for pid in purchased_book_ids:
            ip = self.book_index(pid)
            if ip is None:
                continue
            s = cosine_similarity(self._matrix[ip], self._matrix[ic])[0, 0]
            scores.append(float(s))
        return max(scores) if scores else 0.0


def category_author_similarity(purchase_book: Book, candidate: Book) -> float:
    s = 0.0
    if purchase_book.category_id and purchase_book.category_id == candidate.category_id:
        s += 0.65
    pa, ca = (purchase_book.author or "").lower(), (candidate.author or "").lower()
    if pa and ca and pa == ca:
        s += 0.35
    return min(s, 1.0)


def combined_book_similarity(
    tfidf: BookTfidfSimilarity | None,
    purchase_book: Book,
    candidate: Book,
    tfidf_weight: float = 0.6,
) -> float:
    struct = category_author_similarity(purchase_book, candidate)
    if tfidf is None:
        return struct
    t = tfidf.similarity(purchase_book.book_id, candidate.book_id)
    return tfidf_weight * t + (1.0 - tfidf_weight) * struct


def time_decay_weight(purchase_date: datetime, now: datetime, decay_rate: float) -> float:
    days_ago = max((now - purchase_date).days, 0)
    return float(np.exp(-decay_rate * days_ago))
