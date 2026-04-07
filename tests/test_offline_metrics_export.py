import json
from pathlib import Path

import pytest


def _reset_offline_cache() -> None:
    import src.monitoring.offline_metrics as om

    om._cached_mtime = None
    om._cached_payload = None


def test_metrics_http_includes_offline_when_json_present(client, tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIN_METRICS_EXPORT_PATH", str(tmp_path / "train_metrics_last.json"))
    _reset_offline_cache()
    (tmp_path / "train_metrics_last.json").write_text(
        json.dumps(
            {
                "generated_at_unix": 1_700_000_000,
                "algorithms": {
                    "demo_algo": {"precision_at_10": 0.33, "map": 0.07},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"bookstore_offline_evaluation" in r.content
    assert b"demo_algo" in r.content


@pytest.mark.slow
def test_train_mock_writes_export_json(tmp_path):
    import os
    import subprocess
    import sys

    out = tmp_path / "train_metrics_last.json"
    env = os.environ.copy()
    env["TRAIN_METRICS_EXPORT_PATH"] = str(out)
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "src.training.train", "--mock"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "content_tfidf" in data["algorithms"]
    assert "precision_at_5" in data["algorithms"]["content_tfidf"]
