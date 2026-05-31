from datetime import date, datetime
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
    grant_momentum: float = 0.0


class TrendItem(BaseModel):
    technology: TechnologyOut
    composite_score: float
    components: TrendComponents
    rank: int


# ----- Opportunities -----


class OpportunityItem(BaseModel):
    id: UUID
    title: str
    thesis: str
    technology: str | None = None
    market: str | None = None
    technical_risk: str | None = None
    commercial_potential: str | None = None
    score: float
    confidence: float
    evidence: dict


# ----- White space -----


class WhiteSpaceItem(BaseModel):
    id: UUID
    technology: str | None = None
    research_activity: float
    funding_present: float
    startup_density: float
    whitespace_score: float
    rationale: str | None = None


# ----- Bottlenecks -----


class BottleneckItem(BaseModel):
    id: UUID
    technology: str | None = None
    problem_statement: str
    frequency: int
    severity: float


# ----- Founder fit -----


class FounderProfileRequest(BaseModel):
    email: str | None = None
    skills: list[str] = Field(default_factory=list)
    research_areas: list[str] = Field(default_factory=list)
    summary: str | None = Field(
        default=None, description="Free-text bio used to build the profile embedding."
    )


class FounderProfileOut(BaseModel):
    id: UUID
    skills: list[str]
    research_areas: list[str]
    embedded: bool


class FounderFitItem(BaseModel):
    opportunity_id: UUID
    title: str
    fit_score: float
    rationale: str
    matched: list[str]
    gaps: list[str]


# ----- RAG / Ask -----


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    doc_types: list[str] | None = None
    technology: str | None = None
    limit: int = Field(8, ge=1, le=20)


class Citation(BaseModel):
    id: UUID
    title: str
    url: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool


# ----- Weekly report -----


class WeeklyReportOut(BaseModel):
    week_start: date
    payload: dict
    generated_at: datetime | None = None
