from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    env: str
    version: str


class TechnologyOut(BaseModel):
    id: UUID
    slug: str
    name: str
    category: str

    model_config = {"from_attributes": True}


class SearchFilters(BaseModel):
    published_after: date | None = None
    technology: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    doc_types: list[str] | None = None
    filters: SearchFilters | None = None
    mode: str = "hybrid"
    limit: int = Field(20, ge=1, le=100)


class SearchItem(BaseModel):
    id: UUID
    doc_type: str
    title: str
    score: float
    snippet: str | None = None
    url: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchItem]
    next_cursor: str | None = None


class TrendComponents(BaseModel):
    paper_growth: float
    patent_growth: float
    funding_momentum: float


class TrendItem(BaseModel):
    technology: TechnologyOut
    composite_score: float
    components: TrendComponents
    rank: int
