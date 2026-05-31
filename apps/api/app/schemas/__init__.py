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


# ----- Linkage -----


class LinkageEntity(BaseModel):
    id: UUID
    name: str
    count: int = 0
    extra: dict = Field(default_factory=dict)


class LinkageChainSample(BaseModel):
    paper_title: str
    inventor: str
    patent_title: str
    assignee: str | None = None
    grant_title: str | None = None
    company: str | None = None


class TechnologyLinkageSummary(BaseModel):
    papers: int
    patents: int
    grants: int
    researchers: int
    inventors: int
    companies: int
    commercialization_stage: str


class TechnologyLinkageOut(BaseModel):
    technology: TechnologyOut
    summary: TechnologyLinkageSummary
    top_inventors: list[LinkageEntity]
    top_companies: list[LinkageEntity]
    top_labs: list[LinkageEntity]
    chain_samples: list[LinkageChainSample]


class TechnologyGapItem(BaseModel):
    technology_slug: str
    technology_name: str
    papers: int = 0
    patents: int = 0
    grants: int = 0
    startups: int = 0


class PersonInsightItem(BaseModel):
    person_name: str
    affiliation: str | None = None
    paper_docs: int = 0
    patent_docs: int = 0


class CompanyInsightItem(BaseModel):
    organization: str
    patent_docs: int = 0
    non_patent_mentions: int = 0


class LinkageInsightsOut(BaseModel):
    technologies_lab_to_commercialization: list[TechnologyGapItem]
    professors_labs_with_patentable_work: list[PersonInsightItem]
    quiet_patent_filers: list[CompanyInsightItem]
    grant_rich_startup_poor_areas: list[TechnologyGapItem]
    patent_rich_low_academic_areas: list[TechnologyGapItem]


# ----- Markets -----


class HeadlineItem(BaseModel):
    title: str
    url: str | None = None
    published_at: date | None = None
    doc_type: str
    technologies: list[str] = Field(default_factory=list)


class MarketRegionOut(BaseModel):
    region: str
    market_tier: str
    counts_by_doc_type: dict[str, int]
    top_technologies: list[str]
    headlines: list[HeadlineItem]


class MarketHeadlinesOut(BaseModel):
    major_markets: list[MarketRegionOut]
    minor_markets: list[MarketRegionOut]


class SectorCapitalItem(BaseModel):
    sector: str
    documents: int
    papers: int
    patents: int
    grants: int
    company_presence: int
    funding_usd: float
    avg_trend_score: float
    capital_attractiveness: float
    wealth_thesis: str


class RegionalCapitalItem(BaseModel):
    region: str
    market_tier: str
    sector: str
    document_signals: int
    company_presence: int
    funding_usd: float
    capital_attractiveness: float
    wealth_thesis: str


class MarketCapitalMapOut(BaseModel):
    majority_sectors: list[SectorCapitalItem]
    major_market_hotspots: list[RegionalCapitalItem]
    minor_market_hotspots: list[RegionalCapitalItem]
