# API Design

FastAPI REST surface. JSON over HTTPS, JWT bearer auth, cursor pagination, OpenAPI auto-generated at `/docs`. Versioned under `/api/v1`.

## Conventions

- **Auth:** `Authorization: Bearer <jwt>`. Roles: `founder`, `vc`, `corp`, `admin`.
- **Pagination:** `?limit=20&cursor=<opaque>` → `{ items, next_cursor }`.
- **Errors:** RFC 7807 problem+json `{ type, title, status, detail }`.
- **Idempotency:** mutation endpoints accept `Idempotency-Key`.
- **Rate limits:** per-key token bucket; surfaced via `X-RateLimit-*` headers.

---

## 1. Search & retrieval

```http
POST /api/v1/search
```
Hybrid semantic + filter search across all document types.
```jsonc
// request
{
  "query": "solid-state battery startups",
  "doc_types": ["paper", "patent", "funding"],   // optional
  "filters": { "published_after": "2024-01-01", "technology": "solid-state-electrolyte" },
  "mode": "hybrid",                               // semantic | keyword | hybrid
  "limit": 20
}
// response
{
  "items": [
    { "id": "...", "doc_type": "funding", "title": "...", "score": 0.87,
      "snippet": "...", "technologies": ["solid-state-electrolyte"], "url": "..." }
  ],
  "next_cursor": "..."
}
```

```http
GET /api/v1/documents/{id}
GET /api/v1/documents/{id}/related        # graph neighbors (1–2 hops)
```

---

## 2. Trends

```http
GET /api/v1/trends?window=90d&category=chemistry&limit=20
GET /api/v1/trends/{technology_id}        # time series + component breakdown
```
```jsonc
// GET /api/v1/trends response item
{
  "technology": { "id": "...", "name": "Sulfide solid electrolyte", "slug": "sulfide-electrolyte" },
  "composite_score": 0.91,
  "components": { "paper_growth": 0.45, "patent_growth": 0.30, "funding_momentum": 0.80 },
  "rank": 3,
  "window": { "start": "2025-03-01", "end": "2025-05-31" }
}
```

---

## 3. Opportunities

```http
GET  /api/v1/opportunities?min_confidence=0.7&sort=score
GET  /api/v1/opportunities/{id}
POST /api/v1/opportunities/generate        # admin/on-demand regeneration
```
```jsonc
// opportunity brief response
{
  "id": "...",
  "title": "AI-based solid-state battery design platform",
  "thesis": "Few software providers serve a rapidly growing, well-funded SSB R&D space...",
  "evidence": { "paper_growth_pct": 45, "patents": 23, "invested_usd": 200000000, "software_providers": 4 },
  "market": "Battery startups",
  "technical_risk": "medium",
  "commercial_potential": "high",
  "confidence": 0.85,
  "score": 0.88,
  "supporting_documents": ["...", "..."]
}
```

---

## 4. White space & bottlenecks

```http
GET /api/v1/white-spaces?min_score=0.6
GET /api/v1/bottlenecks?technology={id}&sort=severity
```
```jsonc
// white-space item
{ "technology": "lithium-metal-anode-protection", "whitespace_score": 0.78,
  "research_activity": 0.82, "funding_present": 0.65, "startup_density": 0.12,
  "rationale": "High research + funding, very low startup density." }
```

---

## 5. Founder profile & fit

```http
POST /api/v1/founder/profile
GET  /api/v1/founder/profile
POST /api/v1/founder/fit                    # rank opportunities for current profile
```
```jsonc
// POST /api/v1/founder/profile request
{
  "education": [{ "degree": "PhD", "field": "Mechanical Engineering", "institution": "..." }],
  "skills": ["solid-state batteries", "COMSOL", "multiphysics simulation",
             "fracture mechanics", "HPC", "AI/ML"],
  "experience": [{ "title": "Research Scientist", "years": 4 }],
  "research_areas": ["solid-state batteries", "interface mechanics"]
}
// POST /api/v1/founder/fit response
{
  "items": [
    { "opportunity_id": "...", "title": "AI-based solid-state battery design platform",
      "fit_score": 0.92,
      "rationale": "Direct overlap: SSB domain + COMSOL/multiphysics + AI/ML for design automation.",
      "skill_overlap": { "matched": ["solid-state batteries","COMSOL","AI/ML"], "gaps": ["go-to-market"] } }
  ]
}
```

---

## 6. Reports

```http
GET /api/v1/reports/weekly/latest
GET /api/v1/reports/weekly/{week_start}     # e.g. 2026-05-25
GET /api/v1/reports/weekly/{week_start}/pdf
```
```jsonc
{
  "week_start": "2026-05-25",
  "top_technologies": [ ... ],
  "top_grants": [ ... ],
  "top_startups": [ ... ],
  "top_patents": [ ... ],
  "top_opportunities": [ ... ]
}
```

---

## 7. Admin / pipeline ops

```http
GET  /api/v1/admin/sources
POST /api/v1/admin/sources/{id}/run         # trigger connector
GET  /api/v1/admin/ingestion/runs           # status, dedup rate, costs
POST /api/v1/admin/analytics/recompute      # trends/opps/whitespace
```

---

## 8. RAG / ask endpoint (synthesis)

```http
POST /api/v1/ask
```
Natural-language Q&A grounded in the corpus (citations returned).
```jsonc
// request
{ "question": "What technical bottlenecks remain unsolved in sulfide electrolytes?" }
// response
{
  "answer": "Recurring unsolved challenges are (1) air/moisture sensitivity ...",
  "citations": [ { "document_id": "...", "title": "...", "url": "..." } ],
  "confidence": 0.81
}
```

OpenAPI/Swagger served at `/docs`, ReDoc at `/redoc`, schema at `/api/v1/openapi.json`.
