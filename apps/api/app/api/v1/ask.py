from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import AskRequest, AskResponse
from app.services.rag import ask as ask_service

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    return ask_service(db, req)
