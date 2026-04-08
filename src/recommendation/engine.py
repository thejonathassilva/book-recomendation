from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sqlalchemy.orm import Session

from src.data.models import Book, Purchase, User
from src.data.repositories import books as books_repo
from src.data.repositories import purchases as purchases_repo
from src.data.repositories import users as users_repo
from src.recommendation import similarity as sim
from src.recommendation import vector_store as vs
from src.recommendation.weights import category_weight_map


def _finite_python_float(x: float) -> float:
    v = float(x)
    if not math.isfinite(v):
        return 0.0
    return v


def _redis_client():  # type: ignore[no-untyped-def]
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return None
    try:
        import redis

        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def invalidate_recommendation_cache_for_user(user_id: int) -> None:
    r = _redis_client()
    if not r:
        return
    try:
        for key in r.scan_iter(match=f"rec:{user_id}:*"):
            r.delete(key)
    except Exception:
        pass


@dataclass
class EngineConfig:
    user_history_weight: float = 0.50
    similar_users_weight: float = 0.35
    vector_weight: float = 0.15
    decay_rate: float = 0.005
    demographic_part: float = 0.3
    behavioral_part: float = 0.7
    similar_users_top_k: int = 50
    max_candidates: int = 500
    config_dir: str | None = None
    tfidf_max_books: int = 12000

    def __post_init__(self) -> None:
        if os.environ.get("REC_W_OWN"):
            self.user_history_weight = float(os.environ["REC_W_OWN"])
        if os.environ.get("REC_W_SIM"):
            self.similar_users_weight = float(os.environ["REC_W_SIM"])
        if os.environ.get("REC_W_VEC"):
            self.vector_weight = float(os.environ["REC_W_VEC"])
        if os.environ.get("REC_TFIDF_MAX_BOOKS"):
            z = os.environ["REC_TFIDF_MAX_BOOKS"].strip()
            self.tfidf_max_books = 0 if z in ("", "0") else int(z)


