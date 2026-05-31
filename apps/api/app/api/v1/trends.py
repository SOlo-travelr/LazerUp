from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import TrendItem
from app.services.trends import list_trends

router = APIRouter()


@router.get("/trends", response_model=list[TrendItem])
def trends(window: str = "90d", limit: int = 20, db: Session = Depends(get_db)) -> list[TrendItem]:
    return list_trends(db, window=window, limit=limit)
