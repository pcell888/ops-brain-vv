"""租户注册表数据访问 — tenant_registries 表。"""

from __future__ import annotations

import json
import logging

from psycopg.rows import dict_row

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def get_tenant_row(tenant_id: str) -> dict | None:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, tenant_name, industry_code, industry_name, config, created_at, updated_at "
                    "FROM tenant_registries WHERE tenant_id = %s AND status = 1",
                    (tenant_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        raise AppError("查询租户失败", tenant_id=tenant_id) from e


async def list_active_tenants() -> list[dict]:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, tenant_name, industry_code, industry_name, config, created_at, updated_at "
                    "FROM tenant_registries WHERE status = 1 "
                    "ORDER BY created_at DESC"
                )
                return await cur.fetchall()
    except Exception as e:
        raise AppError("查询企业列表失败") from e


async def get_tenant_config_row(tenant_id: str) -> dict | None:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, config FROM tenant_registries WHERE tenant_id = %s",
                    (tenant_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        raise AppError("查询租户配置失败", tenant_id=tenant_id) from e


async def upsert_tenant(
    tenant_id: str,
    tenant_name: str,
    api_base_url: str,
    industry_code: str | None,
    industry_name: str | None,
    config: dict,
) -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO tenant_registries "
                    "(tenant_id, tenant_name, api_base_url, auth_type, auth_credential, "
                    "industry_code, industry_name, status, config) "
                    "VALUES (%s, %s, %s, 'token', 'pending', %s, %s, 1, %s::jsonb) "
                    "ON CONFLICT (tenant_id) DO UPDATE SET "
                    "tenant_name = EXCLUDED.tenant_name, "
                    "api_base_url = EXCLUDED.api_base_url, "
                    "industry_code = COALESCE(EXCLUDED.industry_code, tenant_registries.industry_code), "
                    "industry_name = COALESCE(EXCLUDED.industry_name, tenant_registries.industry_name), "
                    "status = 1, "
                    "config = EXCLUDED.config, "
                    "updated_at = NOW()",
                    (
                        tenant_id,
                        tenant_name,
                        api_base_url,
                        industry_code,
                        industry_name,
                        json.dumps(config, ensure_ascii=False),
                    ),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("upsert 租户失败", tenant_id=tenant_id) from e
