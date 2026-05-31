from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import LinkageInsightsOut, TechnologyLinkageOut
from app.services.linkage import get_linkage_insights, get_technology_linkage

router = APIRouter()


@router.get("/linkage/{technology_slug}", response_model=TechnologyLinkageOut)
def technology_linkage(
    technology_slug: str,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> TechnologyLinkageOut:
    payload = get_technology_linkage(db, slug=technology_slug, limit=limit)
    if payload is None:
        raise HTTPException(status_code=404, detail="technology_not_found")
    return payload


@router.get("/linkage-insights", response_model=LinkageInsightsOut)
def linkage_insights(limit: int = 10, db: Session = Depends(get_db)) -> LinkageInsightsOut:
    return get_linkage_insights(db, limit=limit)
