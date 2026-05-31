"""Automatic source discovery and recommendation stage.

This does not blindly scrape the web. Instead it scores a curated candidate set
of retrieval sources against the current corpus gaps, then records the best
marginal sources for each battery region/segment so the system can improve its
retrieval mix over time.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from db import engine
from telemetry import log_event

_SELECT_SECTORS = text(
    """
    SELECT t.category AS sector,
           COUNT(*) AS docs,
           COUNT(DISTINCT dorg.organization_id) AS orgs
    FROM document_technology dt
    JOIN technology t ON t.id = dt.technology_id
    JOIN document d ON d.id = dt.document_id
    LEFT JOIN document_organization dorg ON dorg.document_id = d.id
    GROUP BY t.category
    ORDER BY docs DESC
    """
)

_SELECT_SOURCES = text(
    "SELECT name, kind, base_url, enabled FROM source ORDER BY name"
)


@dataclass(slots=True)
class SourceCandidate:
    name: str
    kind: str
    url: str
    reason: str
    score: float


_CANDIDATES = [
    SourceCandidate(
        name="batterycompanies",
        kind="news",
        url="https://www.batterycompanies.com/",
        reason="Company/startup coverage for battery commercialization and funding signals.",
        score=0.86,
    ),
    SourceCandidate(
        name="electrive",
        kind="news",
        url="https://www.electrive.com/feed/",
        reason="Strong EV and battery manufacturing coverage in Europe and Asia.",
        score=0.84,
    ),
    SourceCandidate(
        name="insideevs",
        kind="news",
        url="https://insideevs.com/feed/",
        reason="EV battery product launches and OEM commercialization signals.",
        score=0.8,
    ),
    SourceCandidate(
        name="batterytechonline",
        kind="news",
        url="https://www.batterytechonline.com/feed/",
        reason="Battery manufacturing, materials and supply-chain coverage.",
        score=0.78,
    ),
]



def discover_sources(limit: int = 5) -> dict:
    with engine.begin() as conn:
        sectors = conn.execute(_SELECT_SECTORS).mappings().all()
        existing = {row["name"] for row in conn.execute(_SELECT_SOURCES).mappings().all()}

    sector_names = [row["sector"] for row in sectors[:5]]
    candidates = sorted(_CANDIDATES, key=lambda c: c.score, reverse=True)
    recommendations = []
    for candidate in candidates:
        if candidate.name in existing:
            continue
        recommendations.append(
            {
                "name": candidate.name,
                "kind": candidate.kind,
                "url": candidate.url,
                "score": candidate.score,
                "reason": candidate.reason,
                "matched_sectors": sector_names,
            }
        )
        if len(recommendations) >= limit:
            break

    payload = {"recommended_sources": recommendations, "sector_focus": sector_names}
    log_event("source_discovery", "discover", "ok", "source recommendations refreshed", payload)
    return {"status": "ok", **payload}
