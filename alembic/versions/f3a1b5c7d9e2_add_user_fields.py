"""add user_id user_name to tenant_registries and assignee_user_name to exec_tasks

Also change exec_tasks.assignee_user_id from INTEGER to VARCHAR(64) to
match tenant_registries.user_id which is str type.

Revision ID: f3a1b5c7d9e2
Revises: 07fb8a665282
Create Date: 2026-04-28
"""

from alembic import op

revision = "f3a1b5c7d9e2"
down_revision = "07fb8a665282"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tenant_registries
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(64),
        ADD COLUMN IF NOT EXISTS user_name VARCHAR(128)
        """
    )
    op.execute(
        """
        ALTER TABLE exec_tasks
        ADD COLUMN IF NOT EXISTS assignee_user_name VARCHAR(128)
        """
    )
    op.execute(
        """
        ALTER TABLE exec_tasks
        ALTER COLUMN assignee_user_id TYPE VARCHAR(64)
        USING assignee_user_id::VARCHAR(64)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE exec_tasks
        ALTER COLUMN assignee_user_id TYPE INTEGER
        USING CASE WHEN assignee_user_id ~ '^\d+$' THEN assignee_user_id::INTEGER ELSE NULL END
        """
    )
    op.execute(
        """
        ALTER TABLE exec_tasks
        DROP COLUMN IF EXISTS assignee_user_name
        """
    )
    op.execute(
        """
        ALTER TABLE tenant_registries
        DROP COLUMN IF EXISTS user_name,
        DROP COLUMN IF EXISTS user_id
        """
    )