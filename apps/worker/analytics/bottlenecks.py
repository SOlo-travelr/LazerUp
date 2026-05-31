"""Technical bottleneck finder (docs/ALGORITHMS.md §4).

MVP extraction is deterministic and LLM-free: it scans abstracts for unsolved-
problem cue phrases, clusters the matches per (technology, cue) and scores each
cluster by frequency x recency x breadth. Persists to ``bottleneck``.

When the LLM provider is configured the extraction can later be upgraded to a
function-call; the scoring stays formula-driven either way.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy import text

from analytics.mathx import clamp, minmax
from db import engine

LOOKBACK_DAYS = 365
MIN_FREQUENCY = 2  # ignore one-off mentions
MAX_SUPPORTING = 25

# Cue phrases that flag an open/unsolved challenge in scientific abstracts.
_CUES: dict[str, str] = {
    "remains challenging": "remains challenging",
    "remains a challenge": "remains a challenge",
    "still challenging": "still challenging",
    "open problem": "open problem",
    "open challenge": "open challenge",
    "limited by": "limited by",
    "hindered by": "hindered by",
    "bottleneck": "bottleneck",
    "not yet": "not yet achieved",
    "remains elusive": "remains elusive",
    "poorly understood": "poorly understood",
    "major obstacle": "major obstacle",
    "key challenge": "key challenge",
    "yet to be": "yet to be solved",
}

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _representative_sentence(abstract: str, cue: str) -> str:
    for sentence in _SENT_SPLIT.split(abstract):
        if cue in sentence.lower():
            return sentence.strip()[:400]
    return f"Unresolved challenge ({cue})."


def compute_bottlenecks() -> dict:
    today = date.today()
    since = today - timedelta(days=LOOKBACK_DAYS)
    recent_cutoff = today - timedelta(days=90)

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT d.id AS doc_id, dt.technology_id AS tech,
                       d.abstract AS abstract, d.published_at AS published_at,
                       d.source_id AS source_id
                FROM document d
                JOIN document_technology dt ON dt.document_id = d.id
                WHERE d.abstract IS NOT NULL
                  AND d.published_at >= :since
                """
            ),
            {"since": since},
        ).mappings().all()

        # cluster key -> aggregate
        clusters: dict[tuple[str, str], dict] = {}
        for r in rows:
            text_l = (r["abstract"] or "").lower()
            tech = str(r["tech"])
            for cue, label in _CUES.items():
                if cue not in text_l:
                    continue
                key = (tech, label)
                c = clusters.setdefault(
                    key,
                    {
                        "technology_id": tech,
                        "label": label,
                        "docs": [],
                        "sources": set(),
                        "recent": 0,
                        "statement": "",
                    },
                )
                if len(c["docs"]) < MAX_SUPPORTING:
                    c["docs"].append(str(r["doc_id"]))
                c["sources"].add(str(r["source_id"]))
                if r["published_at"] and r["published_at"] >= recent_cutoff:
                    c["recent"] += 1
                if not c["statement"]:
                    c["statement"] = _representative_sentence(r["abstract"], cue)

        clusters = {
            k: v for k, v in clusters.items() if len(v["docs"]) >= MIN_FREQUENCY
        }
        if not clusters:
            conn.execute(text("DELETE FROM bottleneck"))
            return {"status": "empty", "bottlenecks": 0}

        freqs = [len(c["docs"]) for c in clusters.values()]
        freq_norm = dict(zip(clusters.keys(), minmax(freqs), strict=True))

        # severity = freq x recency x breadth (docs/ALGORITHMS.md §4)
        persisted = []
        for key, c in clusters.items():
            frequency = len(c["docs"])
            recency = clamp(c["recent"] / frequency)
            breadth = clamp(len(c["sources"]) / 3.0)  # >=3 sources => full breadth
            severity = clamp(
                freq_norm[key] * (0.4 + 0.6 * recency) * (0.5 + 0.5 * breadth)
            )
            persisted.append(
                {
                    "technology_id": c["technology_id"],
                    "problem_statement": c["statement"],
                    "frequency": frequency,
                    "supporting_docs": c["docs"],
                    "severity": severity,
                }
            )

        # Idempotent recompute.
        conn.execute(text("DELETE FROM bottleneck"))
        for row in persisted:
            conn.execute(
                text(
                    """
                    INSERT INTO bottleneck (
                        technology_id, problem_statement, frequency,
                        supporting_docs, severity
                    ) VALUES (
                        :technology_id, :problem_statement, :frequency,
                        CAST(:supporting_docs AS uuid[]), :severity
                    )
                    """
                ),
                row,
            )

    return {"status": "ok", "bottlenecks": len(persisted)}
