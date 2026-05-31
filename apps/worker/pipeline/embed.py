"""Embedding pipeline.

Selects documents that do not yet have an embedding, batches them through the
configured provider, and stores vectors in `document_embedding`. Idempotent:
already-embedded documents are skipped, so re-runs are cheap.
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import text

from db import engine
from embeddings import get_embedding_provider, to_pgvector
from telemetry import log_event, storage_snapshot

_SELECT_MISSING = text(
    """
    SELECT d.id,
           coalesce(d.title, '') || '. ' || coalesce(d.abstract, '') AS content
    FROM document d
    LEFT JOIN document_embedding de ON de.document_id = d.id
    WHERE de.document_id IS NULL
    ORDER BY d.created_at DESC
    LIMIT :batch
    """
)

_INSERT_EMBEDDING = text(
    """
    INSERT INTO document_embedding (document_id, model, embedding)
    VALUES (:document_id, :model, CAST(:embedding AS vector))
    ON CONFLICT (document_id) DO NOTHING
    """
)


def embed_new_documents(batch_size: int = 256) -> dict:
    snapshot = storage_snapshot()
    if not snapshot.within_budget:
        payload = asdict(snapshot)
        log_event("embedding", "budget", "blocked", "storage budget exceeded", payload)
        return {"status": "blocked", "reason": "storage_budget_exceeded", "storage": payload}

    provider = get_embedding_provider()
    if not provider.enabled:
        log_event("embedding", "skip", "skipped", "no embedding provider configured")
        return {"status": "skipped", "reason": "no_embedding_provider"}

    embedded = 0
    with engine.begin() as conn:
        rows = conn.execute(_SELECT_MISSING, {"batch": batch_size}).mappings().all()
        if not rows:
            result = {"status": "ok", "embedded": 0}
            log_event("embedding", "finish", "ok", "no pending documents", result)
            return result

        vectors = provider.embed([r["content"] for r in rows])
        for row, vec in zip(rows, vectors, strict=True):
            conn.execute(
                _INSERT_EMBEDDING,
                {
                    "document_id": str(row["id"]),
                    "model": provider.model,
                    "embedding": to_pgvector(vec),
                },
            )
            embedded += 1

    result = {"status": "ok", "embedded": embedded}
    log_event("embedding", "finish", "ok", "embedding cycle complete", result)
    return result
