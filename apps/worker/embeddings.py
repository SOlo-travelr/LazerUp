"""Embedding providers.

`get_embedding_provider()` returns an OpenAI-backed provider when an API key is
configured, otherwise a disabled null provider so the pipeline still runs
end-to-end without credentials (embeddings are simply skipped).
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

import httpx

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


@runtime_checkable
class EmbeddingProvider(Protocol):
    enabled: bool
    model: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class NullEmbeddingProvider:
    enabled = False
    model = "none"

    def __init__(self, dim: int = 3072) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return []


class OpenAIEmbeddingProvider:
    enabled = True

    def __init__(self, api_key: str, model: str, dim: int) -> None:
        self._api_key = api_key
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = httpx.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self.model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]


def get_embedding_provider() -> EmbeddingProvider:
    key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    dim = int(os.getenv("EMBEDDING_DIM", "3072"))
    if key and not key.startswith("sk-replace"):
        return OpenAIEmbeddingProvider(api_key=key, model=model, dim=dim)
    return NullEmbeddingProvider(dim=dim)


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
