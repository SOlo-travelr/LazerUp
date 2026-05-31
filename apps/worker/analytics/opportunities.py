"""Opportunity detection engine (docs/ALGORITHMS.md §2).

    OppScore = w_M*M + w_F*F + w_G*G + w_B*B,  w = {0.30, 0.25, 0.30, 0.15}

M = momentum (latest trend composite), F = funding presence, G = gap (inverse
startup density), B = buildability (inverse worst-bottleneck severity). Confidence
is evidence strength, independent of score. The LLM only narrates the brief from
the computed evidence; numbers come from the formulas. Idempotent recompute into
``opportunity`` (active rows replaced).
"""

from __future__ import annotations

import json
import math

from sqlalchemy import text

from analytics import metrics
from analytics.mathx import clamp, minmax, sigmoid
from db import engine
from llm import get_llm_provider

WEIGHTS = {"M": 0.30, "F": 0.25, "G": 0.30, "B": 0.15}
DEFAULT_BUILDABILITY = 0.5
MIN_NDOCS = 1  # ignore technologies with no corpus
TOP_N = 30

# Confidence = sigmoid(alpha*ln(1+Ndocs) + beta*source_diversity + gamma*recency)
_ALPHA, _BETA, _GAMMA = 0.45, 0.30, 1.0

_CATEGORY_CAPABILITIES = {
    "chemistry": ["electrochemistry", "materials science", "synthesis"],
    "materials": ["materials science", "characterization", "modeling"],
    "manufacturing": ["process engineering", "scale-up", "automation"],
    "software": ["machine learning", "simulation", "data engineering"],
    "recycling": ["process chemistry", "separation", "sustainability"],
    "systems": ["systems engineering", "controls", "thermal management"],
}


def _required_capabilities(name: str, category: str) -> list[str]:
    caps = list(_CATEGORY_CAPABILITIES.get(category.lower(), ["materials science"]))
    for token in name.replace("-", " ").split():
        if len(token) > 3 and token.lower() not in {"battery", "based"}:
            caps.append(token.lower())
    # de-dup preserving order
    seen: set[str] = set()
    out = []
    for c in caps:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:8]


def _risk_label(buildability: float) -> str:
    if buildability >= 0.66:
        return "Low"
    if buildability >= 0.34:
        return "Medium"
    return "High"


def _commercial_label(score: float) -> str:
    if score >= 0.66:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"


def _template_brief(name: str, ev: dict) -> tuple[str, str]:
    title = f"{name} — {_commercial_label(ev['score'])}-potential opportunity"
    thesis = (
        f"{name} shows momentum {ev['M']:.2f}, funding presence {ev['F']:.2f}, "
        f"market gap {ev['G']:.2f} and buildability {ev['B']:.2f}. "
        f"Evidence: {ev['paper_recent']} recent papers, {ev['patent_recent']} patents, "
        f"${ev['funding_recent']:,.0f} in recent funding across {ev['org_count']} "
        f"organizations. A focused team can address this with "
        f"{', '.join(ev['required_capabilities'][:3])}."
    )
    return title, thesis


def _llm_brief(provider, name: str, ev: dict) -> tuple[str, str] | None:
    prompt = (
        "You are a battery-industry analyst. Using ONLY the evidence JSON, write a "
        "startup opportunity brief. Return strict JSON with keys 'title' and 'thesis'. "
        "Do not invent numbers.\n\nEvidence:\n" + json.dumps(ev)
    )
    out = provider.complete(
        "You produce concise, grounded startup opportunity briefs.", prompt, max_tokens=400
    )
    if not out:
        return None
    try:
        data = json.loads(out[out.index("{") : out.rindex("}") + 1])
        return str(data["title"]), str(data["thesis"])
    except Exception:
        return None


