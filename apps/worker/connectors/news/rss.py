"""Generic RSS news connector for battery-industry feeds."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Iterable

import httpx

from connectors.base import BaseConnector, NormalizedDocument, RawRecord

# Default battery-industry feeds spanning research, manufacturing, supply chain,
# mining/materials and grid storage; extend via the source registry config.
DEFAULT_FEEDS = [
    "https://www.energy-storage.news/feed/",
    "https://electrek.co/feed/",
    "https://www.mining.com/feed/",
    "https://thedriven.io/feed/",
    "https://www.pv-magazine.com/feed/",
]


class RSSConnector(BaseConnector):
    name = "industry_rss"
    kind = "news"

    def __init__(self, feeds: list[str] | None = None) -> None:
        self.feeds = feeds or DEFAULT_FEEDS

    def fetch(self, since: str | None) -> Iterable[RawRecord]:
        for feed_url in self.feeds:
            try:
                resp = httpx.get(feed_url, timeout=30, follow_redirects=True)
                resp.raise_for_status()
            except httpx.HTTPError:
                continue
            root = ET.fromstring(resp.text)
            for item in root.iter("item"):
                link = (item.findtext("link") or "").strip()
                yield RawRecord(
                    external_id=link,
                    payload={
                        "title": (item.findtext("title") or "").strip(),
                        "description": (item.findtext("description") or "").strip(),
                        "link": link,
                        "pubDate": item.findtext("pubDate"),
                    },
                )

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        published: date | None = None
        if raw.payload.get("pubDate"):
            try:
                dt: datetime = parsedate_to_datetime(raw.payload["pubDate"])
                published = dt.date()
            except (TypeError, ValueError):
                published = None
        return NormalizedDocument(
            doc_type="news",
            external_id=raw.external_id,
            title=raw.payload.get("title") or "Untitled",
            abstract=raw.payload.get("description"),
            url=raw.payload.get("link"),
            published_at=published or date.today(),
            metadata={"source": "industry_rss"},
        )
