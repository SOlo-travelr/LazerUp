"""Founder Fit scoring (docs/ALGORITHMS.md §5).

Hybrid score combining a semantic profile<->opportunity match with symbolic skill
overlap, domain alignment and risk alignment:

    Fit = w1*cos + w2*SkillJaccard + w3*DomainMatch + w4*RiskAlignment

When no embedding provider is configured the semantic term is dropped and its
weight is redistributed across the symbolic terms, so the score stays meaningful.
"""

from __future__ import annotations

import json
import math
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embeddings import get_embedding_provider, to_pgvector
from app.core.llm import get_llm_provider
from app.schemas import FounderFitItem, FounderProfileOut, FounderProfileRequest

_W = {"cos": 0.40, "jaccard": 0.25, "domain": 0.20, "risk": 0.15}
_RISK_LEVEL = {"High": 1.0, "Medium": 0.6, "Low": 0.3}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _tokens(values: list[str]) -> set[str]:
    out: set[str] = set()
    for v in values:
        for tok in str(v).replace("-", " ").lower().split():
            if len(tok) > 2:
                out.add(tok)
    return out


def create_profile(db: Session, req: FounderProfileRequest) -> FounderProfileOut:
    provider = get_embedding_provider()
    profile_id = uuid.uuid4()
    user_id = None

    if req.email:
        user_id = db.execute(
            text(
                """
                INSERT INTO app_user (email) VALUES (:email)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING id
                """
            ),
            {"email": req.email},
        ).scalar()

    text_blob = req.summary or " ".join(req.skills + req.research_areas)
    embedded = False
    embedding_sql = "NULL"
    params: dict = {
        "id": profile_id,
        "user_id": user_id,
        "skills": req.skills,
        "research_areas": req.research_areas,
    }
    if provider.enabled and text_blob.strip():
        params["embedding"] = to_pgvector(provider.embed_query(text_blob))
        embedding_sql = "CAST(:embedding AS vector)"
        embedded = True

    db.execute(
        text(
            f"""
            INSERT INTO founder_profile (id, user_id, skills, research_areas, embedding)
            VALUES (:id, :user_id, :skills, :research_areas, {embedding_sql})
            """
        ),
        params,
    )
    db.commit()
    return FounderProfileOut(
        id=profile_id,
        skills=req.skills,
        research_areas=req.research_areas,
        embedded=embedded,
    )


def _profile_embedding(db: Session, profile_id: uuid.UUID) -> list[float] | None:
    row = db.execute(
        text(
            "SELECT CASE WHEN embedding IS NULL THEN NULL ELSE embedding::text END AS emb "
            "FROM founder_profile WHERE id = :id"
        ),
        {"id": profile_id},
    ).first()
    if not row or row[0] is None:
        return None
    return [float(x) for x in row[0].strip("[]").split(",") if x]


def score_fit(db: Session, profile_id: uuid.UUID, limit: int = 20) -> list[FounderFitItem]:
    prof = db.execute(
        text("SELECT skills, research_areas FROM founder_profile WHERE id = :id"),
        {"id": profile_id},
    ).mappings().first()
    if not prof:
        return []

    skills = list(prof["skills"] or [])
    research = list(prof["research_areas"] or [])
    skill_set = {s.lower() for s in skills}
    research_tokens = _tokens(research)
    depth = min(1.0, len(skills) / 8.0 + (0.3 if research else 0.0))

    profile_emb = _profile_embedding(db, profile_id)
    embed_provider = get_embedding_provider()
    use_semantic = profile_emb is not None and embed_provider.enabled

    opportunities = db.execute(
        text(
            """
            SELECT o.id, o.title, o.thesis, o.technical_risk, o.evidence,
                   t.name AS tech_name, t.category AS tech_category
            FROM opportunity o
            LEFT JOIN technology t ON t.id = o.technology_id
            WHERE o.status = 'active'
            """
        )
    ).mappings().all()

    llm = get_llm_provider()
    results: list[FounderFitItem] = []
    for o in opportunities:
        evidence = o["evidence"] or {}
        required = [c.lower() for c in evidence.get("required_capabilities", [])]
        required_set = set(required)

        inter = skill_set & required_set
        union = skill_set | required_set
        jaccard = len(inter) / len(union) if union else 0.0

        domain_tokens = _tokens([o["tech_name"] or "", o["tech_category"] or ""])
        domain = 1.0 if research_tokens & domain_tokens else (0.4 if domain_tokens else 0.0)

        risk_level = _RISK_LEVEL.get(o["technical_risk"] or "Medium", 0.6)
        risk_align = 1.0 - abs(risk_level - depth)

        cos = 0.0
        if use_semantic and embed_provider.enabled:
            opp_emb = embed_provider.embed_query(f"{o['title']}. {o['thesis']}")
            cos = _cosine(profile_emb, opp_emb)

        if use_semantic:
            fit = (
                _W["cos"] * cos
                + _W["jaccard"] * jaccard
                + _W["domain"] * domain
                + _W["risk"] * risk_align
            )
        else:
            # Redistribute the semantic weight across symbolic terms.
            sym = _W["jaccard"] + _W["domain"] + _W["risk"]
            fit = (
                (_W["jaccard"] / sym) * jaccard
                + (_W["domain"] / sym) * domain
                + (_W["risk"] / sym) * risk_align
            )

        matched = sorted(inter | (research_tokens & domain_tokens))
        gaps = sorted(required_set - skill_set)
        rationale = _rationale(llm, o["title"], matched, gaps, fit)

        db.execute(
            text(
                """
                INSERT INTO founder_fit (
                    profile_id, opportunity_id, fit_score, rationale, skill_overlap
                ) VALUES (
                    :profile_id, :opportunity_id, :fit_score, :rationale,
                    CAST(:skill_overlap AS jsonb)
                )
                ON CONFLICT (profile_id, opportunity_id) DO UPDATE SET
                    fit_score = EXCLUDED.fit_score,
                    rationale = EXCLUDED.rationale,
                    skill_overlap = EXCLUDED.skill_overlap
                """
            ),
            {
                "profile_id": profile_id,
                "opportunity_id": o["id"],
                "fit_score": round(fit, 6),
                "rationale": rationale,
                "skill_overlap": json.dumps({"matched": matched, "gaps": gaps}),
            },
        )
        results.append(
            FounderFitItem(
                opportunity_id=o["id"],
                title=o["title"],
                fit_score=round(fit, 6),
                rationale=rationale,
                matched=matched,
                gaps=gaps,
            )
        )

    db.commit()
    results.sort(key=lambda r: r.fit_score, reverse=True)
    return results[:limit]


def _rationale(llm, title: str, matched: list[str], gaps: list[str], fit: float) -> str:
    template = (
        f"Fit {fit:.2f}. Strengths: {', '.join(matched) or 'limited direct overlap'}. "
        f"Gaps: {', '.join(gaps) or 'none significant'}."
    )
    if not llm.enabled:
        return template
    out = llm.complete(
        "You explain founder-opportunity fit in two sentences, grounded in the overlap.",
        f"Opportunity: {title}\nMatched: {matched}\nGaps: {gaps}\nFit score: {fit:.2f}",
        max_tokens=160,
    )
    return out or template
