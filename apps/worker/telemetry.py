"""Worker telemetry helpers.

Records system events for retrieval, embedding, processing, and source discovery.
Also exposes a lightweight storage-budget check used to stop growth before the
pipeline exceeds the configured quota.
"""

from __future__ import annotations

import os
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from db import engine

MAX_STORAGE_GB = float(os.getenv("MAX_STORAGE_GB", "100"))
WORKSPACE_PATH = Path(os.getenv("WORKSPACE_PATH", "/app"))
CACHE_PATH = Path(os.getenv("CONNECTOR_CACHE_DIR", "/tmp/lazerup_connector_cache"))

_INSERT_EVENT = text(
    """
    INSERT INTO system_event (component, phase, status, message, payload)
    VALUES (:component, :phase, :status, :message, CAST(:payload AS jsonb))
    """
)


@dataclass(slots=True)
class StorageSnapshot:
    used_gb: float
    free_gb: float
    limit_gb: float
    within_budget: bool



def log_event(component: str, phase: str, status: str, message: str = "", payload: dict | None = None) -> None:
    with engine.begin() as conn:
        conn.execute(
            _INSERT_EVENT,
            {
                "component": component,
                "phase": phase,
                "status": status,
                "message": message,
                "payload": json.dumps(payload or {}),
            },
        )



def _dir_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    for entry in path.rglob("*"):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                continue
    return total



def storage_snapshot() -> StorageSnapshot:
    usage = shutil.disk_usage(WORKSPACE_PATH)
    cache_bytes = _dir_size_bytes(CACHE_PATH)
    # Approximate the live store size by counting local cache plus the writable
    # workspace mount; the database volume is tracked separately in health UI.
    used_gb = (usage.used + cache_bytes) / (1024**3)
    free_gb = usage.free / (1024**3)
    within_budget = used_gb < MAX_STORAGE_GB and free_gb > 1.0
    return StorageSnapshot(
        used_gb=round(used_gb, 3),
        free_gb=round(free_gb, 3),
        limit_gb=MAX_STORAGE_GB,
        within_budget=within_budget,
    )



def db_size_gb() -> float:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT pg_database_size(current_database()) AS size")).first()
    size = float(row[0] or 0) if row else 0.0
    return round(size / (1024**3), 3)
