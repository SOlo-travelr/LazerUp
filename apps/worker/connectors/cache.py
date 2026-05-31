"""Small JSON cache for connector fallback payloads.

Used when upstream APIs rate-limit or timeout. On successful responses we persist
page payloads; on errors connectors can read latest cached pages to keep ingest
productive instead of returning zero records.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_CACHE_DIR = Path(os.getenv("CONNECTOR_CACHE_DIR", "/tmp/lazerup_connector_cache"))


def _path(key: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in key)
    return _CACHE_DIR / f"{safe}.json"


def write_cache(key: str, payload: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _path(key).write_text(json.dumps(payload), encoding="utf-8")


def read_cache(key: str) -> dict | None:
    path = _path(key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
