"""Testes de recommendation.weights."""

import os

from src.data.models import Category, CategoryWeight
from src.recommendation.weights import category_weight_map, load_yaml_defaults


def test_load_yaml_defaults_missing_dir(tmp_path):
    assert load_yaml_defaults(str(tmp_path / "nope")) == {}


def test_load_yaml_defaults_reads_config():
    d = load_yaml_defaults(os.path.join(os.path.dirname(__file__), "..", "config"))
    assert isinstance(d, dict)


def test_category_weight_map_prefers_table(db_session):
    c = Category(name="WCat", weight=1.0)
    db_session.add(c)
    db_session.flush()
    db_session.add(CategoryWeight(category_id=c.category_id, weight=2.5))
    db_session.commit()
    m = category_weight_map(db_session, os.path.join(os.path.dirname(__file__), "..", "config"))
    assert m[c.category_id] == 2.5
