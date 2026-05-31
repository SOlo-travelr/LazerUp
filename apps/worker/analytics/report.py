"""Weekly Intelligence Report (docs/ALGORITHMS.md §6).

Aggregates the week's top rows from the derived tables, optionally narrates each
section with the LLM (deterministic template fallback), and upserts the JSON
payload into ``weekly_report`` keyed by ISO week start (Monday).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Connection

from db import engine
from llm import get_llm_provider

TOP_N = 5


def _week_start(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def _top_technologies(conn: Connection) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (ts.technology_id)
                   t.name AS name, ts.composite_score AS score, ts.rank AS rank
            FROM trend_score ts
            JOIN technology t ON t.id = ts.technology_id
            ORDER BY ts.technology_id, ts.window_end DESC
            """
        )
    ).mappings().all()
    ranked = sorted(rows, key=lambda r: r["score"] or 0, reverse=True)[:TOP_N]
    return [{"name": r["name"], "score": round(r["score"] or 0, 4)} for r in ranked]


def _top_opportunities(conn: Connection) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT title, score, confidence, technical_risk, commercial_potential
            FROM opportunity
            WHERE status = 'active'
            ORDER BY score DESC
            LIMIT :n
            """
        ),
        {"n": TOP_N},
    ).mappings().all()
    return [
        {
            "title": r["title"],
            "score": round(r["score"] or 0, 4),
            "confidence": round(r["confidence"] or 0, 4),
            "technical_risk": r["technical_risk"],
            "commercial_potential": r["commercial_potential"],
        }
        for r in rows
    ]


def _top_grants(conn: Connection, since: date) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT d.title AS title, ga.program AS program, ga.amount_usd AS amount
            FROM grant_award ga
            JOIN document d ON d.id = ga.document_id
            WHERE COALESCE(ga.start_date, d.published_at) >= :since
            ORDER BY ga.amount_usd DESC NULLS LAST
            LIMIT :n
            """
        ),
        {"since": since, "n": TOP_N},
    ).mappings().all()
    return [
        {"title": r["title"], "program": r["program"], "amount_usd": float(r["amount"] or 0)}
        for r in rows
    ]


def _top_patents(conn: Connection, since: date) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT d.title AS title, p.patent_number AS patent_number
            FROM patent p
            JOIN document d ON d.id = p.document_id
            WHERE COALESCE(p.grant_date, d.published_at) >= :since
            ORDER BY COALESCE(p.grant_date, d.published_at) DESC
            LIMIT :n
            """
        ),
        {"since": since, "n": TOP_N},
    ).mappings().all()
    return [{"title": r["title"], "patent_number": r["patent_number"]} for r in rows]


def _top_funding(conn: Connection, since: date) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT o.name AS org, fe.round AS round, fe.amount_usd AS amount
            FROM funding_event fe
            LEFT JOIN organization o ON o.id = fe.org_id
            WHERE fe.announced_at >= :since
            ORDER BY fe.amount_usd DESC NULLS LAST
            LIMIT :n
            """
        ),
        {"since": since, "n": TOP_N},
    ).mappings().all()
    return [
        {"org": r["org"], "round": r["round"], "amount_usd": float(r["amount"] or 0)}
        for r in rows
    ]


def _narrative(payload: dict) -> str | None:
    provider = get_llm_provider()
    if not provider.enabled:
        techs = ", ".join(t["name"] for t in payload["top_technologies"][:3]) or "n/a"
        opps = payload["top_opportunities"][0]["title"] if payload["top_opportunities"] else "n/a"
        return (
            f"This week the fastest-accelerating battery technologies were {techs}. "
            f"The leading opportunity is {opps}. "
            f"{len(payload['top_grants'])} notable grants and "
            f"{len(payload['top_funding'])} funding rounds were recorded."
        )
    return provider.complete(
        "You write concise executive battery-intelligence summaries grounded in the data.",
        "Write a 4-6 sentence executive summary from this weekly data (do not invent "
        "numbers):\n" + json.dumps(payload),
        max_tokens=400,
    )


def build_weekly_report() -> dict:
    week_start = _week_start()
    since = week_start - timedelta(days=7)

    with engine.begin() as conn:
        payload = {
            "week_start": week_start.isoformat(),
            "top_technologies": _top_technologies(conn),
            "top_opportunities": _top_opportunities(conn),
            "top_grants": _top_grants(conn, since),
            "top_patents": _top_patents(conn, since),
            "top_funding": _top_funding(conn, since),
        }
        payload["summary"] = _narrative(payload)

        conn.execute(
            text(
                """
                INSERT INTO weekly_report (week_start, payload)
                VALUES (:week_start, CAST(:payload AS jsonb))
                ON CONFLICT (week_start) DO UPDATE SET
                    payload = EXCLUDED.payload,
                    generated_at = now()
                """
            ),
            {"week_start": week_start, "payload": json.dumps(payload)},
        )

    return {"status": "ok", "week_start": week_start.isoformat()}
