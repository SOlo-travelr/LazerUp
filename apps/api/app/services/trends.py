"""Trend service.

M1 placeholder: returns ranked technologies with zeroed scores until the trend
engine (docs/ALGORITHMS.md §1) is implemented in milestone M6.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Technology
from app.schemas import TechnologyOut, TrendComponents, TrendItem


def list_trends(db: Session, window: str = "90d", limit: int = 20) -> list[TrendItem]:
    techs = db.execute(select(Technology).limit(limit)).scalars().all()
    return [
        TrendItem(
            technology=TechnologyOut.model_validate(t),
            composite_score=0.0,
            components=TrendComponents(
                paper_growth=0.0, patent_growth=0.0, funding_momentum=0.0
            ),
            rank=i + 1,
        )
        for i, t in enumerate(techs)
    ]
