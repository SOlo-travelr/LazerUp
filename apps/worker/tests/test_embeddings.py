"""Tests for the embedding provider selection and vector formatting."""

import importlib

import embeddings


def test_null_provider_when_no_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    importlib.reload(embeddings)
    provider = embeddings.get_embedding_provider()
    assert provider.enabled is False
    assert provider.embed(["x"]) == []


def test_placeholder_key_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-replace-me")
    provider = embeddings.get_embedding_provider()
    assert provider.enabled is False


def test_to_pgvector_format() -> None:
    assert embeddings.to_pgvector([0.5, -1.0]) == "[0.50000000,-1.00000000]"
