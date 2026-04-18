"""企业/租户注册表与中台同步业务逻辑（兼容层）。"""

from __future__ import annotations

import asyncio
import json
import logging

from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.datetime_cn import serialize_instant_cn
from src.core.db_pool import get_conn
from src.mcp_servers.biz_api_client import BizAPIClient, BizAPIError
from src.mcp_servers.tenant_router import TenantNotFoundError, TenantRouter
from src.core.tenant_config import (
    CONFIG_DEFAULTS,
    normalize_diagnosis_trigger_mode,
    normalize_tenant_config,
    update_tenant_config,
)

logger = logging.getLogger(__name__)

_platform_router = TenantRouter()
_platform_biz = BizAPIClient(_platform_router)


class EnterpriseServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class SyncEnterpriseBody(BaseModel):
    """生态 APP 同步企业：有则更新，无则创建。"""

    name: str = Field(default="", max_length=256)
    store_id: str | None = Field(default=None, max_length=64)
    industry: str | None = Field(default=None, max_length=64)
    scale: str | None = Field(default=None, pattern=r"^(small|medium|large|enterprise)$")
    team_size: int | None = Field(default=None, ge=1, le=100000)


async def _get_tenant_row(tenant_id: str) -> dict | None:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, tenant_name, industry_code, industry_name, config, created_at, updated_at "
                    "FROM tenant_registry WHERE tenant_id = %s AND status = 1",
                    (tenant_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        logger.warning("查询租户 %s 失败: %s", tenant_id, e)
        return None


def _row_to_enterprise(row: dict) -> dict:
    raw_config = row.get("config") or {}
    if isinstance(raw_config, str):
        raw_config = json.loads(raw_config)
    normalized_config = normalize_tenant_config(raw_config)

    return {
        "id": row["tenant_id"],
        "name": row.get("tenant_name") or row["tenant_id"],
        "industry": row.get("industry_code") or "general",
        "industry_name": row.get("industry_name"),
        "scale": normalized_config.get("scale"),
        "team_size": normalized_config.get("team_size"),
        "config": {
            "analysis_period_days": normalized_config.get("analysis_period_days", 30),
            "auto_diagnosis_frequency": _trigger_mode_to_frequency(
                normalized_config.get("diagnosis_trigger_mode", "manual")
            ),
            "solution_sort_strategy": normalized_config.get("solution_sort_strategy", "balanced"),
        },
        "stores": normalized_config.get("stores", []),
        "created_at": serialize_instant_cn(row["created_at"]) if row.get("created_at") else None,
        "updated_at": serialize_instant_cn(row["updated_at"]) if row.get("updated_at") else None,
    }


def _trigger_mode_to_frequency(mode: str) -> str:
    return normalize_diagnosis_trigger_mode(mode)


def _merge_sync_config(current: dict | str | None, body: SyncEnterpriseBody) -> dict:
    raw_config = current or {}
    if isinstance(raw_config, str):
        raw_config = json.loads(raw_config)

    config = normalize_tenant_config({**CONFIG_DEFAULTS, **raw_config})

    if body.scale is not None:
        config["scale"] = body.scale
    if body.team_size is not None:
        config["team_size"] = body.team_size
    if body.store_id is not None:
        stores = config.get("stores")
        if not isinstance(stores, list):
            stores = []
        matched = False
        normalized_stores = []
        for store in stores:
            if not isinstance(store, dict):
                continue
            if store.get("store_id") == body.store_id:
                matched = True
                normalized_stores.append(
                    {
                        "store_id": body.store_id,
                        "store_name": store.get("store_name") or "",
                    }
                )
            else:
                normalized_stores.append(store)
        if not matched:
            normalized_stores.append({"store_id": body.store_id, "store_name": ""})
        config["stores"] = normalized_stores

    return config


def _coerce_industry_code(val) -> str | None:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, int):
        return str(val)
    s = str(val).strip()
    return s or None


def _platform_enterprise_fields(payload: dict, fallback_name: str) -> dict:
    core = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    serve = core.get("serveUrl") or core.get("serve_url")
    if serve is None or not str(serve).strip():
        raise ValueError("中台 projectInfo 未返回 serveUrl")
    api_base_url = str(serve).strip().rstrip("/")
    raw_name = core.get("customerName") if core.get("customerName") is not None else core.get("customer_name")
    tenant_name = str(raw_name).strip() if raw_name is not None else ""
    if not tenant_name:
        tenant_name = fallback_name.strip()
    if not tenant_name:
        raise ValueError("中台未返回 customerName 且请求体 name 为空")
    industry_code = _coerce_industry_code(core.get("businessClassCode") or core.get("business_class_code"))
    in_raw = (
        core.get("businessClassName") if core.get("businessClassName") is not None else core.get("business_class_name")
    )
    industry_name = str(in_raw).strip() if in_raw is not None and str(in_raw).strip() else None
    return {
        "tenant_name": tenant_name,
        "api_base_url": api_base_url,
        "industry_code": industry_code,
        "industry_name": industry_name,
    }


