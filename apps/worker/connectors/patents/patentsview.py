"""USPTO PatentsView connector."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Iterable

import httpx

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
FIELDS = ["patent_id", "patent_title", "patent_abstract", "patent_date"]


class PatentsViewConnector(BaseConnector):
    name = "uspto_patentsview"
    kind = "patent"

    def fetch(self, since: str | None, per_page: int = 50) -> Iterable[RawRecord]:
        params = {
            "q": json.dumps(QUERY),
            "f": json.dumps(FIELDS),
            "o": json.dumps({"size": per_page}),
        }
        headers = {}
        api_key = os.getenv("PATENTSVIEW_API_KEY", "")
        if api_key:
            headers["X-Api-Key"] = api_key
        try:
            resp = http_get(PATENTSVIEW_API, params=params, headers=headers or None)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            # Host unreachable (e.g. DNS failure in restricted networks): skip
            # this source gracefully instead of failing the whole ingest run.
            logger.warning(
                "patentsview unreachable, skipping source: %s", exc.__class__.__name__
            )
            return
        for patent in resp.json().get("patents", []) or []:
            yield RawRecord(external_id=str(patent.get("patent_id", "")), payload=patent)

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        p = raw.payload
        published = None
        if p.get("patent_date"):
            try:
                published = date.fromisoformat(p["patent_date"])
            except ValueError:
                published = None
        return NormalizedDocument(
            doc_type="patent",
            external_id=raw.external_id,
            title=p.get("patent_title") or "Untitled patent",
            abstract=p.get("patent_abstract"),
            url=f"https://patents.google.com/patent/US{raw.external_id}",
            published_at=published,
            metadata={"source": "uspto_patentsview", "patent_number": raw.external_id},
        )
