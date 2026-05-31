"""arXiv connector (cond-mat / battery query).

M1 reference implementation of the Connector contract. Network calls are kept
behind `fetch` so the pipeline can be unit-tested with stubbed records.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from connectors.base import BaseConnector, NormalizedDocument, RawRecord, http_get

ARXIV_API = "https://export.arxiv.org/api/query"
# Broad battery value-chain coverage: chemistries, materials, manufacturing,
# recycling and grid storage (kept within cond-mat/physics relevance).
QUERY = (
    'all:"solid-state battery" OR all:"lithium-ion battery" OR all:"sodium-ion" '
    'OR all:"lithium metal anode" OR all:"silicon anode" OR all:"solid electrolyte" '
    'OR all:"lithium-sulfur" OR all:"flow battery" OR all:"battery recycling" '
    'OR all:"cathode material" OR all:"grid energy storage"'
)


class ArxivConnector(BaseConnector):
    name = "arxiv"
    kind = "paper"

    def fetch(self, since: str | None, max_results: int = 50) -> Iterable[RawRecord]:
        since_dt = None
        if since:
            try:
                since_dt = date.fromisoformat(since)
            except ValueError:
                since_dt = None
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
            published = None
            published_text = entry.findtext("a:published", "", ns)
            if published_text:
                try:
                    published = datetime.fromisoformat(published_text.replace("Z", "+00:00")).date()
                except ValueError:
                    published = None
            if since_dt and published and published <= since_dt:
                break
            ext_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
            authors = [
                (author.findtext("a:name", default="", namespaces=ns) or "").strip()
                for author in entry.findall("a:author", ns)
            ]
            yield RawRecord(
                external_id=ext_id,
                payload={
                    "title": (entry.findtext("a:title", "", ns) or "").strip(),
                    "summary": (entry.findtext("a:summary", "", ns) or "").strip(),
                    "published": entry.findtext("a:published", "", ns),
                    "link": ext_id,
                    "authors": [a for a in authors if a],
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
            metadata={"source": "arxiv", "authors": raw.payload.get("authors", [])},
        )
