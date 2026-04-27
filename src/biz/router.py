"""租户路由 — tenant_id → 连接信息"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import psycopg.rows

from src.core.db_pool import get_conn

logger = logging.getLogger(__name__)


class TenantNotFoundError(Exception):
    pass


@dataclass
class TenantContext:
    tenant_id: str
    tenant_name: str
    api_base_url: str
    auth_headers: dict
    industry_code: str | None
    config: dict = field(default_factory=dict)


def build_auth_headers(auth_type: str, credential: str) -> dict:
    if auth_type == "token":
        return {"Authorization": credential}
    if auth_type == "hmac":
        return {"X-Service-Signature": credential}
    return {}


class TenantRouter:
    """tenant_id → TenantContext"""
    
    async def resolve(self, tenant_id: str) -> TenantContext:
        from src.biz.biz_constants import is_mock_tenant
        from src.biz.biz_constants import MOCK_TENANT_ID

        if is_mock_tenant(tenant_id):
            return TenantContext(
                tenant_id=MOCK_TENANT_ID,
                tenant_name="本地业务模拟",
                api_base_url="http://biz-mock.internal",
                auth_headers={},
                industry_code="retail_general",
                config={},
            )

        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM tenant_registries WHERE tenant_id = %s AND status = 1",
                    (tenant_id,),
                )
                row = await cur.fetchone()

        if not row:
            raise TenantNotFoundError(f"租户 {tenant_id} 不存在或已停用")

        return TenantContext(
            tenant_id=row["tenant_id"],
            tenant_name=row["tenant_name"],
            api_base_url=row["api_base_url"].rstrip("/"),
            auth_headers=build_auth_headers(row["auth_type"], row["auth_credential"]),
            industry_code=row.get("industry_code"),
            config=row.get("config") or {},
        )
