"""应用用到的 PostgreSQL 表初始化（无 Alembic，按需执行）。"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from psycopg import AsyncConnection

from src.core.config import get_settings

logger = logging.getLogger(__name__)


def _uri_to_conninfo(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme not in ("postgresql", "postgres", "postgresql+asyncpg"):
        return uri
    parts = []
    if parsed.hostname:
        parts.append(f"host={parsed.hostname}")
    if parsed.port:
        parts.append(f"port={parsed.port}")
    if parsed.path and parsed.path != "/":
        parts.append(f"dbname={parsed.path.lstrip('/')}")
    if parsed.username:
        parts.append(f"user={parsed.username}")
    if parsed.password:
        parts.append(f"password={parsed.password}")
    return " ".join(parts)


TENANT_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS tenant_registry (
    tenant_id       VARCHAR(32) PRIMARY KEY,
    tenant_name     VARCHAR(128) NOT NULL,
    api_base_url    VARCHAR(256) NOT NULL,
    auth_type       VARCHAR(16) DEFAULT 'token',
    auth_credential TEXT NOT NULL,
    industry_code   VARCHAR(32),
    status          SMALLINT DEFAULT 1,
    config          JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
"""

SEED_PLATFORM = """
INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, status)
VALUES ('__platform__', '平台中台', 'https://platform-center.wlwq.com/api', 'token', 'mock', 1)
ON CONFLICT (tenant_id) DO NOTHING;
"""

SEED_WLWQ_LOCAL = """
INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code, status, config)
VALUES ('wlwq_local', 'wlwq 本地模拟', 'http://localhost:8200', 'token', 'mock', 'retail_general', 1,
        '{"diagnosis_trigger_mode": "manual", "analysis_period_days": 30, "stores": [{"store_id": "st_001", "store_name": "AI示范店"}]}')
ON CONFLICT (tenant_id) DO NOTHING;
"""

AI_DIAGNOSIS_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS ai_diagnosis_report (
    id           BIGSERIAL PRIMARY KEY,
    thread_id    VARCHAR(128) NOT NULL UNIQUE,
    tenant_id    VARCHAR(32)  NOT NULL,
    store_id     VARCHAR(32)  NOT NULL,
    trigger_type VARCHAR(32)  NOT NULL DEFAULT 'manual',
    report       JSONB       NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_report_tenant_store ON ai_diagnosis_report (tenant_id, store_id);
CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_report_created_at ON ai_diagnosis_report (created_at DESC);
"""

# 旧库为 timestamp without time zone：按中国墙钟解读后存为 timestamptz（内部 UTC）
_MIGRATE_AI_DIAGNOSIS_REPORT_CREATED_AT = """
DO $migrate$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_type t ON t.oid = a.atttypid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'ai_diagnosis_report'
      AND a.attname = 'created_at'
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND t.typname = 'timestamp'
  ) THEN
    ALTER TABLE public.ai_diagnosis_report
      ALTER COLUMN created_at TYPE timestamptz
      USING (CASE WHEN created_at IS NULL THEN NULL ELSE created_at AT TIME ZONE 'Asia/Shanghai' END);
  END IF;
END
$migrate$;
"""

AI_PUSH_LOG_DDL = """
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
);
CREATE INDEX IF NOT EXISTS ix_ai_push_log_thread ON ai_push_log (thread_id);
CREATE INDEX IF NOT EXISTS ix_ai_push_log_tenant_store ON ai_push_log (tenant_id, store_id);
CREATE INDEX IF NOT EXISTS ix_ai_push_log_created_at ON ai_push_log (created_at DESC);
"""

AI_EXEC_TASK_DDL = """
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
    priority            VARCHAR(20),
    status              VARCHAR(20) DEFAULT 'pending',
    related_resources   JSONB DEFAULT '[]',
    created_at          TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_exec_task_thread ON ai_exec_task (thread_id);
CREATE INDEX IF NOT EXISTS ix_ai_exec_task_tenant_store ON ai_exec_task (tenant_id, store_id);
CREATE INDEX IF NOT EXISTS ix_ai_exec_task_plan ON ai_exec_task (plan_id);
CREATE INDEX IF NOT EXISTS ix_ai_exec_task_created_at ON ai_exec_task (created_at DESC);
"""

AI_EFFECT_TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS ai_effect_tracking (
    thread_id     VARCHAR(128) PRIMARY KEY,
    tenant_id     VARCHAR(32)  NOT NULL,
    store_id      VARCHAR(32)  NOT NULL,
    tracking_data JSONB        NOT NULL DEFAULT '{}',
    created_at    TIMESTAMP    DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_effect_tracking_tenant_store ON ai_effect_tracking (tenant_id, store_id);
"""

AI_PENDING_REVIEW_DDL = """
CREATE TABLE IF NOT EXISTS ai_pending_review (
    id              BIGSERIAL PRIMARY KEY,
    thread_id       VARCHAR(128) NOT NULL UNIQUE,
    tenant_id       VARCHAR(32)  NOT NULL,
    store_id        VARCHAR(32)  NOT NULL,
    review_due_date DATE         NOT NULL,
    status          VARCHAR(20)  DEFAULT 'pending',
    created_at      TIMESTAMP    DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_pending_review_due ON ai_pending_review (review_due_date) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS ix_ai_pending_review_tenant_store ON ai_pending_review (tenant_id, store_id);
"""

