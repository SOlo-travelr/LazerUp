"""Connector framework.

Every source (paper / patent / grant / funding / news) implements `Connector`,
giving the pipeline a uniform contract for scheduling, retries, dedup and metrics.
Adding a source = new subclass + a row in the `source` registry. No pipeline change.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Literal, Protocol, runtime_checkable

import httpx

logger = logging.getLogger("connectors")

DocType = Literal["paper", "patent", "grant", "funding", "news"]

# Transient HTTP statuses worth retrying (rate limits + upstream hiccups).
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_RETRYABLE_EXC = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def http_get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
    max_retries: int = 4,
    backoff_base: float = 1.5,
) -> httpx.Response:
    """GET with exponential backoff for rate limits and transient failures.

    Honors a ``Retry-After`` header on 429 responses. Raises the last error if
    every attempt fails so callers can decide whether to fall back gracefully.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code in _RETRY_STATUSES:
                wait = _retry_wait(resp, attempt, backoff_base)
                logger.warning(
                    "http_get retry: url=%s status=%s attempt=%s/%s wait=%.1fs",
                    url, resp.status_code, attempt + 1, max_retries, wait,
                )
                if attempt + 1 < max_retries:
                    time.sleep(wait)
                    continue
            resp.raise_for_status()
            return resp
        except _RETRYABLE_EXC as exc:
            last_exc = exc
            wait = backoff_base ** attempt
            logger.warning(
                "http_get transient error: url=%s err=%s attempt=%s/%s wait=%.1fs",
                url, exc.__class__.__name__, attempt + 1, max_retries, wait,
            )
            if attempt + 1 < max_retries:
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def _retry_wait(resp: httpx.Response, attempt: int, backoff_base: float) -> float:
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return backoff_base ** attempt



@dataclass(slots=True)
class RawRecord:
    """Untransformed payload as fetched from a source."""

    external_id: str
    payload: dict


@dataclass(slots=True)
class NormalizedDocument:
    """Source-agnostic document ready for dedup + storage."""

    doc_type: DocType
    external_id: str
    title: str
    abstract: str | None = None
    url: str | None = None
    published_at: date | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        basis = f"{self.title.strip().lower()}|{(self.abstract or '').strip().lower()}|{self.published_at}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()


@runtime_checkable
class Connector(Protocol):
    name: str
    kind: DocType

    def fetch(self, since: str | None) -> Iterable[RawRecord]:
        """Return raw records published/updated after the watermark `since`."""
        ...

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        """Transform a raw record into a normalized document."""
        ...


class BaseConnector:
    """Convenience base with sane defaults; subclasses set `name`/`kind`."""

    name: str = "base"
    kind: DocType = "paper"

    def fetch(self, since: str | None) -> Iterable[RawRecord]:  # pragma: no cover
        raise NotImplementedError

    def parse(self, raw: RawRecord) -> NormalizedDocument:  # pragma: no cover
        raise NotImplementedError
