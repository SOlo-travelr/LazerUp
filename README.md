# Battery Opportunity Scanner (BOS)

> Continuously monitors the global battery ecosystem and surfaces emerging startup opportunities, technology white spaces, commercialization gaps, funding trends, and technical bottlenecks **before they become obvious**.

## What it does

Instead of dumping hundreds of papers, patents, grants, and news articles on the user, BOS **synthesizes** signals across the ecosystem and answers:

- What battery technologies are gaining momentum?
- Where is funding flowing?
- What technical bottlenecks remain unsolved?
- Which areas are overcrowded vs. underserved (white space)?
- What startup opportunities are emerging?
- Which opportunities fit *this* founder's expertise?

## Target users

Battery startup founders · VC firms · Corporate strategy teams · National labs · University TTOs · Researchers · Government agencies.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, diagrams, stack justification, scaling |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | PostgreSQL + pgvector schema, graph model |
| [docs/API_DESIGN.md](docs/API_DESIGN.md) | REST API surface, auth, contracts |
| [docs/ALGORITHMS.md](docs/ALGORITHMS.md) | Trend scoring, opportunity detection, white space, founder fit |
| [docs/ROADMAP.md](docs/ROADMAP.md) | MVP roadmap, milestones, timeline, cost, deployment |
| [docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) | Repository layout |

## Stack at a glance

- **Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind · TanStack Query
- **Backend:** FastAPI · Python 3.12 · SQLAlchemy 2 · Pydantic v2
- **Data:** PostgreSQL 16 · pgvector · Redis · S3
- **Graph:** PostgreSQL adjacency tables for MVP → Neo4j when graph queries dominate (see ADR-001)
- **AI:** OpenAI embeddings + GPT-4o for RAG, synthesis, and structured extraction
- **Pipelines:** Celery + Celery Beat (daily ingestion DAGs)
- **Infra:** Docker · GitHub Actions · AWS (ECS Fargate, RDS, ElastiCache, S3)

## Quick start (target dev workflow)

```bash
docker compose up -d        # postgres+pgvector, redis, api, worker, web
make migrate                # alembic upgrade head
make seed                   # taxonomy + source registry
make ingest-once            # run all collectors a single time
open http://localhost:3000
```