AI_EFFECT_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS ai_effect_snapshot (
    id           BIGSERIAL PRIMARY KEY,
    thread_id    VARCHAR(128) NOT NULL,
    tenant_id    VARCHAR(32)  NOT NULL,
    store_id     VARCHAR(32)  NOT NULL,
    snapshot_data JSONB       NOT NULL DEFAULT '{}',
    snapshot_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_effect_snapshot_thread ON ai_effect_snapshot (thread_id, snapshot_at);
"""

AI_SOLUTION_KNOWLEDGE_DDL = """
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
);
CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_indicators ON ai_solution_knowledge USING GIN (target_indicators);
CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_industry ON ai_solution_knowledge (industry_code);
CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_achievement ON ai_solution_knowledge (achievement_rate DESC);
CREATE INDEX IF NOT EXISTS ix_ai_solution_knowledge_tenant ON ai_solution_knowledge (tenant_id);
"""

AI_REVIEW_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS ai_review_report (
    thread_id  VARCHAR(128) PRIMARY KEY,
    tenant_id  VARCHAR(32)  NOT NULL,
    store_id   VARCHAR(32)  NOT NULL,
    report     JSONB        NOT NULL DEFAULT '{}',
    created_at TIMESTAMP   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_review_report_tenant_store ON ai_review_report (tenant_id, store_id);
"""


async def ensure_tenant_registry():
    """若 tenant_registry 不存在则建表并插入种子数据；启动时调用可避免首请求 ProgrammingError。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(TENANT_REGISTRY_DDL)
                await cur.execute(SEED_PLATFORM)
                await cur.execute(SEED_WLWQ_LOCAL)
            await conn.commit()
        logger.info("tenant_registry 表已就绪")
    except Exception as e:
        logger.warning("tenant_registry 初始化跳过（可手动执行 make init-db）: %s", e)


async def ensure_ai_diagnosis_report():
    """若 ai_diagnosis_report 不存在则建表；已存在且 created_at 为无时区 timestamp 时升级为 timestamptz。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(AI_DIAGNOSIS_REPORT_DDL)
                await cur.execute(_MIGRATE_AI_DIAGNOSIS_REPORT_CREATED_AT)
            await conn.commit()
        logger.info("ai_diagnosis_report 表已就绪")
    except Exception as e:
        logger.warning("ai_diagnosis_report 初始化跳过: %s", e)


async def ensure_ai_push_log():
    """若 ai_push_log 不存在则建表（诊断系统本地推送留存）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(AI_PUSH_LOG_DDL)
            await conn.commit()
        logger.info("ai_push_log 表已就绪")
    except Exception as e:
        logger.warning("ai_push_log 初始化跳过: %s", e)


async def ensure_ai_exec_task():
    """若 ai_exec_task 不存在则建表（诊断系统本地执行任务留存）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                for stmt in AI_EXEC_TASK_DDL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await cur.execute(stmt)
            await conn.commit()
        logger.info("ai_exec_task 表已就绪")
    except Exception as e:
        logger.warning("ai_exec_task 初始化跳过: %s", e)


async def ensure_ai_pending_review():
    """若 ai_pending_review 不存在则建表（待复盘调度记录）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                for stmt in AI_PENDING_REVIEW_DDL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await cur.execute(stmt)
            await conn.commit()
        logger.info("ai_pending_review 表已就绪")
    except Exception as e:
        logger.warning("ai_pending_review 初始化跳过: %s", e)


async def ensure_ai_solution_knowledge():
    """若 ai_solution_knowledge 不存在则建表（方案沉淀知识库）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                for stmt in AI_SOLUTION_KNOWLEDGE_DDL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await cur.execute(stmt)
            await conn.commit()
        logger.info("ai_solution_knowledge 表已就绪")
    except Exception as e:
        logger.warning("ai_solution_knowledge 初始化跳过: %s", e)


async def ensure_ai_effect_snapshot():
    """若 ai_effect_snapshot 不存在则建表（追踪期指标快照）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                for stmt in AI_EFFECT_SNAPSHOT_DDL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await cur.execute(stmt)
            await conn.commit()
        logger.info("ai_effect_snapshot 表已就绪")
    except Exception as e:
        logger.warning("ai_effect_snapshot 初始化跳过: %s", e)


async def ensure_ai_effect_tracking():
    """若 ai_effect_tracking 不存在则建表（效果追踪数据本地留存）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(AI_EFFECT_TRACKING_DDL)
            await conn.commit()
        logger.info("ai_effect_tracking 表已就绪")
    except Exception as e:
        logger.warning("ai_effect_tracking 初始化跳过: %s", e)


async def ensure_ai_review_report():
    """若 ai_review_report 不存在则建表（复盘报告本地留存）。"""
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    try:
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(AI_REVIEW_REPORT_DDL)
            await conn.commit()
        logger.info("ai_review_report 表已就绪")
    except Exception as e:
        logger.warning("ai_review_report 初始化跳过: %s", e)
