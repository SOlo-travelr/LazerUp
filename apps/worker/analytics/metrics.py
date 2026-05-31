"""Shared per-technology metrics used by the white-space and opportunity engines.

One pass over the store produces the raw counts each engine normalizes. Reading
the latest ``trend_score`` row supplies momentum (M) so trends must run first.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Connection

RECENT_DAYS = 90


def technology_names(conn: Connection) -> dict[str, dict]:
    rows = conn.execute(
        text("SELECT id, slug, name, category FROM technology")
    ).mappings().all()
    return {
        str(r["id"]): {"slug": r["slug"], "name": r["name"], "category": r["category"]}
        for r in rows
    }


def corpus_metrics(conn: Connection) -> dict[str, dict]:
    """Per-technology corpus size, recency window and source diversity."""
    recent_start = date.today() - timedelta(days=RECENT_DAYS)
    rows = conn.execute(
        text(
            """
            SELECT dt.technology_id AS tech,
                   COUNT(*) AS ndocs,
                   COUNT(*) FILTER (WHERE d.published_at >= :recent_start) AS recent_docs,
                   COUNT(DISTINCT s.kind) AS source_diversity,
                   COUNT(*) FILTER (WHERE d.doc_type = 'paper'
                                    AND d.published_at >= :recent_start) AS paper_recent,
                   COUNT(*) FILTER (WHERE d.doc_type = 'patent'
                                    AND d.published_at >= :recent_start) AS patent_recent
            FROM document_technology dt
            JOIN document d ON d.id = dt.document_id
            JOIN source s ON s.id = d.source_id
            GROUP BY dt.technology_id
            """
        ),
        {"recent_start": recent_start},
    ).mappings().all()
    return {
        str(r["tech"]): {
            "ndocs": int(r["ndocs"]),
            "recent_docs": int(r["recent_docs"]),
            "source_diversity": int(r["source_diversity"]),
            "paper_recent": int(r["paper_recent"]),
            "patent_recent": int(r["patent_recent"]),
        }
        for r in rows
    }


def startup_density(conn: Connection) -> dict[str, int]:
    """Distinct organizations linked to each technology's documents."""
    rows = conn.execute(
        text(
            """
            SELECT dt.technology_id AS tech, COUNT(DISTINCT dorg.organization_id) AS orgs
            FROM document_technology dt
            JOIN document_organization dorg ON dorg.document_id = dt.document_id
            GROUP BY dt.technology_id
            """
        )
    ).mappings().all()
    return {str(r["tech"]): int(r["orgs"]) for r in rows}


def funding_recent(conn: Connection) -> dict[str, float]:
    """Recent-window funding USD (grants + rounds) per technology."""
    recent_start = date.today() - timedelta(days=RECENT_DAYS)
    rows = conn.execute(
        text(
            """
            SELECT tech, SUM(amount) AS total FROM (
                SELECT dt.technology_id AS tech, COALESCE(ga.amount_usd, 0) AS amount
                FROM grant_award ga
                JOIN document_technology dt ON dt.document_id = ga.document_id
                WHERE ga.start_date >= :recent_start
                UNION ALL
                SELECT dt.technology_id AS tech, COALESCE(fe.amount_usd, 0) AS amount
                FROM funding_event fe
                JOIN document_technology dt ON dt.document_id = fe.document_id
                WHERE fe.announced_at >= :recent_start
            ) x
            GROUP BY tech
            """
        ),
        {"recent_start": recent_start},
    ).mappings().all()
    return {str(r["tech"]): float(r["total"] or 0) for r in rows}


def latest_trend(conn: Connection) -> dict[str, dict]:
    """Most recent trend_score row per technology (momentum source)."""
    rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (technology_id)
                   technology_id, composite_score, paper_growth, patent_growth,
                   funding_momentum, grant_momentum
            FROM trend_score
            ORDER BY technology_id, window_end DESC
            """
        )
    ).mappings().all()
    return {
        str(r["technology_id"]): {
            "composite": float(r["composite_score"] or 0),
            "paper_growth": float(r["paper_growth"] or 0),
            "patent_growth": float(r["patent_growth"] or 0),
            "funding_momentum": float(r["funding_momentum"] or 0),
            "grant_momentum": float(r["grant_momentum"] or 0),
        }
        for r in rows
    }


def max_bottleneck_severity(conn: Connection) -> dict[str, float]:
    rows = conn.execute(
        text(
            """
            SELECT technology_id, MAX(severity) AS sev
            FROM bottleneck
            GROUP BY technology_id
            """
        )
    ).mappings().all()
    return {str(r["technology_id"]): float(r["sev"] or 0) for r in rows}