async def _fetch_project_info_for_sync(enterprise_id: str, auth_override: str | None) -> dict:
    params = {"projectId": enterprise_id}
    ov = (auth_override or "").strip()
    if ov:
        return await _platform_biz.platform_get(
            "ai/customer/projectInfo",
            params,
            auth_authorization_override=ov,
        )
    try:
        return await _platform_biz.platform_get(
            "ai/customer/projectInfo",
            params,
            auth_tenant_id=enterprise_id,
        )
    except TenantNotFoundError:
        raise EnterpriseServiceError(
            401,
            "租户尚未入库，请携带 Authorization 请求中台以完成首次同步",
        ) from None


async def _invalidate_tenant_cache(tenant_id: str) -> None:
    settings = get_settings()
    if settings.tenant_cache_ttl <= 0:
        return
    try:
        import redis.asyncio as aioredis

        rd = aioredis.from_url(settings.redis_url, decode_responses=True)
        await rd.delete(f"tenant:{tenant_id}")
        await rd.aclose()
    except Exception as e:
        logger.debug("清理租户 Redis 缓存失败 tenant=%s: %s", tenant_id, e)


async def list_enterprises_compat() -> dict:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, tenant_name, industry_code, industry_name, config, created_at, updated_at "
                    "FROM tenant_registry WHERE status = 1 "
                    "ORDER BY created_at DESC"
                )
                rows = await cur.fetchall()
        enterprises = [_row_to_enterprise(r) for r in rows]
        return {"enterprises": enterprises, "total": len(enterprises)}
    except Exception as e:
        logger.exception("查询企业列表失败")
        raise EnterpriseServiceError(500, "查询企业列表失败，请稍后重试") from e


async def get_enterprise_compat(enterprise_id: str) -> dict:
    row = await _get_tenant_row(enterprise_id)
    if not row:
        raise EnterpriseServiceError(404, "企业不存在")
    return _row_to_enterprise(row)


async def sync_enterprise_compat(enterprise_id: str, body: SyncEnterpriseBody, auth_override: str | None) -> dict:
    created = False
    try:
        raw_info = await _fetch_project_info_for_sync(enterprise_id, auth_override)
        pf = _platform_enterprise_fields(raw_info, body.name)
    except EnterpriseServiceError:
        raise
    except ValueError as e:
        raise EnterpriseServiceError(400, str(e)) from e
    except BizAPIError as e:
        raise EnterpriseServiceError(502, f"中台请求失败: {e.message}") from e
    except asyncio.TimeoutError as e:
        raise EnterpriseServiceError(504, "中台请求超时，请稍后重试") from e
    except Exception as e:
        logger.exception("同步企业失败 enterprise_id=%s", enterprise_id)
        raise EnterpriseServiceError(500, "同步企业失败，请稍后重试") from e

    tenant_name = pf["tenant_name"]
    api_base_url = pf["api_base_url"]
    industry_code = pf["industry_code"] or body.industry
    industry_name = pf["industry_name"]

    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, config FROM tenant_registry WHERE tenant_id = %s",
                    (enterprise_id,),
                )
                row = await cur.fetchone()
                config = _merge_sync_config(row.get("config") if row else None, body)
                created = not row
                await cur.execute(
                    "INSERT INTO tenant_registry "
                    "(tenant_id, tenant_name, api_base_url, auth_type, auth_credential, "
                    "industry_code, industry_name, status, config) "
                    "VALUES (%s, %s, %s, 'token', 'pending', %s, %s, 1, %s::jsonb) "
                    "ON CONFLICT (tenant_id) DO UPDATE SET "
                    "tenant_name = EXCLUDED.tenant_name, "
                    "api_base_url = EXCLUDED.api_base_url, "
                    "industry_code = COALESCE(EXCLUDED.industry_code, tenant_registry.industry_code), "
                    "industry_name = COALESCE(EXCLUDED.industry_name, tenant_registry.industry_name), "
                    "status = 1, "
                    "config = EXCLUDED.config, "
                    "updated_at = NOW()",
                    (
                        enterprise_id,
                        tenant_name,
                        api_base_url + "/web/ai",
                        industry_code,
                        industry_name,
                        json.dumps(config, ensure_ascii=False),
                    ),
                )
            await conn.commit()
    except Exception as e:
        logger.exception("同步企业失败 enterprise_id=%s", enterprise_id)
        raise EnterpriseServiceError(500, "同步企业失败，请稍后重试") from e

    await _invalidate_tenant_cache(enterprise_id)

    updated_row = await _get_tenant_row(enterprise_id)
    if not updated_row:
        raise EnterpriseServiceError(500, "同步企业后读取结果失败")
    return {"enterprise": _row_to_enterprise(updated_row), "created": created}


async def patch_enterprise_config_compat(enterprise_id: str, config: dict) -> dict:
    row = await _get_tenant_row(enterprise_id)
    if not row:
        raise EnterpriseServiceError(404, "企业不存在")

    patch: dict = {}
    if "analysis_period_days" in config:
        patch["analysis_period_days"] = config["analysis_period_days"]
    if "auto_diagnosis_frequency" in config:
        patch["diagnosis_trigger_mode"] = normalize_diagnosis_trigger_mode(config["auto_diagnosis_frequency"])
    if "solution_sort_strategy" in config:
        patch["solution_sort_strategy"] = config["solution_sort_strategy"]

    if patch:
        await update_tenant_config(enterprise_id, patch)

    updated_row = await _get_tenant_row(enterprise_id)
    return _row_to_enterprise(updated_row) if updated_row else {}
