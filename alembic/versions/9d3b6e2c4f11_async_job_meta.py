"""async_job_meta

Revision ID: 9d3b6e2c4f11
Revises: 28a724d9c529
Create Date: 2026-04-14
"""

from alembic import op

revision = "9d3b6e2c4f11"
down_revision = "28a724d9c529"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_async_job_meta (
            id         BIGSERIAL PRIMARY KEY,
            job_id     VARCHAR(128) NOT NULL UNIQUE,
            thread_id  VARCHAR(128) NOT NULL,
            tenant_id  VARCHAR(32)  NOT NULL,
            job_kind   VARCHAR(32)  NOT NULL,
            status     VARCHAR(20)  NOT NULL,
            payload    JSONB        NOT NULL DEFAULT '{}'::jsonb,
            error      TEXT,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_async_job_meta_thread ON ai_async_job_meta (thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_async_job_meta_status ON ai_async_job_meta (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_async_job_meta_updated ON ai_async_job_meta (updated_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_async_job_meta CASCADE")

