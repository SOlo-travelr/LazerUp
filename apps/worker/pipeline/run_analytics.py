"""Analytics orchestrator.

Runs the scoring engines in dependency order:
bottlenecks (buildability input) -> trends (momentum) -> white-space -> opportunities.
Each engine is independently transactional; a failure in one is reported but does
not abort the others.
"""

from __future__ import annotations

from analytics.bottlenecks import compute_bottlenecks
from analytics.opportunities import compute_opportunities
from analytics.trends import compute_trends
from analytics.whitespace import compute_white_spaces
from telemetry import log_event

_STAGES = (
    ("bottlenecks", compute_bottlenecks),
    ("trends", compute_trends),
    ("white_spaces", compute_white_spaces),
    ("opportunities", compute_opportunities),
)


def run_analytics() -> dict:
    log_event("processing", "analytics", "start", "analytics cycle starting")
    results: dict[str, dict] = {}
    for name, fn in _STAGES:
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001 - report per-stage, keep going
            results[name] = {"status": "error", "error": str(exc)}
    log_event("processing", "analytics", "ok", "analytics cycle complete", results)
    return results


if __name__ == "__main__":
    import json

    print(json.dumps(run_analytics(), indent=2))
