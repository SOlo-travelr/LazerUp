from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import OpportunityItem
from app.services.analytics import list_opportunities

router = APIRouter()


@router.get("/opportunities", response_model=list[OpportunityItem])
def opportunities(limit: int = 20, db: Session = Depends(get_db)) -> list[OpportunityItem]:
    return list_opportunities(db, limit=limit)
