from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import WeeklyReportOut
from app.services.reports import get_latest_report

router = APIRouter()


@router.get("/reports/latest", response_model=WeeklyReportOut)
def latest_report(db: Session = Depends(get_db)) -> WeeklyReportOut:
    report = get_latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No weekly report generated yet")
    return report
