from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import BottleneckItem
from app.services.analytics import list_bottlenecks

router = APIRouter()


@router.get("/bottlenecks", response_model=list[BottleneckItem])
def bottlenecks(limit: int = 20, db: Session = Depends(get_db)) -> list[BottleneckItem]:
    return list_bottlenecks(db, limit=limit)
