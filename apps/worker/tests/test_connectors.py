"""Pure (network-free) tests for connector parsing logic."""

from connectors.base import RawRecord
from connectors.grants.nsf import NSFConnector
from connectors.grants.sbir import SBIRConnector
from connectors.news.rss import RSSConnector
from connectors.papers.semantic_scholar import SemanticScholarConnector
from connectors.patents.patentsview import PatentsViewConnector


def test_semantic_scholar_parse() -> None:
    raw = RawRecord(
        external_id="10.1000/x",
        payload={
            "title": "Sulfide electrolytes",
            "abstract": "An abstract.",
            "year": 2025,
            "publicationDate": "2025-03-01",
            "url": "https://example.org",
        },
    )
    doc = SemanticScholarConnector().parse(raw)
    assert doc.doc_type == "paper"
    assert doc.published_at.isoformat() == "2025-03-01"
    assert len(doc.content_hash) == 64


def test_patentsview_parse_builds_google_url() -> None:
    raw = RawRecord(
        external_id="11223344",
        payload={
            "patent_title": "Solid electrolyte",
            "patent_abstract": "Claims...",
            "patent_date": "2024-06-15",
        },
    )
    doc = PatentsViewConnector().parse(raw)
    assert doc.doc_type == "patent"
    assert doc.url.endswith("US11223344")


def test_nsf_parse_handles_us_date() -> None:
    raw = RawRecord(
        external_id="2099001",
        payload={"title": "Battery research", "abstractText": "x", "date": "06/15/2024"},
    )
    doc = NSFConnector().parse(raw)
    assert doc.doc_type == "grant"
    assert doc.published_at.isoformat() == "2024-06-15"


def test_sbir_parse() -> None:
    raw = RawRecord(
        external_id="C-1",
        payload={"award_title": "Battery startup", "abstract": "x", "award_year": 2023},
    )
    doc = SBIRConnector().parse(raw)
    assert doc.doc_type == "grant"
    assert doc.published_at.year == 2023


def test_rss_parse() -> None:
    raw = RawRecord(
        external_id="https://news/1",
        payload={
            "title": "New gigafactory",
            "description": "summary",
            "link": "https://news/1",
            "pubDate": "Tue, 15 Apr 2025 10:00:00 GMT",
        },
    )
    doc = RSSConnector().parse(raw)
    assert doc.doc_type == "news"
    assert doc.published_at.isoformat() == "2025-04-15"