def compute_opportunities() -> dict:
    provider = get_llm_provider()
    with engine.begin() as conn:
        names = metrics.technology_names(conn)
        if not names:
            conn.execute(text("DELETE FROM opportunity WHERE status = 'active'"))
            return {"status": "empty", "opportunities": 0}

        corpus = metrics.corpus_metrics(conn)
        density = metrics.startup_density(conn)
        funding = metrics.funding_recent(conn)
        trend = metrics.latest_trend(conn)
        severity = metrics.max_bottleneck_severity(conn)

        tech_ids = [t for t in names if corpus.get(t, {}).get("ndocs", 0) >= MIN_NDOCS]
        if not tech_ids:
            conn.execute(text("DELETE FROM opportunity WHERE status = 'active'"))
            return {"status": "empty", "opportunities": 0}

        funding_norm = dict(
            zip(tech_ids, minmax([funding.get(t, 0.0) for t in tech_ids]), strict=True)
        )
        density_norm = dict(
            zip(tech_ids, minmax([float(density.get(t, 0)) for t in tech_ids]), strict=True)
        )

        candidates = []
        for t in tech_ids:
            info = names[t]
            c = corpus.get(t, {})
            ndocs = c.get("ndocs", 0)
            recent_docs = c.get("recent_docs", 0)
            diversity = c.get("source_diversity", 0)

            M = trend.get(t, {}).get("composite", 0.0)
            F = funding_norm[t]
            G = 1.0 - density_norm[t]
            B = 1.0 - severity.get(t, 0.0) if t in severity else DEFAULT_BUILDABILITY
            score = clamp(WEIGHTS["M"] * M + WEIGHTS["F"] * F + WEIGHTS["G"] * G + WEIGHTS["B"] * B)

            recency = clamp(recent_docs / ndocs) if ndocs else 0.0
            confidence = sigmoid(
                _ALPHA * math.log1p(ndocs) + _BETA * diversity + _GAMMA * recency - 1.5
            )

            ev = {
                "technology": info["name"],
                "category": info["category"],
                "M": round(M, 4),
                "F": round(F, 4),
                "G": round(G, 4),
                "B": round(B, 4),
                "score": round(score, 4),
                "confidence": round(confidence, 4),
                "paper_recent": c.get("paper_recent", 0),
                "patent_recent": c.get("patent_recent", 0),
                "funding_recent": funding.get(t, 0.0),
                "org_count": density.get(t, 0),
                "ndocs": ndocs,
                "required_capabilities": _required_capabilities(info["name"], info["category"]),
            }
            reshuffle_priority = clamp(
                score
                + 0.04 * sigmoid(recent_docs / 3.0)
                + 0.03 * sigmoid(float(ev["paper_recent"]) + float(ev["patent_recent"]))
                + 0.02 * sigmoid(math.log1p(float(ev["funding_recent"])) / 8.0)
                + 0.01 * confidence
            )
            ev["reshuffle_score"] = round(reshuffle_priority, 4)
            candidates.append(
                {
                    "technology_id": t,
                    "evidence": ev,
                    "score": score,
                    "confidence": confidence,
                    "reshuffle_score": reshuffle_priority,
                    "buildability": B,
                    "name": info["name"],
                    "category": info["category"],
                }
            )

        candidates.sort(key=lambda x: (x["reshuffle_score"], x["score"], x["confidence"]), reverse=True)
        candidates = candidates[:TOP_N]

        conn.execute(text("DELETE FROM opportunity WHERE status = 'active'"))
        for cand in candidates:
            ev = cand["evidence"]
            brief = (_llm_brief(provider, cand["name"], ev) if provider.enabled else None) or (
                _template_brief(cand["name"], ev)
            )
            title, thesis = brief
            conn.execute(
                text(
                    """
                    INSERT INTO opportunity (
                        title, thesis, technology_id, evidence, market,
                        technical_risk, commercial_potential, confidence, score, status
                    ) VALUES (
                        :title, :thesis, :technology_id, CAST(:evidence AS jsonb), :market,
                        :technical_risk, :commercial_potential, :confidence, :score, 'active'
                    )
                    """
                ),
                {
                    "title": title,
                    "thesis": thesis,
                    "technology_id": cand["technology_id"],
                    "evidence": json.dumps(ev),
                    "market": f"{cand['category'].title()} battery solutions",
                    "technical_risk": _risk_label(cand["buildability"]),
                    "commercial_potential": _commercial_label(cand["score"]),
                    "confidence": cand["confidence"],
                    "score": cand["score"],
                },
            )

    return {"status": "ok", "opportunities": len(candidates)}
