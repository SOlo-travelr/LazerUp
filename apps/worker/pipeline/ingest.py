"""Ingestion pipeline orchestration.

Runs registered connectors, normalizes records, and applies tier-1/2 dedup
(exact id + content hash). Embedding + LLM extraction (tier-3 fuzzy dedup) are
layered on in milestone M4.
"""

from __future__ import annotations

from connectors.base import Connector, NormalizedDocument
from connectors.papers.arxiv import ArxivConnector

# Connector registry. Extend as sources are implemented.
CONNECTORS: list[Connector] = [ArxivConnector()]


def collect(connector: Connector, since: str | None = None) -> list[NormalizedDocument]:
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
    summary: dict[str, int] = {}
    for connector in CONNECTORS:
        try:
            docs = collect(connector)
            summary[connector.name] = len(docs)
            # TODO(M4): persist via repository with DB-level dedup + S3 archive.
        except Exception as exc:  # keep one bad source from blocking others
            summary[connector.name] = -1
            print(f'{{"level":"ERROR","connector":"{connector.name}","error":"{exc}"}}')
    return {"status": "ok", "ingested": summary}
