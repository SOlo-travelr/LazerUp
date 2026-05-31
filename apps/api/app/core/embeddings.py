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

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        resp = httpx.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "input": [text]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


def get_embedding_provider() -> EmbeddingProvider:
    key = settings.openai_api_key
    if key and not key.startswith("sk-replace"):
        return OpenAIEmbeddingProvider(api_key=key, model=settings.embedding_model)
    return NullEmbeddingProvider()


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
