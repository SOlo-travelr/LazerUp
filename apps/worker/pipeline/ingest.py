"""Ingestion pipeline orchestration.

Runs registered connectors, normalizes records, applies in-batch dedup, and
persists to PostgreSQL with DB-level tier-1/2 dedup (external id + content hash).
Embedding generation runs as a separate stage (`pipeline.embed`).
"""

from __future__ import annotations

from dataclasses import asdict

from connectors.base import Connector, NormalizedDocument
from connectors.grants.nsf import NSFConnector
from connectors.grants.sbir import SBIRConnector
from connectors.news.company_rss import CompanyRSSConnector
from connectors.news.rss import RSSConnector
from connectors.papers.arxiv import ArxivConnector
from connectors.papers.semantic_scholar import SemanticScholarConnector
from connectors.patents.patentsview import PatentsViewConnector
from db import engine
from repository import get_source_id, upsert_document
from telemetry import log_event, storage_snapshot

# Connector registry. Each `name` must match a row in the `source` table (seed).
CONNECTORS: list[Connector] = [
    ArxivConnector(),
    SemanticScholarConnector(),
    PatentsViewConnector(),
    NSFConnector(),
    SBIRConnector(),
    CompanyRSSConnector(),
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
    snapshot = storage_snapshot()
    if not snapshot.within_budget:
        payload = asdict(snapshot)
        log_event("retrieval", "budget", "blocked", "storage budget exceeded", payload)
        return {"status": "blocked", "reason": "storage_budget_exceeded", "storage": payload}

    log_event("retrieval", "start", "ok", "starting retrieval cycle", asdict(snapshot))
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

    result = {"status": "ok", "ingested": summary}
    log_event("retrieval", "finish", "ok", "retrieval cycle complete", result)
    return result
