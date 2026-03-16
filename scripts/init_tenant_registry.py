"""在 PostgreSQL 中创建 tenant_registry 表并插入平台/本地 wlwq 租户（若表已存在则跳过）。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urllib.parse import urlparse
from psycopg import AsyncConnection


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


SQL_CREATE = """
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

SQL_INSERT_PLATFORM = """
INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, status)
VALUES ('__platform__', '平台中台', 'https://platform-center.wlwq.com/api', 'token', 'mock', 1)
ON CONFLICT (tenant_id) DO NOTHING;
"""

SQL_INSERT_WLWQ = """
INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code, status)
VALUES ('wlwq_local', 'wlwq 本地模拟', 'http://localhost:8200', 'token', 'mock', 'retail_general', 1)
ON CONFLICT (tenant_id) DO NOTHING;
"""

SQL_AI_DIAGNOSIS_REPORT = """
CREATE TABLE IF NOT EXISTS ai_diagnosis_report (
    id           BIGSERIAL PRIMARY KEY,
    thread_id    VARCHAR(128) NOT NULL UNIQUE,
    tenant_id    VARCHAR(32)  NOT NULL,
    store_id     VARCHAR(32)  NOT NULL,
    trigger_type VARCHAR(32)  NOT NULL DEFAULT 'manual',
    report       JSONB       NOT NULL,
    created_at   TIMESTAMP   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_report_tenant_store ON ai_diagnosis_report (tenant_id, store_id);
CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_report_created_at ON ai_diagnosis_report (created_at DESC);
"""


async def main():
    from src.core.config import get_settings
    settings = get_settings()
    conninfo = _uri_to_conninfo(settings.postgres_uri)
    async with await AsyncConnection.connect(conninfo) as conn:
        async with conn.cursor() as cur:
            await cur.execute(SQL_CREATE)
            await cur.execute(SQL_INSERT_PLATFORM)
            await cur.execute(SQL_INSERT_WLWQ)
            await cur.execute(SQL_AI_DIAGNOSIS_REPORT)
        await conn.commit()
    print("tenant_registry、ai_diagnosis_report 已就绪")


if __name__ == "__main__":
    asyncio.run(main())
