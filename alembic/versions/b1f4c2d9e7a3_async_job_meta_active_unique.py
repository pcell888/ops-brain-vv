"""async_job_meta_active_unique

Revision ID: b1f4c2d9e7a3
Revises: 9d3b6e2c4f11
Create Date: 2026-04-14
"""

from alembic import op

revision = "b1f4c2d9e7a3"
down_revision = "9d3b6e2c4f11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_async_job_meta_thread_active
            ON ai_async_job_meta (thread_id)
         WHERE status IN ('queued', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_ai_async_job_meta_thread_active")

