"""Ingestion pipeline orchestration.

Runs registered connectors, normalizes records, applies in-batch dedup, and
persists to PostgreSQL with DB-level tier-1/2 dedup (external id + content hash).
Embedding generation runs as a separate stage (`pipeline.embed`).
"""

from __future__ import annotations

from connectors.base import Connector, NormalizedDocument
from connectors.grants.nsf import NSFConnector
from connectors.grants.sbir import SBIRConnector
from connectors.news.rss import RSSConnector
from connectors.papers.arxiv import ArxivConnector
from connectors.papers.semantic_scholar import SemanticScholarConnector
from connectors.patents.patentsview import PatentsViewConnector
from db import engine
from repository import get_source_id, upsert_document

# Connector registry. Each `name` must match a row in the `source` table (seed).
CONNECTORS: list[Connector] = [
    ArxivConnector(),
    SemanticScholarConnector(),
    PatentsViewConnector(),
    NSFConnector(),
    SBIRConnector(),
    RSSConnector(),
]


def collect(connector: Connector, since: str | None = None) -> list[NormalizedDocument]:
    """Fetch + parse + in-batch dedup (no DB)."""
    docs: list[NormalizedDocument] = []
    seen_hashes: set[str] = set()
    for raw in connector.fetch(since):
        doc = connector.parse(raw)
        if doc.content_hash in seen_hashes:
            continue
        seen_hashes.add(doc.content_hash)
        docs.append(doc)
    return docs


def run_all_connectors() -> dict:
    summary: dict[str, dict] = {}
    for connector in CONNECTORS:
        try:
            with engine.begin() as conn:
                source_id = get_source_id(conn, connector.name)
                if source_id is None:
                    summary[connector.name] = {"error": "source_not_registered"}
                    continue

                inserted = duplicates = 0
                for doc in collect(connector):
                    _id, was_new = upsert_document(conn, source_id, doc)
                    if was_new:
                        inserted += 1
                    else:
                        duplicates += 1
                summary[connector.name] = {"inserted": inserted, "duplicates": duplicates}
        except Exception as exc:  # keep one bad source from blocking others
            summary[connector.name] = {"error": str(exc)}
            print(f'{{"level":"ERROR","connector":"{connector.name}","error":"{exc}"}}')

    return {"status": "ok", "ingested": summary}
