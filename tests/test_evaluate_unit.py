"""Testes do módulo evaluate (holdout, métricas agregadas, CLI)."""

import json
import sys
from unittest.mock import MagicMock

import pandas as pd
from src.training.evaluate import (
    _remap_ids,
    evaluate_algorithm,
    holdout_per_user,
    main,
)


def test_remap_ids():
    df = pd.DataFrame({"user_id": [5, 5, 9], "book_id": [100, 101, 200]})
    out, u_map, b_map = _remap_ids(df)
    assert "u_idx" in out.columns and "b_idx" in out.columns
    assert len(u_map) == 2 and len(b_map) == 3


def test_holdout_single_purchase_user():
    df = pd.DataFrame({"user_id": [1], "book_id": [10]})
    train, test_rel = holdout_per_user(df, test_ratio=0.3, seed=1)
    assert len(train) == 1
    assert test_rel.get(1) == set() or not test_rel.get(1)


def test_evaluate_algorithm_popular_style():
    test_rel = {1: {10, 11}, 2: {20}}

    def rec_fn(uid: int) -> list[int]:
        if uid == 1:
            return [10, 12, 13]
        return [20, 21]

    m = evaluate_algorithm("x", rec_fn, [1, 2], test_rel, k=2)
    assert m["algo"] == "x"
    assert "precision_at_2" in m
    assert m["map"] >= 0.0


def test_evaluate_main_success(monkeypatch, capsys, tmp_path):
    df = pd.DataFrame(
        {
            "user_id": [1, 1, 1, 2, 2, 2, 3, 3],
            "book_id": [10, 11, 12, 20, 21, 22, 30, 31],
        }
    )
    monkeypatch.setattr("src.training.evaluate.pd.read_sql_query", lambda *a, **k: df)
    monkeypatch.setattr("src.training.evaluate.create_engine", lambda url: MagicMock())
    monkeypatch.setattr(sys, "argv", ["evaluate", "--k", "3"])
    main()
    out = capsys.readouterr().out
    assert "popular_baseline" in out or "precision" in out.lower()


def test_evaluate_main_empty(monkeypatch, capsys):
    monkeypatch.setattr(
        "src.training.evaluate.pd.read_sql_query",
        lambda *a, **k: pd.DataFrame(columns=["user_id", "book_id"]),
    )
    monkeypatch.setattr("src.training.evaluate.create_engine", lambda url: MagicMock())
    monkeypatch.setattr(sys, "argv", ["evaluate"])
    main()
    assert "error" in capsys.readouterr().out


def test_evaluate_main_writes_output(monkeypatch, tmp_path):
    df = pd.DataFrame({"user_id": [1, 1, 2, 2], "book_id": [10, 11, 20, 21]})
    monkeypatch.setattr("src.training.evaluate.pd.read_sql_query", lambda *a, **k: df)
    monkeypatch.setattr("src.training.evaluate.create_engine", lambda url: MagicMock())
    out_path = tmp_path / "m.json"
    monkeypatch.setattr(sys, "argv", ["evaluate", "--k", "2", "--output", str(out_path)])
    main()
    assert out_path.is_file()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "precision_at_2" in data or "algo" in data
