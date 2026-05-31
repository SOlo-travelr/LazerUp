"""Hybrid search service.

Combines PostgreSQL full-text search with pgvector ANN via Reciprocal Rank
Fusion (RRF). When no embedding provider is configured the vector branch is
skipped and search degrades gracefully to FTS only. SQL filters (doc type,
publish date, technology) are applied as a pre-filter in both branches.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embeddings import get_embedding_provider, to_pgvector
from app.schemas import SearchItem, SearchRequest, SearchResponse

_RRF_K = 60
_CANDIDATES = 50


def _build_filters(req: SearchRequest, id_col: str) -> tuple[str, dict]:
    clauses: list[str] = ["TRUE"]
    params: dict = {}
    if req.doc_types:
        clauses.append("doc_type = ANY(:doc_types)")
        params["doc_types"] = list(req.doc_types)
    if req.filters and req.filters.published_after:
        clauses.append("published_at >= :pub_after")
        params["pub_after"] = req.filters.published_after
    if req.filters and req.filters.technology:
        clauses.append(
            "EXISTS (SELECT 1 FROM document_technology dt "
            "JOIN technology t ON t.id = dt.technology_id "
            f"WHERE dt.document_id = {id_col} AND t.slug = :tech)"
        )
        params["tech"] = req.filters.technology
    return " AND ".join(clauses), params


def semantic_search(db: Session, req: SearchRequest) -> SearchResponse:
    query = req.query.strip()
    fused: dict[str, dict] = {}

    def fuse(rows) -> None:
        for rank, row in enumerate(rows, start=1):
            doc_id = str(row["id"])
            score = 1.0 / (_RRF_K + rank)
            if doc_id in fused:
                fused[doc_id]["rrf"] += score
            else:
                fused[doc_id] = {"row": row, "rrf": score}

    # ---- FTS branch ----
    if req.mode in ("hybrid", "keyword"):
        where, params = _build_filters(req, "document.id")
        params.update({"q": query, "limit": _CANDIDATES})
        fts_sql = text(
            f"""
            SELECT id, doc_type, title, abstract, url,
                   ts_rank(
                       to_tsvector('english', coalesce(title,'') || ' ' || coalesce(abstract,'')),
                       plainto_tsquery('english', :q)
                   ) AS score
            FROM document
            WHERE {where}
              AND (
                  :q = '' OR
                  to_tsvector('english', coalesce(title,'') || ' ' || coalesce(abstract,''))
                      @@ plainto_tsquery('english', :q)
              )
            ORDER BY score DESC NULLS LAST
            LIMIT :limit
            """
        )
        fuse(db.execute(fts_sql, params).mappings().all())

    # ---- Vector branch ----
    provider = get_embedding_provider()
    if req.mode in ("hybrid", "semantic") and provider.enabled and query:
        where, params = _build_filters(req, "d.id")
        params.update({"vec": to_pgvector(provider.embed_query(query)), "limit": _CANDIDATES})
        vec_sql = text(
            f"""
            SELECT d.id, d.doc_type, d.title, d.abstract, d.url,
                   1 - (de.embedding <=> CAST(:vec AS vector)) AS score
            FROM document d
            JOIN document_embedding de ON de.document_id = d.id
            WHERE {where}
            ORDER BY de.embedding <=> CAST(:vec AS vector)
            LIMIT :limit
            """
        )
        fuse(db.execute(vec_sql, params).mappings().all())

    ranked = sorted(fused.values(), key=lambda e: e["rrf"], reverse=True)[: req.limit]
    items = [
        SearchItem(
            id=e["row"]["id"],
            doc_type=e["row"]["doc_type"],
            title=e["row"]["title"],
            score=round(e["rrf"], 6),
            snippet=(e["row"]["abstract"] or "")[:240] or None,
            url=e["row"]["url"],
        )
        for e in ranked
    ]
    return SearchResponse(items=items, next_cursor=None)
