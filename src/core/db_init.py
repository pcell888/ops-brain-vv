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
INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code, status)
VALUES ('wlwq_local', 'wlwq 本地模拟', 'http://localhost:8200', 'token', 'mock', 'retail_general', 1)
ON CONFLICT (tenant_id) DO NOTHING;
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
