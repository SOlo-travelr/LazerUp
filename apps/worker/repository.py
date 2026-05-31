"""Document persistence with tier-1/2 deduplication.

Tier-1 (exact id) and tier-2 (content hash) dedup are enforced by the database
unique constraints; `ON CONFLICT DO NOTHING` makes upserts idempotent so a
re-run never creates duplicates. Tier-3 (fuzzy/semantic) dedup lands later.
"""

from __future__ import annotations

import json

from sqlalchemy import Connection, text

from connectors.base import NormalizedDocument

_GET_SOURCE_ID = text("SELECT id FROM source WHERE name = :name")

_INSERT_DOC = text(
    """
    INSERT INTO document
        (source_id, doc_type, external_id, content_hash,
         title, abstract, url, published_at, metadata)
    VALUES
        (:source_id, :doc_type, :external_id, :content_hash,
         :title, :abstract, :url, :published_at, CAST(:metadata AS jsonb))
    ON CONFLICT DO NOTHING
    RETURNING id
    """
)


def get_source_id(conn: Connection, name: str) -> str | None:
    row = conn.execute(_GET_SOURCE_ID, {"name": name}).first()
    return str(row[0]) if row else None


def upsert_document(
    conn: Connection, source_id: str, doc: NormalizedDocument
) -> tuple[str | None, bool]:
    """Insert a document if new. Returns (document_id, was_inserted)."""
    row = conn.execute(
        _INSERT_DOC,
        {
            "source_id": source_id,
            "doc_type": doc.doc_type,
            "external_id": doc.external_id,
            "content_hash": doc.content_hash,
            "title": doc.title,
            "abstract": doc.abstract,
            "url": doc.url,
            "published_at": doc.published_at,
            "metadata": json.dumps(doc.metadata or {}),
        },
    ).first()
    if row is None:
        return None, False
    return str(row[0]), True
