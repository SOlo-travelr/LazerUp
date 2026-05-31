"""RAG Ask service (docs/ALGORITHMS.md §8).

Retrieves with the existing hybrid (FTS + vector) search, then generates a
grounded answer with inline citations. When no LLM is configured it returns an
extractive answer built from the top retrieved snippets so the endpoint still
works end-to-end.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.llm import get_llm_provider
from app.schemas import AskRequest, AskResponse, Citation, SearchFilters, SearchRequest
from app.services.search import semantic_search

_SYSTEM = (
    "You are a battery-industry research assistant. Answer ONLY from the provided "
    "context passages and cite them inline as [n]. If the context is insufficient, "
    "say so plainly. Do not invent facts."
)


def ask(db: Session, req: AskRequest) -> AskResponse:
    search_req = SearchRequest(
        query=req.question,
        doc_types=req.doc_types,
        filters=SearchFilters(technology=req.technology) if req.technology else None,
        mode="hybrid",
        limit=req.limit,
    )
    results = semantic_search(db, search_req)
    items = results.items

    citations = [Citation(id=it.id, title=it.title, url=it.url) for it in items]
    if not items:
        return AskResponse(
            answer="I couldn't find supporting documents for that question.",
            citations=[],
            grounded=False,
        )

    context = "\n\n".join(
        f"[{i}] {it.title}\n{it.snippet or ''}" for i, it in enumerate(items, start=1)
    )

    provider = get_llm_provider()
    if provider.enabled:
        answer = provider.complete(_SYSTEM, f"Context:\n{context}\n\nQuestion: {req.question}")
        if answer:
            return AskResponse(answer=answer, citations=citations, grounded=True)

    # Extractive fallback.
    top = items[:3]
    extract = " ".join(f"{it.title}: {(it.snippet or '').strip()}" for it in top)
    answer = (
        f"Based on the most relevant sources: {extract} "
        f"[{', '.join(str(i) for i in range(1, len(top) + 1))}]"
    )
    return AskResponse(answer=answer, citations=citations, grounded=False)
