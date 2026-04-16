"""ai_pending_review.review_due_date -> timestamptz (分钟级到期)

Revision ID: a7c3e2b91d4f
Revises: b1f4c2d9e7a3
Create Date: 2026-04-16
"""

from alembic import op

revision = "a7c3e2b91d4f"
down_revision = "b1f4c2d9e7a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ai_pending_review
        ALTER COLUMN review_due_date TYPE TIMESTAMP WITH TIME ZONE
        USING (review_due_date::timestamp AT TIME ZONE 'Asia/Shanghai');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE ai_pending_review
        ALTER COLUMN review_due_date TYPE DATE
        USING ((review_due_date AT TIME ZONE 'Asia/Shanghai')::date);
        """
    )
