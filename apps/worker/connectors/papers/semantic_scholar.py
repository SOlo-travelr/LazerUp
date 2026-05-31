"""Semantic Scholar connector (Graph API bulk search)."""

from __future__ import annotations

import os
from datetime import date
from typing import Iterable

from connectors.base import BaseConnector, NormalizedDocument, RawRecord, http_get
from connectors.cache import read_cache, write_cache

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,year,url,externalIds,publicationDate,authors"
QUERY = (
    "solid-state battery OR lithium metal anode OR sodium-ion battery OR "
    "silicon anode OR cathode material OR battery recycling OR "
    "grid energy storage OR stationary storage OR battery management system OR "
    "fast charging OR lithium-sulfur battery OR separator OR electrolyte additive"
)


class SemanticScholarConnector(BaseConnector):
    name = "semantic_scholar"
    kind = "paper"

    def fetch(
        self,
        since: str | None,
        limit: int = 50,
        max_pages: int = 4,
    ) -> Iterable[RawRecord]:
        headers = {}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        if api_key:
            headers["x-api-key"] = api_key
        seen: set[str] = set()
        for page in range(max_pages):
            offset = page * limit
            params = {"query": QUERY, "fields": FIELDS, "limit": limit, "offset": offset}
            cache_key = f"semantic_scholar_page_{page}"
            payload: dict | None = None
            try:
                resp = http_get(S2_API, params=params, headers=headers or None)
                payload = resp.json()
                write_cache(cache_key, payload)
            except Exception:
                payload = read_cache(cache_key)
                if payload is None:
                    continue

            batch = payload.get("data", []) or []
            if not batch:
                break

            emitted = 0
            for paper in batch:
                ext = paper.get("externalIds", {}) or {}
                ext_id = str(ext.get("DOI") or paper.get("paperId") or "")
                if not ext_id or ext_id in seen:
                    continue
                seen.add(ext_id)
                emitted += 1
                yield RawRecord(external_id=ext_id, payload=paper)
            if emitted == 0:
                break

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        p = raw.payload
        published = None
        if p.get("publicationDate"):
            try:
                published = date.fromisoformat(p["publicationDate"])
            except ValueError:
                published = None
        if published is None and p.get("year"):
            published = date(int(p["year"]), 1, 1)
        authors = []
        for author in p.get("authors") or []:
            name = (author or {}).get("name")
            if name:
                authors.append(name)
        return NormalizedDocument(
            doc_type="paper",
            external_id=raw.external_id,
            title=p.get("title") or "Untitled",
            abstract=p.get("abstract"),
            url=p.get("url"),
            published_at=published,
            metadata={
                "source": "semantic_scholar",
                "year": p.get("year"),
                "authors": authors,
            },
        )
