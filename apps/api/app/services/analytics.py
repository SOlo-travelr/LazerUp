"""Read services for the derived analytics tables.

Opportunities, white spaces and bottlenecks are computed and persisted by the
worker engines; the API simply serves the latest rows.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import BottleneckItem, OpportunityItem, WhiteSpaceItem


def list_opportunities(db: Session, limit: int = 20) -> list[OpportunityItem]:
    rows = db.execute(
        text(
            """
            SELECT o.id, o.title, o.thesis, o.market, o.technical_risk,
                   o.commercial_potential, o.score, o.confidence, o.evidence,
                   t.name AS technology
            FROM opportunity o
            LEFT JOIN technology t ON t.id = o.technology_id
            WHERE o.status = 'active'
            ORDER BY o.score DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    return [
        OpportunityItem(
            id=r["id"],
            title=r["title"],
            thesis=r["thesis"],
            technology=r["technology"],
            market=r["market"],
            technical_risk=r["technical_risk"],
            commercial_potential=r["commercial_potential"],
            score=round(r["score"] or 0, 6),
            confidence=round(r["confidence"] or 0, 6),
            evidence=r["evidence"] or {},
        )
        for r in rows
    ]


def list_white_spaces(db: Session, limit: int = 20) -> list[WhiteSpaceItem]:
    rows = db.execute(
        text(
            """
            SELECT w.id, w.research_activity, w.funding_present, w.startup_density,
                   w.whitespace_score, w.rationale, t.name AS technology
            FROM white_space w
            LEFT JOIN technology t ON t.id = w.technology_id
            ORDER BY w.whitespace_score DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    return [
        WhiteSpaceItem(
            id=r["id"],
            technology=r["technology"],
            research_activity=round(r["research_activity"] or 0, 6),
            funding_present=round(r["funding_present"] or 0, 6),
            startup_density=round(r["startup_density"] or 0, 6),
            whitespace_score=round(r["whitespace_score"] or 0, 6),
            rationale=r["rationale"],
        )
        for r in rows
    ]


def list_bottlenecks(db: Session, limit: int = 20) -> list[BottleneckItem]:
    rows = db.execute(
        text(
            """
            SELECT b.id, b.problem_statement, b.frequency, b.severity,
                   t.name AS technology
            FROM bottleneck b
            LEFT JOIN technology t ON t.id = b.technology_id
            ORDER BY b.severity DESC NULLS LAST
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    return [
        BottleneckItem(
            id=r["id"],
            technology=r["technology"],
            problem_statement=r["problem_statement"],
            frequency=int(r["frequency"] or 0),
            severity=round(r["severity"] or 0, 6),
        )
        for r in rows
    ]
