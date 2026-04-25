"""diagnosis_session table

Revision ID: c8d1f3a5e9b2
Revises: b1f4c2d9e7a3
Create Date: 2026-04-25
"""

from alembic import op

revision = "c8d1f3a5e9b2"
down_revision = "a7c3e2b91d4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_diagnosis_session (
        thread_id           VARCHAR(128) PRIMARY KEY,
        tenant_id           VARCHAR(32)  NOT NULL,
        store_id            VARCHAR(32)  NOT NULL DEFAULT '',
        phase               VARCHAR(32)  NOT NULL DEFAULT 'collecting',
        state_json          JSONB        NOT NULL DEFAULT '{}',
        trigger_type        VARCHAR(32)  NOT NULL DEFAULT 'manual',
        triggered_by        VARCHAR(128),
        selected_dimensions JSONB,
        selected_indicators JSONB,
        auth_token          TEXT,
        created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_diagnosis_session_tenant ON ai_diagnosis_session (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_diagnosis_session_phase ON ai_diagnosis_session (phase)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_diagnosis_session_created_at ON ai_diagnosis_session (created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_diagnosis_session CASCADE")
