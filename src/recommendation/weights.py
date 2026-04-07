import os
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import Category, CategoryWeight


def load_yaml_defaults(config_dir: str | None = None) -> dict[str, float]:
    base = Path(config_dir or os.environ.get("CONFIG_DIR", "config"))
    path = base / "category_weights.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return dict(data.get("defaults") or {})


def category_weight_map(db: Session, config_dir: str | None = None) -> dict[int, float]:
    defaults = load_yaml_defaults(config_dir)
    rows = db.execute(select(Category)).scalars().all()
    cw_rows = {r.category_id: r.weight for r in db.execute(select(CategoryWeight)).scalars().all()}
    out: dict[int, float] = {}
    for c in rows:
        w = float(defaults.get(c.name, c.weight))
        if c.category_id in cw_rows:
            w = float(cw_rows[c.category_id])
        out[c.category_id] = w
    return out
