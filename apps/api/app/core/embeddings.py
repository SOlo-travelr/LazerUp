"""API-side embedding provider.

Mirrors the worker provider so the API can embed search queries. Falls back to
a disabled null provider when no key is configured (search degrades to FTS).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx

from app.core.config import settings

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


@runtime_checkable
class EmbeddingProvider(Protocol):
    enabled: bool

    def embed_query(self, text: str) -> list[float]: ...


class NullEmbeddingProvider:
    enabled = False

    def embed_query(self, text: str) -> list[float]:
        return []


class OpenAIEmbeddingProvider:
    enabled = True

    def __init__(self, api_key: str, model: str, dim: int) -> None:
        self._api_key = api_key
        self._model = model
        self._dim = dim

    def embed_query(self, text: str) -> list[float]:
        payload: dict = {"model": self._model, "input": [text]}
        if self._dim:
            payload["dimensions"] = self._dim
        resp = httpx.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


class OllamaEmbeddingProvider:
    enabled = True

    def __init__(self, base_url: str, model: str) -> None:
        self._url = base_url.rstrip("/") + "/api/embed"
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        resp = httpx.post(
            self._url,
            json={"model": self._model, "input": [text]},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider.lower() == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ollama_url, model=settings.embedding_model
        )
    key = settings.openai_api_key
    if key and not key.startswith("sk-replace"):
        return OpenAIEmbeddingProvider(
            api_key=key, model=settings.embedding_model, dim=settings.embedding_dim
        )
    return NullEmbeddingProvider()


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
