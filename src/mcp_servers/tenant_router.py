"""
租户路由器 — 所有MCP Server共享。
根据 tenant_id 解析出目标企业的 API 地址和鉴权信息。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
import psycopg
import redis.asyncio as aioredis
from cryptography.fernet import Fernet

from src.core.config import get_settings

logger = logging.getLogger(__name__)


def _pg_uri_to_conninfo(uri: str) -> str:
    """postgresql:// 或 postgresql+asyncpg:// 转为 psycopg 可用的 conninfo（key=value）。"""
    uri = uri.strip()
    if len(uri) >= 2 and uri[0] == uri[-1] and uri[0] in ("'", '"'):
        uri = uri[1:-1].strip()
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
    """
    租户路由器 — 所有MCP Server共享。
    根据 tenant_id 解析出目标企业的 API 地址和鉴权信息。
    """

    def __init__(self, pg_uri: str | None = None, redis_url: str | None = None):
        settings = get_settings()
        raw = pg_uri or settings.postgres_uri
        self._pg_conninfo = _pg_uri_to_conninfo(raw)
        self._redis_url = redis_url or settings.redis_url
        self._encrypt_key = settings.credential_encrypt_key
        self._redis: aioredis.Redis | None = None
        self._http_clients: dict[str, httpx.AsyncClient] = {}

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def resolve(self, tenant_id: str) -> TenantContext:
        """解析租户上下文。tenant_cache_ttl>0 时优先 Redis，否则每次查 PostgreSQL。"""
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
        async with await psycopg.AsyncConnection.connect(self._pg_conninfo) as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM tenant_registry WHERE tenant_id=%s AND status=1",
                    (tenant_id,),
                )
                row = await cur.fetchone()

        if not row:
            logger.error("租户不存在或已停用: tenant_id=%s", tenant_id)
            raise TenantNotFoundError(f"租户 {tenant_id} 不存在或已停用")

        credential = row["auth_credential"]
        # 平台租户优先使用独立的平台鉴权字段，避免与业务端 token 混用。
        if tenant_id == PLATFORM_TENANT_ID and (row.get("platform_auth_credential") or "").strip():
            credential = row["platform_auth_credential"]
        auth_headers = self._build_auth_headers(row["auth_type"], credential)
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

    async def get_client(self, tenant_id: str, ctx: TenantContext | None = None) -> httpx.AsyncClient:
        """获取面向指定租户的 HTTP Client（连接池复用）。默认不在 client 上绑鉴权头，由 BizAPIClient 每请求注入。"""
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
                headers={},
                timeout=30.0,
            )
        else:
            logger.debug("复用已有HTTP客户端: tenant_id=%s", tenant_id)
        return self._http_clients[tenant_id]

    async def get_platform_client(self) -> httpx.AsyncClient:
        """获取平台中台的 HTTP Client（行业基准等公共数据）。"""
        return await self.get_client(PLATFORM_TENANT_ID)

    async def get_tenant_basic_info(self, tenant_id: str) -> tuple[str, str]:
        """返回租户基础信息 (tenant_name, industry_code)。"""
        ctx = await self.resolve(tenant_id)
        return ctx.tenant_name, (ctx.industry_code or "")

    def _build_auth_headers(self, auth_type: str, credential: str) -> dict:
        decrypted = self._decrypt(credential)
        if auth_type == "token":
            return {"Authorization": decrypted}
        elif auth_type == "hmac":
            return {"X-Service-Signature": decrypted}
        return {}

    def _decrypt(self, encrypted: str) -> str:
        if not self._encrypt_key:
            return encrypted
        try:
            f = Fernet(self._encrypt_key.encode())
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            logger.debug("解密失败，使用原始凭证（明文或密钥不匹配）")
            return encrypted

    async def close(self):
        for client in self._http_clients.values():
            await client.aclose()
        self._http_clients.clear()
        if self._redis:
            await self._redis.aclose()
            self._redis = None
