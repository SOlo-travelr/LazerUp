"""Trend detection & scoring (docs/ALGORITHMS.md §1).

Detects *acceleration* across four signals (papers, patents, funding, grants),
log-damps, z-scores across technologies, and squashes a weighted composite to
[0, 1]. Persists ranked rows to ``trend_score`` (upsert on technology+window).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Connection

from analytics.mathx import acceleration, log_damp, sigmoid, zscores
from db import engine

WINDOW_DAYS = 90
WEIGHTS = {"paper": 0.30, "patent": 0.25, "funding": 0.30, "grant": 0.15}

# doc_type -> trend signal key
_DOC_SIGNAL = {"paper": "paper", "patent": "patent", "grant": "grant"}


def _doc_counts(conn: Connection, recent_start: date, prior_start: date) -> dict[str, dict]:
    """Per-technology recent/prior counts split by doc_type."""
    rows = conn.execute(
        text(
            """
            SELECT dt.technology_id AS tech, d.doc_type AS doc_type,
                   SUM(CASE WHEN d.published_at >= :recent_start THEN 1 ELSE 0 END) AS recent,
                   SUM(CASE WHEN d.published_at >= :prior_start
                             AND d.published_at < :recent_start THEN 1 ELSE 0 END) AS prior
            FROM document_technology dt
            JOIN document d ON d.id = dt.document_id
            WHERE d.published_at >= :prior_start
            GROUP BY dt.technology_id, d.doc_type
            """
        ),
        {"recent_start": recent_start, "prior_start": prior_start},
    ).mappings().all()

    out: dict[str, dict] = {}
    for r in rows:
        signal = _DOC_SIGNAL.get(r["doc_type"])
        if signal is None:
            continue
        bucket = out.setdefault(str(r["tech"]), {})
        bucket[signal] = (float(r["recent"] or 0), float(r["prior"] or 0))
    return out


def _funding_amounts(conn: Connection, recent_start: date, prior_start: date) -> dict[str, tuple]:
    """Per-technology recent/prior funding USD (grants + funding rounds)."""
    grant = conn.execute(
        text(
            """
            SELECT dt.technology_id AS tech,
                   SUM(CASE WHEN ga.start_date >= :recent_start
                            THEN COALESCE(ga.amount_usd, 0) ELSE 0 END) AS recent,
                   SUM(CASE WHEN ga.start_date >= :prior_start
                             AND ga.start_date < :recent_start
                            THEN COALESCE(ga.amount_usd, 0) ELSE 0 END) AS prior
            FROM grant_award ga
            JOIN document_technology dt ON dt.document_id = ga.document_id
            WHERE ga.start_date >= :prior_start
            GROUP BY dt.technology_id
            """
        ),
        {"recent_start": recent_start, "prior_start": prior_start},
    ).mappings().all()

    rounds = conn.execute(
        text(
            """
            SELECT dt.technology_id AS tech,
                   SUM(CASE WHEN fe.announced_at >= :recent_start
                            THEN COALESCE(fe.amount_usd, 0) ELSE 0 END) AS recent,
                   SUM(CASE WHEN fe.announced_at >= :prior_start
                             AND fe.announced_at < :recent_start
                            THEN COALESCE(fe.amount_usd, 0) ELSE 0 END) AS prior
            FROM funding_event fe
            JOIN document_technology dt ON dt.document_id = fe.document_id
            WHERE fe.announced_at >= :prior_start
            GROUP BY dt.technology_id
            """
        ),
        {"recent_start": recent_start, "prior_start": prior_start},
    ).mappings().all()

    out: dict[str, list[float]] = {}
    for r in list(grant) + list(rounds):
        acc = out.setdefault(str(r["tech"]), [0.0, 0.0])
        acc[0] += float(r["recent"] or 0)
        acc[1] += float(r["prior"] or 0)
    return {k: (v[0], v[1]) for k, v in out.items()}


def compute_trends() -> dict:
    today = date.today()
    recent_start = today - timedelta(days=WINDOW_DAYS)
    prior_start = today - timedelta(days=2 * WINDOW_DAYS)

    with engine.begin() as conn:
        tech_ids = [str(r[0]) for r in conn.execute(text("SELECT id FROM technology")).all()]
        if not tech_ids:
            return {"status": "empty", "technologies": 0}

        docs = _doc_counts(conn, recent_start, prior_start)
        funds = _funding_amounts(conn, recent_start, prior_start)

        # Raw, log-damped acceleration per signal, aligned across all technologies.
        signals = ("paper", "patent", "funding", "grant")
        damped: dict[str, list[float]] = {s: [] for s in signals}
        for tid in tech_ids:
            d = docs.get(tid, {})
            for s in ("paper", "patent", "grant"):
                recent, prior = d.get(s, (0.0, 0.0))
                damped[s].append(log_damp(acceleration(recent, prior)))
            f_recent, f_prior = funds.get(tid, (0.0, 0.0))
            damped["funding"].append(log_damp(acceleration(f_recent, f_prior, eps=1.0)))

        z = {s: zscores(damped[s]) for s in signals}

        ranked: list[dict] = []
        for i, tid in enumerate(tech_ids):
            composite = sigmoid(sum(WEIGHTS[s] * z[s][i] for s in signals))
            ranked.append(
                {
                    "technology_id": tid,
                    "paper_growth": damped["paper"][i],
                    "patent_growth": damped["patent"][i],
                    "funding_momentum": damped["funding"][i],
                    "grant_momentum": damped["grant"][i],
                    "composite_score": composite,
                }
            )

        ranked.sort(key=lambda r: r["composite_score"], reverse=True)
        for rank, row in enumerate(ranked, start=1):
            row["rank"] = rank
            conn.execute(
                text(
                    """
                    INSERT INTO trend_score (
                        technology_id, window_start, window_end,
                        paper_growth, patent_growth, funding_momentum, grant_momentum,
                        composite_score, rank
                    ) VALUES (
                        :technology_id, :window_start, :window_end,
                        :paper_growth, :patent_growth, :funding_momentum, :grant_momentum,
                        :composite_score, :rank
                    )
                    ON CONFLICT (technology_id, window_end) DO UPDATE SET
                        window_start     = EXCLUDED.window_start,
                        paper_growth     = EXCLUDED.paper_growth,
                        patent_growth    = EXCLUDED.patent_growth,
                        funding_momentum = EXCLUDED.funding_momentum,
                        grant_momentum   = EXCLUDED.grant_momentum,
                        composite_score  = EXCLUDED.composite_score,
                        rank             = EXCLUDED.rank
                    """
                ),
                {**row, "window_start": recent_start, "window_end": today},
            )

    return {"status": "ok", "technologies": len(ranked), "window_end": today.isoformat()}
