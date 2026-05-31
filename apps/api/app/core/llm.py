"""API-side LLM provider for RAG answers and synthesis.

Mirrors the embeddings provider: disabled (null) when no real key is set, so the
/ask endpoint degrades to an extractive answer instead of failing.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx

from app.core.config import settings

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


@runtime_checkable
class LLMProvider(Protocol):
    enabled: bool

    def complete(self, system: str, user: str, *, max_tokens: int = 700) -> str | None: ...


class NullLLMProvider:
    enabled = False

    def complete(self, system: str, user: str, *, max_tokens: int = 700) -> str | None:
        return None


class OpenAILLMProvider:
    enabled = True

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 700) -> str | None:
        try:
            resp = httpx.post(
                OPENAI_CHAT_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return None


def get_llm_provider() -> LLMProvider:
    key = settings.openai_api_key
    if key and not key.startswith("sk-replace"):
        return OpenAILLMProvider(api_key=key, model=settings.synthesis_model)
    return NullLLMProvider()
