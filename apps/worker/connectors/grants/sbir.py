"""SBIR/STTR awards connector (sbir.gov API)."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import httpx

from connectors.base import BaseConnector, NormalizedDocument, RawRecord

SBIR_API = "https://api.www.sbir.gov/public/api/awards"
KEYWORD = "battery"


class SBIRConnector(BaseConnector):
    name = "sbir_sttr"
    kind = "grant"

    def fetch(self, since: str | None, rows: int = 25) -> Iterable[RawRecord]:
        resp = httpx.get(
            SBIR_API,
            params={"keyword": KEYWORD, "rows": rows, "format": "json"},
            timeout=30,
        )
        resp.raise_for_status()
        for award in resp.json() or []:
            ext_id = str(award.get("contract") or award.get("award_link") or award.get("firm", ""))
            yield RawRecord(external_id=ext_id, payload=award)

    def parse(self, raw: RawRecord) -> NormalizedDocument:
        a = raw.payload
        year = a.get("award_year")
        published = date(int(year), 1, 1) if year else date.today()
        return NormalizedDocument(
            doc_type="grant",
            external_id=raw.external_id,
            title=a.get("award_title") or a.get("firm") or "SBIR/STTR award",
            abstract=a.get("abstract"),
            url=a.get("award_link"),
            published_at=published,
            metadata={
                "source": "sbir_sttr",
                "program": a.get("program"),
                "agency": a.get("agency"),
                "amount_usd": a.get("award_amount"),
                "awardee": a.get("firm"),
            },
        )
