"""Search service.

M1 placeholder: keyword search over title/abstract. The hybrid vector + FTS
implementation (pgvector ANN ∪ Postgres FTS, RRF-fused) lands in milestone M5.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document
from app.schemas import SearchItem, SearchRequest, SearchResponse


def semantic_search(db: Session, req: SearchRequest) -> SearchResponse:
    stmt = select(Document)
    if req.doc_types:
        stmt = stmt.where(Document.doc_type.in_(req.doc_types))
    stmt = stmt.where(Document.title.ilike(f"%{req.query}%")).limit(req.limit)

    rows = db.execute(stmt).scalars().all()
    items = [
        SearchItem(
            id=d.id,
            doc_type=d.doc_type,
            title=d.title,
            score=1.0,
            snippet=(d.abstract or "")[:240] or None,
            url=d.url,
        )
        for d in rows
    ]
    return SearchResponse(items=items, next_cursor=None)
