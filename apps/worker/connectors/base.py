"""Connector framework.

Every source (paper / patent / grant / funding / news) implements `Connector`,
giving the pipeline a uniform contract for scheduling, retries, dedup and metrics.
Adding a source = new subclass + a row in the `source` registry. No pipeline change.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Literal, Protocol, runtime_checkable

DocType = Literal["paper", "patent", "grant", "funding", "news"]


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
