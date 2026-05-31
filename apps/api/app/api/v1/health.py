from fastapi import APIRouter

from app.core.config import settings
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/ping", response_model=HealthResponse)
def ping() -> HealthResponse:
    return HealthResponse(status="ok", env=settings.env, version="0.1.0")
