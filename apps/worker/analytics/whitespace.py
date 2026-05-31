"""White-space detection (docs/ALGORITHMS.md §3).

    WhiteSpace_t = R_t * 1[F_t > tau_F] * (1 - D_t)

R = normalized research activity (recent papers+patents), F = normalized funding
presence with a gate so money is actually moving, D = normalized startup density.
High research + funding above threshold + low density => high score. Idempotent
recompute into ``white_space``.
"""

from __future__ import annotations

from sqlalchemy import text

from analytics import metrics
from analytics.mathx import minmax
from db import engine

FUNDING_GATE = 0.15  # normalized funding must exceed this for a true white space


def compute_white_spaces() -> dict:
    with engine.begin() as conn:
        names = metrics.technology_names(conn)
        if not names:
            conn.execute(text("DELETE FROM white_space"))
            return {"status": "empty", "white_spaces": 0}

        corpus = metrics.corpus_metrics(conn)
        density = metrics.startup_density(conn)
        funding = metrics.funding_recent(conn)

        tech_ids = list(names.keys())
        research_raw = [
            corpus.get(t, {}).get("paper_recent", 0) + corpus.get(t, {}).get("patent_recent", 0)
            for t in tech_ids
        ]
        funding_raw = [funding.get(t, 0.0) for t in tech_ids]
        density_raw = [float(density.get(t, 0)) for t in tech_ids]

        r_norm = dict(zip(tech_ids, minmax(research_raw), strict=True))
        f_norm = dict(zip(tech_ids, minmax(funding_raw), strict=True))
        d_norm = dict(zip(tech_ids, minmax(density_raw), strict=True))

        results = []
        for t in tech_ids:
            r, f, d = r_norm[t], f_norm[t], d_norm[t]
            gate = 1.0 if f > FUNDING_GATE else 0.0
            score = r * gate * (1.0 - d)
            crowded = d > 0.66 and r < 0.34
            rationale = (
                f"{names[t]['name']}: research activity {r:.2f}, funding presence {f:.2f}, "
                f"startup density {d:.2f}. "
                + (
                    "Overcrowded — high density with cooling research."
                    if crowded
                    else (
                        "Open white space — rising research and active funding with few "
                        "incumbents."
                        if score > 0
                        else "Below funding gate; not an actionable white space yet."
                    )
                )
            )
            results.append(
                {
                    "technology_id": t,
                    "research_activity": r,
                    "funding_present": f,
                    "startup_density": d,
                    "whitespace_score": score,
                    "rationale": rationale,
                }
            )

        conn.execute(text("DELETE FROM white_space"))
        for row in results:
            conn.execute(
                text(
                    """
                    INSERT INTO white_space (
                        technology_id, research_activity, funding_present,
                        startup_density, whitespace_score, rationale
                    ) VALUES (
                        :technology_id, :research_activity, :funding_present,
                        :startup_density, :whitespace_score, :rationale
                    )
                    """
                ),
                row,
            )

    return {"status": "ok", "white_spaces": len(results)}
