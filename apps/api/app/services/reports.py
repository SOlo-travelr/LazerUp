"""Weekly report read service.

Serves the latest weekly_report row (built by the worker, docs/ALGORITHMS.md §6).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import WeeklyReportOut


def get_latest_report(db: Session) -> WeeklyReportOut | None:
    row = db.execute(
        text(
            """
            SELECT week_start, payload, generated_at
            FROM weekly_report
            ORDER BY week_start DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    if not row:
        return None
    return WeeklyReportOut(
        week_start=row["week_start"],
        payload=row["payload"] or {},
        generated_at=row["generated_at"],
    )

