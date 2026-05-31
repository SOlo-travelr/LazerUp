from datetime import date

from connectors.base import NormalizedDocument, RawRecord
from connectors.papers.arxiv import ArxivConnector
from pipeline.ingest import collect


def test_content_hash_is_stable() -> None:
    doc = NormalizedDocument(
        doc_type="paper",
        external_id="x1",
        title="Solid-State Battery",
        abstract="An abstract.",
        published_at=date(2026, 1, 1),
    )
    assert doc.content_hash == doc.content_hash
    assert len(doc.content_hash) == 64


def test_collect_dedupes_identical_records() -> None:
    connector = ArxivConnector()
    raw = RawRecord(
        external_id="abc",
        payload={"title": "Same", "summary": "Same", "published": "2026-01-01T00:00:00Z"},
    )

    connector.fetch = lambda since=None: [raw, raw]  # type: ignore[method-assign]
    docs = collect(connector)
    assert len(docs) == 1
