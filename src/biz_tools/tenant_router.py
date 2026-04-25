"""
租户路由器 — 根据 tenant_id 解析出目标企业的 API 地址和鉴权信息。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx
import psycopg.rows
import redis.asyncio as aioredis

from src.core.config import get_settings
from src.core.db_pool import get_conn
from src.biz_tools.biz_constants import BIZ_MOCK_TENANT_ID, is_biz_mock_tenant

logger = logging.getLogger(__name__)


PLATFORM_TENANT_ID = "__platform__"


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


class TenantRouter:
    def __init__(self, pg_uri: str | None = None, redis_url: str | None = None):
        settings = get_settings()
        self._redis_url = redis_url or settings.redis_url
        self._redis: aioredis.Redis | None = None
        self._http_clients: dict[str, httpx.AsyncClient] = {}

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def _resolve_platform_tenant_from_config(self) -> TenantContext:
        settings = get_settings()
        base = (settings.platform_center_api_base or "").strip().rstrip("/")
        if not base:
            raise TenantNotFoundError(
                "未配置 PLATFORM_CENTER_API_BASE：中台已不从 tenant_registries 读取，请在 .env 中设置该地址"
            )
        auth_type = (settings.platform_center_auth_type or "token").strip() or "token"
        auth_headers = self._build_auth_headers(auth_type, settings.platform_center_auth_credential or "")
        return TenantContext(
            tenant_id=PLATFORM_TENANT_ID,
            tenant_name="平台中台",
            api_base_url=base,
            auth_headers=auth_headers,
            industry_code=None,
            config={},
        )

    async def resolve(self, tenant_id: str) -> TenantContext:
        if tenant_id == PLATFORM_TENANT_ID:
            return self._resolve_platform_tenant_from_config()
        if is_biz_mock_tenant(tenant_id):
            return TenantContext(
                tenant_id=BIZ_MOCK_TENANT_ID,
                tenant_name="本地业务模拟",
                api_base_url="http://biz-mock.internal",
                auth_headers={},
                industry_code="retail_general",
                config={},
            )

        settings = get_settings()
        use_redis_cache = settings.tenant_cache_ttl > 0

        if use_redis_cache:
            rd = await self._get_redis()
            cache_key = f"tenant:{tenant_id}"
            cached = await rd.hgetall(cache_key)
            if cached and "api_base_url" in cached:
                logger.debug(
                    "租户解析命中缓存: tenant_id=%s tenant_name=%s api_base_url=%s",
                    tenant_id,
                    cached.get("tenant_name"),
                    cached.get("api_base_url"),
                )
                return TenantContext(
                    tenant_id=cached["tenant_id"],
                    tenant_name=cached["tenant_name"],
                    api_base_url=cached["api_base_url"],
                    auth_headers=json.loads(cached.get("auth_headers", "{}")),
                    industry_code=cached.get("industry_code") or None,
                    config=json.loads(cached.get("config", "{}")),
                )

        logger.debug("租户解析查询数据库: tenant_id=%s", tenant_id)
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM tenant_registries WHERE tenant_id=%s AND status=1",
                    (tenant_id,),
                )
                row = await cur.fetchone()

        if not row:
            logger.error("租户不存在或已停用: tenant_id=%s", tenant_id)
            raise TenantNotFoundError(f"租户 {tenant_id} 不存在或已停用")

        auth_headers = self._build_auth_headers(row["auth_type"], row["auth_credential"])
        ctx = TenantContext(
            tenant_id=row["tenant_id"],
            tenant_name=row["tenant_name"],
            api_base_url=row["api_base_url"].rstrip("/"),
            auth_headers=auth_headers,
            industry_code=row.get("industry_code"),
            config=row.get("config") or {},
        )

        if use_redis_cache:
            rd = await self._get_redis()
            cache_key = f"tenant:{tenant_id}"
            mapping = {
                "tenant_id": ctx.tenant_id,
                "tenant_name": ctx.tenant_name,
                "api_base_url": ctx.api_base_url,
                "auth_headers": json.dumps(ctx.auth_headers),
                "industry_code": ctx.industry_code or "",
                "config": json.dumps(ctx.config),
            }
            await rd.hset(cache_key, mapping=mapping)
            await rd.expire(cache_key, settings.tenant_cache_ttl)
            logger.debug(
                "租户解析完成并写入 Redis: tenant_id=%s tenant_name=%s api_base_url=%s",
                tenant_id,
                ctx.tenant_name,
                ctx.api_base_url,
            )
        else:
            logger.debug(
                "租户解析完成(无 Redis 缓存): tenant_id=%s api_base_url=%s",
                tenant_id,
                ctx.api_base_url,
            )
        return ctx

    async def get_platform_api_auth_headers(self, enterprise_tenant_id: str) -> dict[str, str]:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT auth_type, auth_credential, platform_auth_credential "
                    "FROM tenant_registries WHERE tenant_id=%s AND status=1",
                    (enterprise_tenant_id,),
                )
                row = await cur.fetchone()
        if not row:
            logger.error("租户不存在或已停用: tenant_id=%s（中台鉴权）", enterprise_tenant_id)
            raise TenantNotFoundError(f"租户 {enterprise_tenant_id} 不存在或已停用")
        cred = (row.get("platform_auth_credential") or "").strip()
        if not cred:
            cred = row["auth_credential"]
        return self._build_auth_headers(row["auth_type"], cred)

    async def get_client(self, tenant_id: str, ctx: TenantContext | None = None) -> httpx.AsyncClient:
        if ctx is None:
            ctx = await self.resolve(tenant_id)
        base = ctx.api_base_url.rstrip("/")
        existing = self._http_clients.get(tenant_id)
        if existing is not None:
            existing_base = str(existing.base_url).rstrip("/")
            if existing_base != base:
                logger.debug("租户 base_url 变更，重建 HTTP 客户端: tenant_id=%s", tenant_id)
                await existing.aclose()
                del self._http_clients[tenant_id]
        if tenant_id not in self._http_clients:
            logger.debug("创建新的HTTP客户端: tenant_id=%s base_url=%s", tenant_id, base)
            self._http_clients[tenant_id] = httpx.AsyncClient(
                base_url=base,
                headers={"Accept-Encoding": "identity"},
                timeout=30.0,
                trust_env=False,
            )
        else:
            logger.debug("复用已有HTTP客户端: tenant_id=%s", tenant_id)
        return self._http_clients[tenant_id]

    async def get_platform_client(self) -> httpx.AsyncClient:
        return await self.get_client(PLATFORM_TENANT_ID)

    async def get_tenant_basic_info(self, tenant_id: str) -> tuple[str, str]:
        ctx = await self.resolve(tenant_id)
        return ctx.tenant_name, (ctx.industry_code or "")

    def _build_auth_headers(self, auth_type: str, credential: str) -> dict:
        if auth_type == "token":
            return {"Authorization": credential}
        elif auth_type == "hmac":
            return {"X-Service-Signature": credential}
        return {}

    async def close(self):
        for client in self._http_clients.values():
            await client.aclose()
        self._http_clients.clear()
        if self._redis:
            await self._redis.aclose()
            self._redis = None
