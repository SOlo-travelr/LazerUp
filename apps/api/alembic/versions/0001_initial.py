"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-01

Creates the full MVP schema from docs/DATABASE_SCHEMA.md using raw SQL so that
pgvector, pg_trgm, HNSW indexes and recursive-graph tables are created exactly
as designed.
"""
from collections.abc import Sequence

import os

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Vector size follows the configured embedding model (e.g. nomic-embed-text=768,
# bge-m3=1024, text-embedding-3-large=1536). Stays within pgvector's HNSW limit.
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.execute(
        """
        CREATE TABLE source (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name        TEXT NOT NULL,
            kind        TEXT NOT NULL,
            base_url    TEXT,
            config      JSONB NOT NULL DEFAULT '{}',
            last_run_at TIMESTAMPTZ,
            watermark   TEXT,
            enabled     BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE document (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            source_id    UUID NOT NULL REFERENCES source(id),
            doc_type     TEXT NOT NULL,
            external_id  TEXT,
            content_hash TEXT NOT NULL,
            title        TEXT NOT NULL,
            abstract     TEXT,
            body         TEXT,
            url          TEXT,
            published_at DATE,
            raw_s3_key   TEXT,
            metadata     JSONB NOT NULL DEFAULT '{}',
            extracted    JSONB,
            language     TEXT DEFAULT 'en',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_document_source_external UNIQUE (source_id, external_id),
            CONSTRAINT uq_document_content_hash UNIQUE (content_hash)
        );
        CREATE INDEX idx_document_type_date  ON document (doc_type, published_at DESC);
        CREATE INDEX idx_document_title_trgm ON document USING gin (title gin_trgm_ops);
        CREATE INDEX idx_document_metadata   ON document USING gin (metadata);
        CREATE INDEX idx_document_fts ON document
            USING gin (to_tsvector('english', coalesce(title,'')||' '||coalesce(abstract,'')));

        CREATE TABLE document_embedding (
            document_id UUID PRIMARY KEY REFERENCES document(id) ON DELETE CASCADE,
            model       TEXT NOT NULL DEFAULT 'text-embedding-3-large',
            embedding   vector("""
        + str(EMBEDDING_DIM)
        + """) NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        -- Dim stays within pgvector's HNSW limit (<=2000), enabling an
        -- approximate-nearest-neighbor index for fast semantic search.
        CREATE INDEX idx_doc_embedding_hnsw ON document_embedding
            USING hnsw (embedding vector_cosine_ops);

        CREATE TABLE technology (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            slug        TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            parent_id   UUID REFERENCES technology(id),
            aliases     TEXT[] NOT NULL DEFAULT '{}',
            description TEXT,
            embedding   vector("""
        + str(EMBEDDING_DIM)
        + """)
        );

        CREATE TABLE organization (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name         TEXT NOT NULL,
            org_type     TEXT,
            country      TEXT,
            homepage     TEXT,
            canonical_id UUID REFERENCES organization(id),
            metadata     JSONB NOT NULL DEFAULT '{}',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_org_name_trgm ON organization USING gin (name gin_trgm_ops);

        CREATE TABLE person (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            full_name   TEXT NOT NULL,
            orcid       TEXT,
            affiliation TEXT,
            metadata    JSONB NOT NULL DEFAULT '{}'
        );

        CREATE TABLE patent (
            document_id   UUID PRIMARY KEY REFERENCES document(id) ON DELETE CASCADE,
            patent_number TEXT,
            assignee_org  UUID REFERENCES organization(id),
            filing_date   DATE,
            grant_date    DATE,
            cpc_codes     TEXT[]
        );

        CREATE TABLE grant_award (
            document_id UUID PRIMARY KEY REFERENCES document(id) ON DELETE CASCADE,
            program     TEXT,
            amount_usd  NUMERIC(14,2),
            awardee_org UUID REFERENCES organization(id),
            start_date  DATE,
            end_date    DATE
        );

        CREATE TABLE funding_event (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_id  UUID REFERENCES document(id) ON DELETE CASCADE,
            org_id       UUID REFERENCES organization(id),
            round        TEXT,
            amount_usd   NUMERIC(14,2),
            announced_at DATE,
            investors    TEXT[]
        );

        CREATE TABLE document_technology (
            document_id   UUID REFERENCES document(id) ON DELETE CASCADE,
            technology_id UUID REFERENCES technology(id) ON DELETE CASCADE,
            confidence    REAL NOT NULL DEFAULT 1.0,
            PRIMARY KEY (document_id, technology_id)
        );
        CREATE TABLE document_organization (
            document_id     UUID REFERENCES document(id) ON DELETE CASCADE,
            organization_id UUID REFERENCES organization(id) ON DELETE CASCADE,
            role            TEXT,
            PRIMARY KEY (document_id, organization_id, role)
        );
        CREATE TABLE document_author (
            document_id UUID REFERENCES document(id) ON DELETE CASCADE,
            person_id   UUID REFERENCES person(id) ON DELETE CASCADE,
            position    INT,
            PRIMARY KEY (document_id, person_id)
        );

        CREATE TABLE graph_edge (
            id        BIGSERIAL PRIMARY KEY,
            src_type  TEXT NOT NULL,
            src_id    UUID NOT NULL,
            edge_type TEXT NOT NULL,
            dst_type  TEXT NOT NULL,
            dst_id    UUID NOT NULL,
            weight    REAL NOT NULL DEFAULT 1.0,
            metadata  JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_graph_edge UNIQUE (src_type, src_id, edge_type, dst_type, dst_id)
        );
        CREATE INDEX idx_edge_src ON graph_edge (src_type, src_id, edge_type);
        CREATE INDEX idx_edge_dst ON graph_edge (dst_type, dst_id, edge_type);

        CREATE TABLE trend_score (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            technology_id UUID REFERENCES technology(id),
            window_start  DATE NOT NULL,
            window_end    DATE NOT NULL,
            paper_growth     REAL,
            patent_growth    REAL,
            funding_momentum REAL,
            grant_momentum   REAL,
            composite_score  REAL NOT NULL,
            rank          INT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_trend UNIQUE (technology_id, window_end)
        );

        CREATE TABLE opportunity (
            id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title          TEXT NOT NULL,
            thesis         TEXT NOT NULL,
            technology_id  UUID REFERENCES technology(id),
            evidence       JSONB NOT NULL,
            market         TEXT,
            technical_risk TEXT,
            commercial_potential TEXT,
            confidence     REAL NOT NULL,
            score          REAL NOT NULL,
            status         TEXT DEFAULT 'active',
            generated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE white_space (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            technology_id     UUID REFERENCES technology(id),
            research_activity REAL,
            funding_present   REAL,
            startup_density   REAL,
            whitespace_score  REAL NOT NULL,
            rationale         TEXT,
            detected_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE bottleneck (
            id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            technology_id     UUID REFERENCES technology(id),
            problem_statement TEXT NOT NULL,
            frequency         INT,
            supporting_docs   UUID[],
            severity          REAL,
            detected_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE app_user (
            id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email      CITEXT UNIQUE NOT NULL,
            role       TEXT NOT NULL DEFAULT 'member',
            org_name   TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE founder_profile (
            id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id        UUID REFERENCES app_user(id) ON DELETE CASCADE,
            education      JSONB,
            skills         TEXT[] NOT NULL DEFAULT '{}',
            experience     JSONB,
            research_areas TEXT[] NOT NULL DEFAULT '{}',
            embedding      vector("""
        + str(EMBEDDING_DIM)
        + """),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE founder_fit (
            id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            profile_id     UUID REFERENCES founder_profile(id) ON DELETE CASCADE,
            opportunity_id UUID REFERENCES opportunity(id) ON DELETE CASCADE,
            fit_score      REAL NOT NULL,
            rationale      TEXT,
            skill_overlap  JSONB,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_founder_fit UNIQUE (profile_id, opportunity_id)
        );

        CREATE TABLE weekly_report (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            week_start   DATE NOT NULL UNIQUE,
            payload      JSONB NOT NULL,
            s3_pdf_key   TEXT,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS weekly_report, founder_fit, founder_profile, app_user,
            bottleneck, white_space, opportunity, trend_score, graph_edge,
            document_author, document_organization, document_technology,
            funding_event, grant_award, patent, person, organization,
            document_embedding, document, technology, source CASCADE;
        """
    )
