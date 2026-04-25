"""请求 token 同步依赖：自动识别租户并回写 tenant_registries。"""

from __future__ import annotations

import logging

from fastapi import Request

from src.core.config import get_settings
from src.core.db_pool import get_conn
from src.core.redis_client import get_redis

logger = logging.getLogger(__name__)


def normalize_token_header(value: str | None) -> str | None:
    token = (value or "").strip()
    return token or None


def resolve_biz_auth_token(token_header: str | None, body_token: str | None) -> str | None:
    # 业务侧 token 约定：请求头 Token 优先，其次请求体 auth_token。
    return normalize_token_header(token_header) or normalize_token_header(body_token)


def _read_tenant_from_mapping(data: dict | None) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("tenant_id", "enterprise_id", "tenantId", "enterpriseId"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def _extract_tenant_id_from_request(request: Request) -> str | None:
    for source in (request.path_params, request.query_params):
        tenant_id = _read_tenant_from_mapping(dict(source))
        if tenant_id:
            return tenant_id

    if request.method.upper() in {"POST", "PUT", "PATCH"}:
        ctype = (request.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                payload = await request.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                tenant_id = _read_tenant_from_mapping(payload)
                if tenant_id:
                    return tenant_id
    return None


async def _extract_body_auth_token(request: Request) -> str | None:
    if request.method.upper() not in {"POST", "PUT", "PATCH"}:
        return None
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/json" not in ctype:
        return None
    try:
        payload = await request.json()
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("auth_token")
    return value.strip() if isinstance(value, str) and value.strip() else None


async def sync_runtime_tokens(tenant_id: str, biz_token: str | None, platform_token: str | None) -> None:
    biz_token = normalize_token_header(biz_token)
    platform_token = normalize_token_header(platform_token)
    if not biz_token and not platform_token:
        return

    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE tenant_registries
                    SET
                        auth_credential = COALESCE(%s, auth_credential),
                        platform_auth_credential = COALESCE(%s, platform_auth_credential),
                        updated_at = NOW()
                    WHERE tenant_id = %s
                    """,
                    (biz_token, platform_token, tenant_id),
                )
            await conn.commit()

        settings = get_settings()
        if settings.tenant_cache_ttl > 0:
            rd = await get_redis()
            keys = [f"tenant:{tenant_id}"]
            await rd.delete(*keys)
    except Exception as e:
        logger.warning("同步请求 token 到租户表失败 tenant_id=%s: %s", tenant_id, e)


async def sync_request_tokens_dependency(request: Request) -> None:
    """统一 token 同步依赖：挂到 router dependencies 后自动执行。"""
    tenant_id = await _extract_tenant_id_from_request(request)
    header_biz_token = normalize_token_header(request.headers.get("Token"))
    body_auth_token = await _extract_body_auth_token(request)
    platform_token = normalize_token_header(request.headers.get("Authorization"))
    biz_token = resolve_biz_auth_token(header_biz_token, body_auth_token)

    request.state.tenant_id_from_request = tenant_id
    request.state.biz_token = biz_token
    request.state.platform_token = platform_token

    if tenant_id:
        await sync_runtime_tokens(tenant_id, biz_token, platform_token)
