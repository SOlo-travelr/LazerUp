"""Trend read service.

Returns the latest persisted trend_score rows (computed by the worker analytics
engine, docs/ALGORITHMS.md §1) joined to their technology, ranked by composite.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import TechnologyOut, TrendComponents, TrendItem


def list_trends(db: Session, window: str = "90d", limit: int = 20) -> list[TrendItem]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (ts.technology_id)
                   t.id AS id, t.slug AS slug, t.name AS name, t.category AS category,
                   ts.composite_score AS composite_score,
                   ts.paper_growth AS paper_growth,
                   ts.patent_growth AS patent_growth,
                   ts.funding_momentum AS funding_momentum,
                   ts.grant_momentum AS grant_momentum
            FROM trend_score ts
            JOIN technology t ON t.id = ts.technology_id
            ORDER BY ts.technology_id, ts.window_end DESC
            """
        )
    ).mappings().all()

    ranked = sorted(rows, key=lambda r: r["composite_score"] or 0, reverse=True)[:limit]
    return [
        TrendItem(
            technology=TechnologyOut(
                id=r["id"], slug=r["slug"], name=r["name"], category=r["category"]
            ),
            composite_score=round(r["composite_score"] or 0, 6),
            components=TrendComponents(
                paper_growth=round(r["paper_growth"] or 0, 6),
                patent_growth=round(r["patent_growth"] or 0, 6),
                funding_momentum=round(r["funding_momentum"] or 0, 6),
                grant_momentum=round(r["grant_momentum"] or 0, 6),
            ),
            rank=i + 1,
        )
        for i, r in enumerate(ranked)
    ]
