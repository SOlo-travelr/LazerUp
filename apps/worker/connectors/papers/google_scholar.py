"""Google Scholar connector via SerpAPI.

Uses SerpAPI's `google_scholar` engine to avoid brittle scraping behavior.
Requires `SERPAPI_API_KEY` in the environment.
"""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Iterable

from connectors.base import BaseConnector, NormalizedDocument, RawRecord, http_get

SERP_API = "https://serpapi.com/search.json"
QUERY = (
    "solid-state battery OR lithium-ion battery OR sodium-ion battery OR "
    "lithium metal anode OR silicon anode OR battery recycling OR "
    "grid energy storage OR battery management system"
)


def _extract_year(text: str | None) -> date | None:
    if not text:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if not match:
        return None
    return date(int(match.group(0)), 1, 1)


class GoogleScholarConnector(BaseConnector):
    name = "google_scholar"
    kind = "paper"

    def fetch(
        self,
        since: str | None,
        per_page: int = 20,
        max_pages: int = 10,
    ) -> Iterable[RawRecord]:
        api_key = os.getenv("SERPAPI_API_KEY", "").strip()
        if not api_key:
            return []

        since_year = None
        if since:
            try:
                since_year = date.fromisoformat(since).year
            except ValueError:
                since_year = None

        seen: set[str] = set()
        for page in range(max_pages):
            params = {
                "engine": "google_scholar",
                "q": QUERY,
                "num": per_page,
                "start": page * per_page,
                "hl": "en",
                "api_key": api_key,
            }
            resp = http_get(SERP_API, params=params, timeout=60)
            payload = resp.json()
            rows = payload.get("organic_results") or []
            if not rows:
                break

            emitted = 0
            for row in rows:
                result_id = str(row.get("result_id") or "").strip()
                link = str(row.get("link") or "").strip()
                ext_id = result_id or link
                if not ext_id or ext_id in seen:
                    continue

                publication_summary = ((row.get("publication_info") or {}).get("summary") or "").strip()
                published = _extract_year(publication_summary)
                if since_year and published and published.year <= since_year:
                    continue

                seen.add(ext_id)
                emitted += 1
                yield RawRecord(external_id=ext_id, payload=row)

            if emitted == 0:
                break

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        row = raw.payload
        publication_summary = ((row.get("publication_info") or {}).get("summary") or "").strip()
        published = _extract_year(publication_summary)
        return NormalizedDocument(
            doc_type="paper",
            external_id=raw.external_id,
            title=(row.get("title") or "Untitled").strip(),
            abstract=(row.get("snippet") or "").strip() or None,
            url=(row.get("link") or "").strip() or None,
            published_at=published,
            metadata={
                "source": "google_scholar",
                "publication_info": publication_summary,
            },
        )
