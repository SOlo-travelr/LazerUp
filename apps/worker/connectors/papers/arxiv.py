"""arXiv connector (cond-mat / battery query).

M1 reference implementation of the Connector contract. Network calls are kept
behind `fetch` so the pipeline can be unit-tested with stubbed records.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from typing import Iterable

from connectors.base import BaseConnector, NormalizedDocument, RawRecord, http_get

ARXIV_API = "https://export.arxiv.org/api/query"
# Broad battery value-chain coverage: chemistries, materials, manufacturing,
# recycling and grid storage (kept within cond-mat/physics relevance).
QUERY_SLICES = [
    'all:"solid-state battery" OR all:"solid electrolyte" OR all:"lithium metal anode"',
    'all:"lithium-ion battery" OR all:"sodium-ion" OR all:"lithium-sulfur"',
    'all:"flow battery" OR all:"grid energy storage" OR all:"stationary storage"',
    'all:"battery recycling" OR all:"cell manufacturing" OR all:"separator"',
    'all:"cathode material" OR all:"anode material" OR all:"electrolyte additive"',
    'all:"battery management system" OR all:"fast charging" OR all:"silicon anode"',
]


class ArxivConnector(BaseConnector):
    name = "arxiv"
    kind = "paper"

    def fetch(
        self,
        since: str | None,
        max_results: int = 100,
        max_pages: int = 1,
    ) -> Iterable[RawRecord]:
        since_dt = None
        if since:
            try:
                since_dt = date.fromisoformat(since)
            except ValueError:
                since_dt = None
        # Atom XML parsing kept minimal for the skeleton; replace with feedparser.
        import xml.etree.ElementTree as ET

        ns = {"a": "http://www.w3.org/2005/Atom"}
        seen_ids: set[str] = set()
        for query in QUERY_SLICES:
            for page in range(max_pages):
                params = {
                    "search_query": query,
                    "start": page * max_results,
                    "max_results": max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
                resp = http_get(ARXIV_API, params=params, timeout=90)
                root = ET.fromstring(resp.text)
                entries = root.findall("a:entry", ns)
                if not entries:
                    break
                seen_any = False
                for entry in entries:
                    published = None
                    published_text = entry.findtext("a:published", "", ns)
                    if published_text:
                        try:
                            published = datetime.fromisoformat(published_text.replace("Z", "+00:00")).date()
                        except ValueError:
                            published = None
                    if since_dt and published and published <= since_dt:
                        continue
                    ext_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
                    if not ext_id or ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)
                    authors = [
                        (author.findtext("a:name", default="", namespaces=ns) or "").strip()
                        for author in entry.findall("a:author", ns)
                    ]
                    seen_any = True
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
                if not seen_any:
                    break
                time.sleep(0.5)

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
