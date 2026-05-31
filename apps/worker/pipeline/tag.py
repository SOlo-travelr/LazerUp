"""Technology tagging stage.

Links documents to taxonomy technologies by matching each technology's
``aliases`` (keyword phrases) against the document title + abstract. Populates
``document_technology`` so the analytics engines (trends, white-space,
opportunities, bottlenecks) have per-technology corpora to score.

Matching is case-insensitive with word boundaries to avoid spurious substring
hits (e.g. the acronym "lto" inside another word). Idempotent: existing links
are preserved via ``ON CONFLICT DO NOTHING``, so re-runs only add new links as
the corpus or taxonomy grows.
"""

from __future__ import annotations

import re

from sqlalchemy import text

from db import engine

_SELECT_TECHS = text("SELECT id, slug, aliases FROM technology")

_SELECT_DOCS = text(
    """
    SELECT id,
           coalesce(title, '') || ' ' || coalesce(abstract, '') AS content
    FROM document
    """
)

_INSERT_LINK = text(
    """
    INSERT INTO document_technology (document_id, technology_id, confidence)
    VALUES (:document_id, :technology_id, :confidence)
    ON CONFLICT (document_id, technology_id) DO NOTHING
    """
)


def _compile(aliases: list[str]) -> re.Pattern | None:
    parts = [re.escape(a.strip()) for a in aliases if a and a.strip()]
    if not parts:
        return None
    # Longest-first so multi-word phrases win; word boundaries on both ends.
    parts.sort(key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b", re.IGNORECASE)


def tag_documents() -> dict:
    with engine.begin() as conn:
        techs = conn.execute(_SELECT_TECHS).mappings().all()
        patterns: list[tuple[str, re.Pattern]] = []
        for t in techs:
            pat = _compile(list(t["aliases"] or []))
            if pat is not None:
                patterns.append((str(t["id"]), pat))

        if not patterns:
            return {"status": "empty", "reason": "no_technology_aliases"}

        docs = conn.execute(_SELECT_DOCS).mappings().all()
        links = 0
        tagged_docs = 0
        for doc in docs:
            content = doc["content"] or ""
            matched = False
            for tech_id, pat in patterns:
                m = pat.findall(content)
                if not m:
                    continue
                matched = True
                # More distinct mentions -> higher confidence (capped at 1.0).
                confidence = min(1.0, 0.6 + 0.1 * len(set(x.lower() for x in m)))
                conn.execute(
                    _INSERT_LINK,
                    {
                        "document_id": str(doc["id"]),
                        "technology_id": tech_id,
                        "confidence": confidence,
                    },
                )
                links += 1
            if matched:
                tagged_docs += 1

    return {
        "status": "ok",
        "documents": len(docs),
        "tagged_documents": tagged_docs,
        "technologies": len(patterns),
        "links": links,
    }


if __name__ == "__main__":
    print(tag_documents())
