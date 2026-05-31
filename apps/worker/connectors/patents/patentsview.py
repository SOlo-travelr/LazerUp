"""USPTO PatentsView connector."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Iterable

import httpx

from connectors.cache import read_cache, write_cache
from connectors.base import (
    BaseConnector,
    NormalizedDocument,
    RawRecord,
    http_get,
    logger,
)

PATENTSVIEW_API = "https://search.patentsview.org/api/v1/patent/"
QUERY = {
    "_and": [
        {"_gte": {"patent_date": "2023-01-01"}},
        {
            "_or": [
                {"_text_phrase": {"patent_abstract": "solid-state electrolyte"}},
                {"_text_phrase": {"patent_abstract": "lithium metal anode"}},
                {"_text_phrase": {"patent_abstract": "battery cell"}},
            ]
        },
    ]
}
FIELDS = [
    "patent_id",
    "patent_title",
    "patent_abstract",
    "patent_date",
    "inventors.inventor_first_name",
    "inventors.inventor_last_name",
    "assignees.assignee_organization",
]


class PatentsViewConnector(BaseConnector):
    name = "uspto_patentsview"
    kind = "patent"

    def fetch(
        self,
        since: str | None,
        per_page: int = 50,
        max_pages: int = 3,
    ) -> Iterable[RawRecord]:
        headers = {}
        api_key = os.getenv("PATENTSVIEW_API_KEY", "")
        if api_key:
            headers["X-Api-Key"] = api_key
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            params = {
                "q": json.dumps(QUERY),
                "f": json.dumps(FIELDS),
                "o": json.dumps({"size": per_page, "page": page}),
            }
            cache_key = f"patentsview_page_{page}"
            payload: dict | None = None
            try:
                resp = http_get(PATENTSVIEW_API, params=params, headers=headers or None)
                payload = resp.json()
                write_cache(cache_key, payload)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                logger.warning(
                    "patentsview unreachable, trying cache page=%s: %s",
                    page,
                    exc.__class__.__name__,
                )
                payload = read_cache(cache_key)
                if payload is None:
                    continue
            except Exception:
                payload = read_cache(cache_key)
                if payload is None:
                    continue

            batch = payload.get("patents", []) or []
            if not batch:
                break

            emitted = 0
            for patent in batch:
                ext_id = str(patent.get("patent_id", ""))
                if not ext_id or ext_id in seen:
                    continue
                seen.add(ext_id)
                emitted += 1
                yield RawRecord(external_id=ext_id, payload=patent)
            if emitted == 0:
                break

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        p = raw.payload
        published = None
        if p.get("patent_date"):
            try:
                published = date.fromisoformat(p["patent_date"])
            except ValueError:
                published = None
        inventors = []
        for inv in p.get("inventors") or []:
            first = (inv or {}).get("inventor_first_name") or ""
            last = (inv or {}).get("inventor_last_name") or ""
            name = (f"{first} {last}").strip()
            if name:
                inventors.append(name)
        assignees = []
        for assignee in p.get("assignees") or []:
            name = (assignee or {}).get("assignee_organization")
            if name:
                assignees.append(name)
        return NormalizedDocument(
            doc_type="patent",
            external_id=raw.external_id,
            title=p.get("patent_title") or "Untitled patent",
            abstract=p.get("patent_abstract"),
            url=f"https://patents.google.com/patent/US{raw.external_id}",
            published_at=published,
            metadata={
                "source": "uspto_patentsview",
                "patent_number": raw.external_id,
                "inventors": inventors,
                "assignees": assignees,
            },
        )
