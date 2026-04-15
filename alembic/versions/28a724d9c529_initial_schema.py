"""initial_schema

Revision ID: 28a724d9c529
Create Date: 2026-04-14

基线迁移：对齐 db_init.py 中 ensure_* 创建的所有表和索引。
对已有库执行 `alembic stamp head` 即可跳过。
"""

from alembic import op

revision = "28a724d9c529"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenant_registry ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS tenant_registry (
        tenant_id       VARCHAR(32) PRIMARY KEY,
        tenant_name     VARCHAR(128) NOT NULL,
        api_base_url    VARCHAR(256) NOT NULL,
        auth_type       VARCHAR(16) DEFAULT 'token',
        auth_credential TEXT NOT NULL,
        platform_auth_credential TEXT,
        industry_code   VARCHAR(32),
        industry_name   VARCHAR(128),
        status          SMALLINT DEFAULT 1,
        config          JSONB DEFAULT '{}',
        created_at      TIMESTAMP DEFAULT NOW(),
        updated_at      TIMESTAMP DEFAULT NOW()
    )
    """)

    # ── ai_diagnosis_report ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_diagnosis_report (
        id           BIGSERIAL PRIMARY KEY,
        thread_id    VARCHAR(128) NOT NULL UNIQUE,
        tenant_id    VARCHAR(32)  NOT NULL,
        store_id     VARCHAR(32)  NOT NULL,
        trigger_type VARCHAR(32)  NOT NULL DEFAULT 'manual',
        report       JSONB       NOT NULL,
        plan_ids     JSONB       DEFAULT '[]'::jsonb,
        created_at   TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_report_tenant_store ON ai_diagnosis_report (tenant_id, store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_report_created_at ON ai_diagnosis_report (created_at DESC)")

    # ── ai_push_log ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_push_log (
        id           BIGSERIAL PRIMARY KEY,
        thread_id    VARCHAR(128) NOT NULL,
        tenant_id    VARCHAR(32)  NOT NULL,
        store_id     VARCHAR(32)  NOT NULL,
        kind         VARCHAR(32)  NOT NULL,
        message_type VARCHAR(64)  NOT NULL DEFAULT '',
        title        VARCHAR(500),
        content      TEXT,
        extra        JSONB DEFAULT '{}',
        created_at   TIMESTAMP DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_push_log_thread ON ai_push_log (thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_push_log_tenant_store ON ai_push_log (tenant_id, store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_push_log_created_at ON ai_push_log (created_at DESC)")

    # ── ai_exec_task ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_exec_task (
        task_id             VARCHAR(32) PRIMARY KEY,
        thread_id           VARCHAR(128) NOT NULL,
        tenant_id           VARCHAR(32)  NOT NULL,
        store_id            VARCHAR(32)  NOT NULL,
        plan_id             VARCHAR(32)  NOT NULL,
        task_name           VARCHAR(500),
        description         TEXT,
        assignee_user_id    INTEGER,
        assignee_account_id VARCHAR(32),
        assignee_dept_id    VARCHAR(32),
        deadline            VARCHAR(200),
        deadline_at         TIMESTAMPTZ,
        priority            VARCHAR(20),
        status              VARCHAR(20) DEFAULT 'pending',
        related_resources   JSONB DEFAULT '{}',
        created_at          TIMESTAMP DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_exec_task_thread ON ai_exec_task (thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_exec_task_tenant_store ON ai_exec_task (tenant_id, store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_exec_task_plan ON ai_exec_task (plan_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_exec_task_created_at ON ai_exec_task (created_at DESC)")

    # ── ai_effect_tracking ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_effect_tracking (
        thread_id     VARCHAR(128) PRIMARY KEY,
        tenant_id     VARCHAR(32)  NOT NULL,
        store_id      VARCHAR(32)  NOT NULL,
        tracking_data JSONB        NOT NULL DEFAULT '{}',
        created_at    TIMESTAMP    DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_effect_tracking_tenant_store ON ai_effect_tracking (tenant_id, store_id)")

    # ── ai_pending_review ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_pending_review (
        id              BIGSERIAL PRIMARY KEY,
        thread_id       VARCHAR(128) NOT NULL UNIQUE,
        tenant_id       VARCHAR(32)  NOT NULL,
        store_id        VARCHAR(32)  NOT NULL,
        review_due_date DATE         NOT NULL,
        status          VARCHAR(20)  DEFAULT 'pending',
        created_at      TIMESTAMP    DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_pending_review_due ON ai_pending_review (review_due_date) WHERE status = 'pending'")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_pending_review_tenant_store ON ai_pending_review (tenant_id, store_id)")

    # ── ai_effect_snapshot ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_effect_snapshot (
        id           BIGSERIAL PRIMARY KEY,
        thread_id    VARCHAR(128) NOT NULL,
        tenant_id    VARCHAR(32)  NOT NULL,
        store_id     VARCHAR(32)  NOT NULL,
        snapshot_data JSONB       NOT NULL DEFAULT '{}',
        snapshot_at  TIMESTAMP    NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_effect_snapshot_thread ON ai_effect_snapshot (thread_id, snapshot_at)")

    # ── ai_solution_knowledge ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_solution_knowledge (
        id              BIGSERIAL PRIMARY KEY,
        tenant_id       VARCHAR(32)  NOT NULL,
        store_id        VARCHAR(32)  NOT NULL,
        thread_id       VARCHAR(128) NOT NULL,
        plan_id         VARCHAR(32)  NOT NULL,
        plan_name       VARCHAR(500) NOT NULL,
        target_indicators TEXT[]      NOT NULL DEFAULT '{}',
        industry_code   VARCHAR(32),
        achievement_rate FLOAT       NOT NULL DEFAULT 0,
        indicator_changes JSONB      NOT NULL DEFAULT '[]',
        plan_detail     JSONB        NOT NULL DEFAULT '{}',
        lessons_learned JSONB        NOT NULL DEFAULT '[]',
        created_at      TIMESTAMP    DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_indicators ON ai_solution_knowledge USING GIN (target_indicators)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_industry ON ai_solution_knowledge (industry_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_achievement ON ai_solution_knowledge (achievement_rate DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_tenant ON ai_solution_knowledge (tenant_id)")

    # ── ai_review_report ──
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_review_report (
        thread_id  VARCHAR(128) PRIMARY KEY,
        tenant_id  VARCHAR(32)  NOT NULL,
        store_id   VARCHAR(32)  NOT NULL,
        report     JSONB        NOT NULL DEFAULT '{}',
        created_at TIMESTAMP   DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_review_report_tenant_store ON ai_review_report (tenant_id, store_id)")

    # ── 种子数据 ──
    op.execute("""
    INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code, status, config)
    VALUES ('wlwq_local', '本地业务模拟', 'http://biz-mock.internal', 'token', 'mock', 'retail_general', 1,
            '{"diagnosis_trigger_mode": "manual", "analysis_period_days": 30, "stores": [{"store_id": "st_001", "store_name": "AI示范店"}]}')
    ON CONFLICT (tenant_id) DO NOTHING
    """)


def downgrade() -> None:
    for table in (
        "ai_review_report",
        "ai_solution_knowledge",
        "ai_effect_snapshot",
        "ai_pending_review",
        "ai_effect_tracking",
        "ai_exec_task",
        "ai_push_log",
        "ai_diagnosis_report",
        "tenant_registry",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
