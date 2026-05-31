"""Semantic Scholar connector (Graph API bulk search)."""

from __future__ import annotations

import os
from datetime import date
from typing import Iterable

from connectors.base import BaseConnector, NormalizedDocument, RawRecord, http_get

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,year,url,externalIds,publicationDate"
QUERY = "solid-state battery OR lithium metal anode OR sodium-ion battery"


class SemanticScholarConnector(BaseConnector):
    name = "semantic_scholar"
    kind = "paper"

    def fetch(self, since: str | None, limit: int = 50) -> Iterable[RawRecord]:
        headers = {}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        if api_key:
            headers["x-api-key"] = api_key
        resp = http_get(
            S2_API,
            params={"query": QUERY, "fields": FIELDS, "limit": limit},
            headers=headers or None,
        )
        for paper in resp.json().get("data", []):
            ext = paper.get("externalIds", {}) or {}
            ext_id = ext.get("DOI") or paper.get("paperId") or ""
            yield RawRecord(external_id=str(ext_id), payload=paper)

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
        return NormalizedDocument(
            doc_type="paper",
            external_id=raw.external_id,
            title=p.get("title") or "Untitled",
            abstract=p.get("abstract"),
            url=p.get("url"),
            published_at=published,
            metadata={"source": "semantic_scholar", "year": p.get("year")},
        )
