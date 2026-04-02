"""前端兼容层 — /enterprises 系列接口，底层读 tenant_registry。"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo
from src.mcp_servers.biz_api_client import BizAPIClient, BizAPIError
from src.mcp_servers.tenant_router import TenantNotFoundError, TenantRouter
from src.core.tenant_config import (
    CONFIG_DEFAULTS,
    normalize_diagnosis_trigger_mode,
    normalize_tenant_config,
    update_tenant_config,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enterprises", tags=["企业(兼容层)"])

_platform_router = TenantRouter()
_platform_biz = BizAPIClient(_platform_router)


class SyncEnterpriseBody(BaseModel):
    """生态 APP 同步企业：有则更新，无则创建。"""

    name: str = Field(default="", max_length=256)
    store_id: str | None = Field(default=None, max_length=64)
    industry: str | None = Field(default=None, max_length=64)
    scale: str | None = Field(default=None, pattern=r"^(small|medium|large|enterprise)$")
    team_size: int | None = Field(default=None, ge=1, le=100000)


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


async def _get_tenant_row(tenant_id: str) -> dict | None:
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
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
    """将 tenant_registry 行转换为前端 Enterprise 格式。"""
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
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
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
    """中台 projectInfo：query 仅 projectId（与入库 tenant_id 同源时等同企业 ID）。

    请求携带 Authorization（中台 platform token）时优先用它调中台，避免已入库租户仍用库中凭证
    从而绕过对当次请求的 token 校验（embed 场景）。
    """
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
        raise HTTPException(
            status_code=401,
            detail="租户尚未入库，请携带 Authorization 请求中台以完成首次同步",
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


@router.get("", summary="企业列表")
async def list_enterprises():
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
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
        raise HTTPException(status_code=500, detail="查询企业列表失败，请稍后重试") from e


@router.get("/{enterprise_id}", summary="企业详情")
async def get_enterprise(enterprise_id: str):
    row = await _get_tenant_row(enterprise_id)
    if not row:
        raise HTTPException(status_code=404, detail="企业不存在")
    return _row_to_enterprise(row)


@router.put("/{enterprise_id}", summary="同步企业")
async def sync_enterprise(enterprise_id: str, body: SyncEnterpriseBody, request: Request):
    created = False
    auth_override = getattr(request.state, "platform_token", None)

    try:
        raw_info = await _fetch_project_info_for_sync(enterprise_id, auth_override)
        pf = _platform_enterprise_fields(raw_info, body.name)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except BizAPIError as e:
        raise HTTPException(status_code=502, detail=f"中台请求失败: {e.message}") from e
    except asyncio.TimeoutError as e:
        raise HTTPException(status_code=504, detail="中台请求超时，请稍后重试") from e
    except Exception as e:
        logger.exception("同步企业失败 enterprise_id=%s", enterprise_id)
        raise HTTPException(status_code=500, detail="同步企业失败，请稍后重试") from e

    tenant_name = pf["tenant_name"]
    api_base_url = pf["api_base_url"]
    industry_code = pf["industry_code"] or body.industry
    industry_name = pf["industry_name"]

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
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
        raise HTTPException(status_code=500, detail="同步企业失败，请稍后重试") from e

    await _invalidate_tenant_cache(enterprise_id)

    updated_row = await _get_tenant_row(enterprise_id)
    if not updated_row:
        raise HTTPException(status_code=500, detail="同步企业后读取结果失败")
    return {"enterprise": _row_to_enterprise(updated_row), "created": created}


@router.patch("/{enterprise_id}/config", summary="更新企业配置")
async def update_enterprise_config(enterprise_id: str, config: dict = Body(...)):
    row = await _get_tenant_row(enterprise_id)
    if not row:
        raise HTTPException(status_code=404, detail="企业不存在")

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
