"""Optional LLM client for narrative generation (briefs, reports).

Mirrors the embeddings provider pattern: when no real API key is configured the
provider is disabled and callers fall back to deterministic templates. Scores
never depend on the LLM — only prose does.
"""

from __future__ import annotations

import os
from typing import Protocol

import httpx

_PLACEHOLDER_PREFIX = "sk-replace"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class LLMProvider(Protocol):
    enabled: bool

    def complete(self, system: str, user: str, *, max_tokens: int = 600) -> str | None: ...


class NullLLMProvider:
    enabled = False

    def complete(self, system: str, user: str, *, max_tokens: int = 600) -> str | None:
        return None


class OpenAILLMProvider:
    enabled = True

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 600) -> str | None:
        try:
            resp = httpx.post(
                _OPENAI_URL,
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
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            # Narrative is best-effort; never fail an analytics run on the LLM.
            return None


def get_llm_provider() -> LLMProvider:
    key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("SYNTHESIS_MODEL", "gpt-4o")
    if key and not key.startswith(_PLACEHOLDER_PREFIX):
        return OpenAILLMProvider(key, model)
    return NullLLMProvider()
