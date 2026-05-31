"""System health and activity read service."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import (
    HealthActivityOut,
    HealthComponentOut,
    HealthStatusOut,
    HealthStorageOut,
    SystemEventOut,
    SourceRecommendationOut,
)

_RECENT_WINDOW_HOURS = 24

_COMPONENTS = ("retrieval", "embedding", "processing", "source_discovery")


def _parse_payload(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else {"value": data}
        except Exception:
            return {"value": value}
    return {}



def get_health_status(db: Session) -> HealthStatusOut:
    recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=_RECENT_WINDOW_HOURS)

    storage_row = db.execute(
        text("SELECT pg_database_size(current_database()) AS db_bytes")
    ).mappings().first() or {"db_bytes": 0}
    db_gb = round(float(storage_row["db_bytes"] or 0) / (1024**3), 3)
    storage = HealthStorageOut(
        db_size_gb=db_gb,
        storage_limit_gb=100.0,
        within_budget=db_gb < 100.0,
    )

    component_rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (component)
                       component, status AS last_status, created_at AS last_event_at
                FROM system_event
                ORDER BY component, created_at DESC
            )
            SELECT se.component,
                   COUNT(*) FILTER (WHERE se.status = 'ok') AS ok_count,
                   COUNT(*) FILTER (WHERE se.status IN ('error', 'blocked')) AS error_count,
                   latest.last_event_at,
                   latest.last_status
            FROM system_event se
            JOIN latest ON latest.component = se.component
            GROUP BY se.component, latest.last_event_at, latest.last_status
            """
        )
    ).mappings().all()
    by_component = {r["component"]: r for r in component_rows}

    components = []
    for component in _COMPONENTS:
        row = by_component.get(component)
        components.append(
            HealthComponentOut(
                component=component,
                status=(row["last_status"] if row else "idle") or "idle",
                ok_count=int(row["ok_count"] or 0) if row else 0,
                error_count=int(row["error_count"] or 0) if row else 0,
                last_event_at=(row["last_event_at"] if row else None),
            )
        )

    recent_events_rows = db.execute(
        text(
            """
            SELECT component, phase, status, message, payload, created_at
            FROM system_event
            WHERE created_at >= :cutoff
            ORDER BY created_at DESC
            LIMIT 25
            """
        ),
        {"cutoff": recent_cutoff},
    ).mappings().all()
    recent_events = [
        SystemEventOut(
            component=r["component"],
            phase=r["phase"],
            status=r["status"],
            message=r["message"],
            payload=_parse_payload(r["payload"]),
            created_at=r["created_at"],
        )
        for r in recent_events_rows
    ]

    source_row = db.execute(
        text(
            """
            SELECT payload, created_at
            FROM system_event
            WHERE component = 'source_discovery'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    recommended_sources = []
    if source_row:
        payload = _parse_payload(source_row["payload"])
        for item in payload.get("recommended_sources", []) or []:
            recommended_sources.append(
                SourceRecommendationOut(
                    name=item.get("name", ""),
                    kind=item.get("kind", "news"),
                    url=item.get("url", ""),
                    score=float(item.get("score", 0) or 0),
                    reason=item.get("reason", ""),
                    matched_sectors=item.get("matched_sectors", []) or [],
                )
            )

    overall_status = "ok"
    if not storage.within_budget:
        overall_status = "degraded"
    if any(c.error_count > 0 for c in components):
        overall_status = "degraded"

    return HealthStatusOut(
        overall_status=overall_status,
        storage=storage,
        components=components,
        recent_activity=HealthActivityOut(events=recent_events),
        source_recommendations=recommended_sources,
    )
