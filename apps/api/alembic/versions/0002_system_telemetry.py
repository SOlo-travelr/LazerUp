"""system telemetry and activity logging

Revision ID: 0002_system_telemetry
Revises: 0001
Create Date: 2026-05-31
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002_system_telemetry"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_event (
            id          BIGSERIAL PRIMARY KEY,
            component   TEXT NOT NULL,
            phase       TEXT NOT NULL,
            status      TEXT NOT NULL,
            message     TEXT,
            payload     JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_system_event_component_time
            ON system_event (component, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_system_event_status_time
            ON system_event (status, created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS system_event CASCADE;")
