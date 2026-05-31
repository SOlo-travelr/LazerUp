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

    def __init__(self, dim: int = 1536) -> None:
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
        payload: dict = {"model": self.model, "input": texts}
        # text-embedding-3-* support truncating to a smaller dimension, keeping
        # vectors within pgvector's HNSW limit (<=2000) while staying high-quality.
        if self.dim:
            payload["dimensions"] = self.dim
        resp = httpx.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]


class OllamaEmbeddingProvider:
    """Local embeddings via an Ollama server (e.g. nomic-embed-text, bge-m3)."""

    enabled = True

    def __init__(self, base_url: str, model: str, dim: int) -> None:
        self._url = base_url.rstrip("/") + "/api/embed"
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = httpx.post(
            self._url,
            json={"model": self.model, "input": texts},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    dim = int(os.getenv("EMBEDDING_DIM", "1536"))
    if provider == "ollama":
        base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        return OllamaEmbeddingProvider(base_url=base_url, model=model, dim=dim)
    key = os.getenv("OPENAI_API_KEY", "")
    if key and not key.startswith("sk-replace"):
        return OpenAIEmbeddingProvider(api_key=key, model=model, dim=dim)
    return NullEmbeddingProvider(dim=dim)


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
