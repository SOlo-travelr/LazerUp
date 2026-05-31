# Repository / Folder Structure

Monorepo. `apps/` for deployables, `packages/` for shared code, `infra/` for IaC, `docs/` for design.

```
LazerUp/
├── README.md
├── docker-compose.yml
├── Makefile
├── .github/
│   └── workflows/
│       ├── ci.yml                 # lint, type-check, test, build
│       ├── deploy-staging.yml
│       └── deploy-prod.yml
│
├── apps/
│   ├── api/                       # FastAPI backend
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   ├── alembic/               # migrations
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/              # config, security, logging, deps
│   │   │   ├── db/                # session, base, models/
│   │   │   ├── schemas/           # Pydantic request/response
│   │   │   ├── api/v1/            # routers: search, trends, opportunities,
│   │   │   │                      #          whitespace, bottlenecks, founder,
│   │   │   │                      #          reports, ask, admin
│   │   │   ├── services/          # business logic
│   │   │   └── repositories/      # data-access layer
│   │   └── tests/
│   │
│   ├── worker/                    # Celery: ingestion + analytics
│   │   ├── Dockerfile
│   │   ├── celery_app.py
│   │   ├── beat_schedule.py
│   │   ├── connectors/            # one module per source
│   │   │   ├── base.py            # Connector interface
│   │   │   ├── papers/            # nature_energy, joule, ees, aem, acs,
│   │   │   │                      # semantic_scholar, arxiv, chemrxiv
│   │   │   ├── patents/           # google_patents, uspto_patentsview
│   │   │   ├── grants/            # doe, arpa_e, nsf, sbir_sttr
│   │   │   ├── funding/           # crunchbase, techcrunch, public
│   │   │   └── news/              # rss, company_announcements
│   │   ├── pipeline/              # dedup, extract, embed, tag, load
│   │   ├── analytics/            # trends, opportunities, whitespace,
│   │   │                         # bottlenecks, founder_fit, reports
│   │   └── tests/
│   │
│   └── web/                       # Next.js 14 frontend
│       ├── package.json
│       ├── Dockerfile
│       ├── next.config.js
│       ├── tailwind.config.ts
│       ├── app/                   # App Router
│       │   ├── (dashboard)/
│       │   │   ├── trends/
│       │   │   ├── opportunities/
│       │   │   ├── white-space/
│       │   │   ├── search/
│       │   │   ├── reports/
│       │   │   └── founder-fit/
│       │   └── layout.tsx
│       ├── components/
│       ├── lib/                   # api client, hooks (TanStack Query)
│       └── tests/
│
├── packages/
│   ├── shared-types/              # OpenAPI-generated TS types
│   ├── llm/                       # LLMProvider abstraction, prompts
│   └── taxonomy/                  # battery taxonomy seed data
│
├── infra/
│   ├── terraform/                 # vpc, rds, elasticache, ecs, alb, s3, cloudfront
│   └── scripts/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── DATABASE_SCHEMA.md
    ├── API_DESIGN.md
    ├── ALGORITHMS.md
    ├── FOLDER_STRUCTURE.md
    └── ROADMAP.md
```

## Connector contract

Every source implements the same interface so scheduling, retry, dedup, and metrics are uniform:

```python
class Connector(Protocol):
    name: str
    kind: Literal["paper", "patent", "grant", "funding", "news"]
    def fetch(self, since: datetime | str | None) -> Iterable[RawRecord]: ...
    def parse(self, raw: RawRecord) -> NormalizedDocument: ...
```

New source = new module implementing `Connector` + a row in the `source` registry. No pipeline changes required.
