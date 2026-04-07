"""Cobertura de parsing e branches em offline_metrics."""

import json

from src.monitoring import offline_metrics as om


def test_parse_mlflow_style_key():
    assert om._parse_mlflow_style_key("map") == ("map", "")
    assert om._parse_mlflow_style_key("precision_at_10")[0] == "precision"
    assert om._parse_mlflow_style_key("recall_at_5")[0] == "recall"
    assert om._parse_mlflow_style_key("ndcg_at_3")[0] == "ndcg"
    assert om._parse_mlflow_style_key("unknown_metric")[0] == "unknown_metric"


def test_default_export_path(monkeypatch):
    monkeypatch.delenv("TRAIN_METRICS_EXPORT_PATH", raising=False)
    p = om._default_export_path()
    assert p.name == "train_metrics_last.json"


def test_apply_offline_metrics_skips_non_float(tmp_path, monkeypatch):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "generated_at_unix": 100,
                "algorithms": {"a": {"precision_at_5": "bad", "map": 0.1}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRAIN_METRICS_EXPORT_PATH", str(p))
    om._cached_mtime = None
    om._cached_payload = None
    om.apply_offline_metrics_from_file()


def test_apply_offline_metrics_bad_json(tmp_path, monkeypatch):
    p = tmp_path / "bad.json"
    p.write_text("{", encoding="utf-8")
    monkeypatch.setenv("TRAIN_METRICS_EXPORT_PATH", str(p))
    om._cached_mtime = None
    om._cached_payload = None
    om.apply_offline_metrics_from_file()


def test_apply_offline_metrics_not_dict_payload(tmp_path, monkeypatch):
    p = tmp_path / "x.json"
    p.write_text("[1,2]", encoding="utf-8")
    monkeypatch.setenv("TRAIN_METRICS_EXPORT_PATH", str(p))
    om._cached_mtime = None
    om._cached_payload = None
    om.apply_offline_metrics_from_file()


def test_apply_nan_metric_skipped(tmp_path, monkeypatch):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "generated_at_unix": 1,
                "algorithms": {"x": {"map": float("nan")}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRAIN_METRICS_EXPORT_PATH", str(p))
    om._cached_mtime = None
    om._cached_payload = None
    om.apply_offline_metrics_from_file()
