from unittest.mock import patch

import src.recommendation.embedding_service as emb


def test_book_to_text():
    assert "alpha" in emb.book_to_text("alpha", "Beta", "gamma desc")
    assert emb.book_to_text("", None, None) == "book"


def test_get_encoder_returns_cached():
    sentinel = object()
    emb._model = sentinel
    assert emb.get_encoder() is sentinel


def test_get_encoder_loads_sentence_transformer(monkeypatch):
    monkeypatch.setattr(emb, "_model", None)
    sentinel = object()
    with patch("sentence_transformers.SentenceTransformer", return_value=sentinel):
        got = emb.get_encoder()
    assert got is sentinel
    emb._model = None
