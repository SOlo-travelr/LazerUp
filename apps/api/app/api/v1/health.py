from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas import HealthResponse, HealthStatusOut
from app.services.health import get_health_status

router = APIRouter()


@router.get("/ping", response_model=HealthResponse)
def ping() -> HealthResponse:
    return HealthResponse(status="ok", env=settings.env, version="0.1.0")


@router.get("/health/status", response_model=HealthStatusOut)
def status(db: Session = Depends(get_db)) -> HealthStatusOut:
    return get_health_status(db)
