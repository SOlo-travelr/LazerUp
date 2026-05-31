from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import FounderFitItem, FounderProfileOut, FounderProfileRequest
from app.services.founder_fit import create_profile, score_fit

router = APIRouter()


@router.post("/founder/profile", response_model=FounderProfileOut)
def create_founder_profile(
    req: FounderProfileRequest, db: Session = Depends(get_db)
) -> FounderProfileOut:
    return create_profile(db, req)


@router.get("/founder/{profile_id}/fit", response_model=list[FounderFitItem])
def founder_fit(
    profile_id: UUID, limit: int = 20, db: Session = Depends(get_db)
) -> list[FounderFitItem]:
    results = score_fit(db, profile_id, limit=limit)
    if not results:
        raise HTTPException(status_code=404, detail="Profile not found or no opportunities scored")
    return results
