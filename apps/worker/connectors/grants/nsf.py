"""NSF Awards API connector."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

import httpx

from connectors.base import BaseConnector, NormalizedDocument, RawRecord

NSF_API = "https://api.nsf.gov/services/v1/awards.json"
FIELDS = "id,title,abstractText,date,fundsObligatedAmt,awardeeName"
KEYWORD = "battery"


class NSFConnector(BaseConnector):
    name = "nsf"
    kind = "grant"

    def fetch(self, since: str | None, limit: int = 25) -> Iterable[RawRecord]:
        resp = httpx.get(
            NSF_API,
            params={"keyword": KEYWORD, "printFields": FIELDS, "rpp": limit},
            timeout=30,
        )
        resp.raise_for_status()
        for award in resp.json().get("response", {}).get("award", []) or []:
            yield RawRecord(external_id=str(award.get("id", "")), payload=award)

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        a = raw.payload
        published = None
        if a.get("date"):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    published = datetime.strptime(a["date"], fmt).date()
                    break
                except ValueError:
                    continue
        return NormalizedDocument(
            doc_type="grant",
            external_id=raw.external_id,
            title=a.get("title") or "NSF award",
            abstract=a.get("abstractText"),
            url=f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={raw.external_id}",
            published_at=published or date.today(),
            metadata={
                "source": "nsf",
                "program": "NSF",
                "amount_usd": a.get("fundsObligatedAmt"),
                "awardee": a.get("awardeeName"),
            },
        )
