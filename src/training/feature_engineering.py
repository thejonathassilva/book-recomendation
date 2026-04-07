from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def load_raw_frames(engine: Engine) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    users = pd.read_sql_query(text("SELECT * FROM users"), engine)
    books = pd.read_sql_query(text("SELECT * FROM books"), engine)
    purchases = pd.read_sql_query(text("SELECT * FROM purchases"), engine)
    categories = pd.read_sql_query(text("SELECT * FROM categories"), engine)
    return users, books, purchases, categories


def age_group(birth: date | datetime | pd.Timestamp) -> str:
    if isinstance(birth, pd.Timestamp):
        birth = birth.date()
    if isinstance(birth, datetime):
        birth = birth.date()
    today = date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    if age < 18:
        return "under_18"
    if age <= 25:
        return "18-25"
    if age <= 35:
        return "26-35"
    if age <= 45:
        return "36-45"
    if age <= 60:
        return "46-60"
    return "60+"


def build_user_features(users: pd.DataFrame, purchases: pd.DataFrame, books: pd.DataFrame) -> pd.DataFrame:
    if purchases.empty:
        return pd.DataFrame()
    b = books.set_index("book_id")
    p = purchases.join(b["category_id"], on="book_id")
    cat_counts = p.groupby("user_id")["category_id"].value_counts().unstack(fill_value=0)
    totals = purchases.groupby("user_id").size().rename("total_purchases")
    spend = purchases.groupby("user_id")["price_paid"].mean().rename("avg_purchase_value")
    last = purchases.groupby("user_id")["purchase_date"].max().rename("last_purchase")
    users_idx = users.set_index("user_id")
    out = users_idx[["region", "gender", "birth_date"]].copy()
    out["age_group"] = out["birth_date"].apply(age_group)
    out = out.join(totals, how="left").join(spend, how="left").join(cat_counts, how="left").join(last, how="left")
    out["total_purchases"] = out["total_purchases"].fillna(0)
    out["avg_purchase_value"] = out["avg_purchase_value"].fillna(0.0)
    for c in cat_counts.columns:
        if c in out.columns:
            out[c] = out[c].fillna(0)
    now = pd.Timestamp.utcnow()
    out["days_since_last_purchase"] = (
        (now - pd.to_datetime(out["last_purchase"])).dt.days.fillna(9999).astype(int)
    )

    def _freq(g: pd.DataFrame) -> float:
        d = pd.to_datetime(g["purchase_date"])
        span_days = max((d.max() - d.min()).days, 1)
        return float(len(g) / (span_days / 30.0))

    freq = purchases.groupby("user_id", group_keys=False).apply(_freq, include_groups=False)
    out["purchase_frequency"] = freq.reindex(out.index).fillna(0.0)
    return out.reset_index()


def build_interaction_sample(
    purchases: pd.DataFrame,
    books: pd.DataFrame,
    sample_book_ids: list[int] | None = None,
    max_users: int | None = 2000,
) -> pd.DataFrame:
    if purchases.empty or books.empty:
        return pd.DataFrame()
    purchases = purchases.copy()
    if "price_paid" not in purchases.columns:
        purchases = purchases.merge(books[["book_id", "price"]], on="book_id", how="left")
        purchases["price_paid"] = purchases["price"]
    user_ids = purchases["user_id"].unique()
    if max_users and len(user_ids) > max_users:
        rng = np.random.default_rng(42)
        user_ids = rng.choice(user_ids, size=max_users, replace=False)
    book_df = books
    if sample_book_ids:
        book_df = books[books["book_id"].isin(sample_book_ids)]
    b_indexed = books.set_index("book_id")
    records = []
    for uid in user_ids:
        up = purchases[purchases["user_id"] == uid]
        bought = set(up["book_id"].tolist())
        for _, bk in book_df.iterrows():
            bid = int(bk["book_id"])
            label = int(bid in bought)
            cid = bk["category_id"]
            same_cat = 0
            for pb in up["book_id"]:
                try:
                    if b_indexed.loc[pb, "category_id"] == cid:
                        same_cat += 1
                except KeyError:
                    continue
            author = bk["author"]
            auth_match = 0
            for pb in up["book_id"]:
                try:
                    if str(b_indexed.loc[pb, "author"] or "").lower() == str(author or "").lower():
                        auth_match = 1
                        break
                except KeyError:
                    continue
            user_prices = up["price_paid"].dropna()
            bp = float(bk["price"] or 0)
            if len(user_prices):
                q25, q75 = user_prices.quantile(0.25), user_prices.quantile(0.75)
                price_match = int(q25 <= bp <= q75)
            else:
                price_match = 0
            records.append(
                {
                    "user_id": uid,
                    "book_id": bid,
                    "label": label,
                    "same_category_purchase_count": same_cat,
                    "author_affinity": auth_match,
                    "price_match": price_match,
                    "category_id": int(cid or 0),
                }
            )
    return pd.DataFrame.from_records(records)