class RecommendationEngine:
    def __init__(self, db: Session, cfg: EngineConfig | None = None) -> None:
        self.db = db
        self.cfg = cfg or EngineConfig(
            config_dir=os.environ.get("CONFIG_DIR"),
        )
        self._redis = _redis_client()
        self._cat_weights: dict[int, float] | None = None
        self._tfidf: sim.BookTfidfSimilarity | None = None
        self._user_cat_matrix: dict[int, dict[int, float]] | None = None
        self._user_category_sets: dict[int, set[int]] | None = None
        self._all_users: dict[int, User] | None = None
        self._batch_purchases: list[Purchase] | None = None
        self._batch_similar: list[tuple[User, float]] | None = None
        self._batch_target_user: User | None = None

    def _begin_recommend_batch(self, user_id: int) -> None:
        self._batch_purchases = purchases_repo.get_user_purchases(self.db, user_id)
        self._batch_target_user = users_repo.get_by_id(self.db, user_id)
        self._batch_similar = (
            self.find_similar_users(self._batch_target_user)
            if self._batch_target_user is not None
            else []
        )

    def _clear_recommend_batch(self) -> None:
        self._batch_purchases = None
        self._batch_similar = None
        self._batch_target_user = None

    def _ensure_indexes(self) -> None:
        if self._cat_weights is None:
            self._cat_weights = category_weight_map(self.db, self.cfg.config_dir)
        if self._tfidf is None:
            cap = self.cfg.tfidf_max_books if self.cfg.tfidf_max_books > 0 else None
            all_books = books_repo.list_all(self.db, limit=cap)
            if not all_books:
                self._tfidf = None
            else:
                try:
                    self._tfidf = sim.BookTfidfSimilarity(all_books)
                except ValueError:
                    self._tfidf = None
        if self._user_cat_matrix is None:
            self._user_cat_matrix = purchases_repo.user_category_counts(self.db)
            self._user_category_sets = {uid: set(d.keys()) for uid, d in self._user_cat_matrix.items()}
        if self._all_users is None:
            users = purchases_repo.all_users_minimal(self.db)
            self._all_users = {u.user_id: u for u in users}

    def get_category_weight(self, category_id: int | None) -> float:
        self._ensure_indexes()
        if category_id is None:
            return 1.0
        return float(self._cat_weights.get(category_id, 1.0))

    def score_perfil_proprio(
        self,
        user_id: int,
        candidate: Book,
        now: datetime | None = None,
    ) -> float:
        self._ensure_indexes()
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        purchases = (
            self._batch_purchases
            if self._batch_purchases is not None
            else purchases_repo.get_user_purchases(self.db, user_id)
        )
        if not purchases:
            return 0.0
        score = 0.0
        total_w = 0.0
        for p in purchases:
            b = p.book
            if b is None:
                continue
            pd = p.purchase_date
            if pd.tzinfo is None:
                pd = pd.replace(tzinfo=timezone.utc)
            tw = sim.time_decay_weight(pd, now, self.cfg.decay_rate)
            cid = b.category_id
            cw = self.get_category_weight(cid)
            sim_b = sim.combined_book_similarity(self._tfidf, b, candidate)
            combined = tw * cw
            score += combined * sim_b
            total_w += combined
        if total_w <= 0:
            return 0.0
        return score / total_w

    def _behavioral_similarity(self, u_id: int, v_id: int) -> float:
        assert self._user_cat_matrix is not None
        assert self._user_category_sets is not None
        vu = self._user_cat_matrix.get(u_id, {})
        vv = self._user_cat_matrix.get(v_id, {})
        cats_u = self._user_category_sets.get(u_id, set())
        cats_v = self._user_category_sets.get(v_id, set())
        jac = sim.jaccard_category_sets(cats_u, cats_v)
        all_cats = sorted(cats_u | cats_v)
        if not all_cats:
            return jac
        vec_u = np.array([vu.get(c, 0.0) for c in all_cats], dtype=float)
        vec_v = np.array([vv.get(c, 0.0) for c in all_cats], dtype=float)
        cos = sim.cosine_vec(vec_u, vec_v)
        return 0.5 * jac + 0.5 * cos

    def find_similar_users(self, target_user: User) -> list[tuple[User, float]]:
        self._ensure_indexes()
        assert self._all_users is not None
        from datetime import date

        ref_date = date.today()
        similarities: list[tuple[User, float]] = []
        for uid, user in self._all_users.items():
            if uid == target_user.user_id:
                continue
            if uid not in (self._user_cat_matrix or {}):
                continue
            d_demo = sim.demographic_similarity(target_user, user, ref_date)
            d_beh = self._behavioral_similarity(target_user.user_id, uid)
            total = self.cfg.demographic_part * d_demo + self.cfg.behavioral_part * d_beh
            similarities.append((user, total))
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[: self.cfg.similar_users_top_k]

    def score_usuarios_similares(
        self,
        user_id: int,
        candidate: Book,
        now: datetime | None = None,
    ) -> float:
        self._ensure_indexes()
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        target = self._batch_target_user if self._batch_target_user is not None else users_repo.get_by_id(self.db, user_id)
        if target is None:
            return 0.0
        similar = self._batch_similar if self._batch_similar is not None else self.find_similar_users(target)
        cand_cat = candidate.category_id
        cw_cand = self.get_category_weight(cand_cat)
        sim_map = {u.user_id: s for u, s in similar}
        similar_ids = list(sim_map.keys())
        if not similar_ids:
            return 0.0
        p_list = purchases_repo.purchases_for_book_by_users(self.db, similar_ids, candidate.book_id)
        num = 0.0
        den = 0.0
        for p in p_list:
            user_sim = sim_map.get(p.user_id, 0.0)
            if user_sim <= 0:
                continue
            pd = p.purchase_date
            if pd.tzinfo is None:
                pd = pd.replace(tzinfo=timezone.utc)
            tw = sim.time_decay_weight(pd, now, self.cfg.decay_rate)
            if tw <= 0:
                continue
            num += user_sim * tw
            den += tw
        if den <= 0:
            return 0.0
        return (num / den) * cw_cand

    def score_vector_semantic(self, user_id: int, candidate: Book) -> float:
        if not vs.pgvector_enabled(self.db) or self.cfg.vector_weight <= 0:
            return 0.0
        cand_vec = vs.get_book_embedding(self.db, candidate.book_id)
        if cand_vec is None:
            return 0.0
        plist = (
            self._batch_purchases
            if self._batch_purchases is not None
            else purchases_repo.get_user_purchases(self.db, user_id)
        )
        pids = [p.book_id for p in plist]
        prof = vs.get_user_profile_embedding(self.db, user_id, pids)
        if prof is None:
            target = self._batch_target_user if self._batch_target_user is not None else users_repo.get_by_id(self.db, user_id)
            if target is None:
                return 0.0
            similar = self._batch_similar if self._batch_similar is not None else self.find_similar_users(target)
            prof = vs.cold_start_profile_from_similar(self.db, similar, purchases_repo)
        if prof is None:
            return 0.0
        cos = vs.cosine_similarity(prof, cand_vec)
        return max(0.0, min(1.0, (cos + 1.0) / 2.0))

    def final_score(self, user_id: int, candidate: Book, now: datetime | None = None) -> float:
        s_own = self.score_perfil_proprio(user_id, candidate, now)
        s_sim = self.score_usuarios_similares(user_id, candidate, now)
        s_vec = self.score_vector_semantic(user_id, candidate)
        total = (
            float(self.cfg.user_history_weight) * float(s_own)
            + float(self.cfg.similar_users_weight) * float(s_sim)
            + float(self.cfg.vector_weight) * float(s_vec)
        )
        return _finite_python_float(total)

    def recommend(
        self,
        user_id: int,
        limit: int = 20,
        use_cache: bool = True,
        cache_ttl: int | None = None,
    ) -> list[tuple[Book, float]]:
        ttl = cache_ttl or int(os.environ.get("REC_CACHE_TTL", "3600"))
        cache_key = f"rec:{user_id}:{limit}"
        if use_cache and self._redis:
            raw = self._redis.get(cache_key)
            if raw:
                try:
                    data = json.loads(raw)
                    items = data.get("items")
                    if not isinstance(items, list):
                        raise ValueError("invalid cache shape")
                    ids_scores = [
                        (int(x[0]), _finite_python_float(float(x[1])))
                        for x in items
                        if isinstance(x, (list, tuple)) and len(x) >= 2
                    ]
                except (json.JSONDecodeError, TypeError, ValueError, KeyError):
                    ids_scores = []
                else:
                    books = []
                    for bid, sc in ids_scores:
                        b = books_repo.get_by_id(self.db, bid)
                        if b:
                            books.append((b, sc))
                    if books:
                        return books

        out: list[tuple[Book, float]] = []
        self._ensure_indexes()
        self._begin_recommend_batch(user_id)
        try:
            sample_k = self.cfg.max_candidates if self.cfg.max_candidates > 0 else 500
            candidates = books_repo.sample_books_not_purchased_by_user(self.db, user_id, sample_k)

            scored: list[tuple[Book, float]] = []
            for c in candidates:
                sc = _finite_python_float(self.final_score(user_id, c))
                scored.append((c, sc))
            scored.sort(key=lambda x: x[1], reverse=True)
            out = scored[:limit]
        finally:
            self._clear_recommend_batch()

        if use_cache and self._redis and out:
            payload = {
                "items": [[b.book_id, _finite_python_float(s)] for b, s in out],
            }
            try:
                self._redis.setex(cache_key, ttl, json.dumps(payload))
            except (TypeError, ValueError):
                pass

        return out
