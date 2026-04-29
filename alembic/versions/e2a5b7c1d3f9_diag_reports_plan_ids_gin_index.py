"""diag_reports_plan_ids_gin_index

Revision ID: e2a5b7c1d3f9
Revises: b1f4c2d9e7a3
Create Date: 2026-04-28
"""

from alembic import op

revision = "e2a5b7c1d3f9"
down_revision = "b1f4c2d9e7a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.diag_reports') IS NOT NULL THEN
                CREATE INDEX IF NOT EXISTS ix_diag_reports_plan_ids
                    ON diag_reports USING GIN (plan_ids jsonb_path_ops);
            ELSIF to_regclass('public.ai_diagnosis_report') IS NOT NULL THEN
                CREATE INDEX IF NOT EXISTS ix_diag_reports_plan_ids
                    ON ai_diagnosis_report USING GIN (plan_ids jsonb_path_ops);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_diag_reports_plan_ids")