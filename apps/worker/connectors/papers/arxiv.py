"""arXiv connector (cond-mat / battery query).

M1 reference implementation of the Connector contract. Network calls are kept
behind `fetch` so the pipeline can be unit-tested with stubbed records.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from connectors.base import BaseConnector, NormalizedDocument, RawRecord, http_get

ARXIV_API = "https://export.arxiv.org/api/query"
QUERY = 'all:"solid-state battery" OR all:"lithium battery" OR all:"sodium-ion"'


class ArxivConnector(BaseConnector):
    name = "arxiv"
    kind = "paper"

    def fetch(self, since: str | None, max_results: int = 50) -> Iterable[RawRecord]:
        params = {
            "search_query": QUERY,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        resp = http_get(ARXIV_API, params=params)
        # Atom XML parsing kept minimal for the skeleton; replace with feedparser.
        import xml.etree.ElementTree as ET

        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)
        for entry in root.findall("a:entry", ns):
            ext_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
            yield RawRecord(
                external_id=ext_id,
                payload={
                    "title": (entry.findtext("a:title", "", ns) or "").strip(),
                    "summary": (entry.findtext("a:summary", "", ns) or "").strip(),
                    "published": entry.findtext("a:published", "", ns),
                    "link": ext_id,
                },
            )

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        published = None
        if raw.payload.get("published"):
            try:
                published = datetime.fromisoformat(
                    raw.payload["published"].replace("Z", "+00:00")
                ).date()
            except ValueError:
                published = None
        return NormalizedDocument(
            doc_type="paper",
            external_id=raw.external_id,
            title=raw.payload.get("title", "Untitled"),
            abstract=raw.payload.get("summary"),
            url=raw.payload.get("link"),
            published_at=published or date.today(),
            metadata={"source": "arxiv"},
        )
