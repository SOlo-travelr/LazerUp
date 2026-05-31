from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import WhiteSpaceItem
from app.services.analytics import list_white_spaces

router = APIRouter()


@router.get("/white-spaces", response_model=list[WhiteSpaceItem])
def white_spaces(limit: int = 20, db: Session = Depends(get_db)) -> list[WhiteSpaceItem]:
    return list_white_spaces(db, limit=limit)
