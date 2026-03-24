"""前端兼容层 — /enterprises 系列接口，底层读 tenant_registry。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo
from src.core.tenant_config import (
    CONFIG_DEFAULTS,
    normalize_diagnosis_trigger_mode,
    normalize_tenant_config,
    update_tenant_config,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enterprises", tags=["企业(兼容层)"])


class SyncEnterpriseBody(BaseModel):
    """生态 APP 同步企业：有则更新，无则创建。"""

    name: str = Field(..., min_length=1, max_length=256)
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
                    "SELECT tenant_id, tenant_name, industry_code, config, created_at, updated_at "
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


@router.get("", summary="企业列表")
async def list_enterprises():
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, tenant_name, industry_code, config, created_at, updated_at "
                    "FROM tenant_registry WHERE status = 1 AND tenant_id != '__platform__' "
                    "ORDER BY created_at DESC"
                )
                rows = await cur.fetchall()
        enterprises = [_row_to_enterprise(r) for r in rows]
        return {"enterprises": enterprises, "total": len(enterprises)}
    except Exception as e:
        logger.error("查询企业列表失败: %s", e)
        raise HTTPException(status_code=500, detail="查询企业列表失败") from e


@router.get("/{enterprise_id}", summary="企业详情")
async def get_enterprise(enterprise_id: str):
    row = await _get_tenant_row(enterprise_id)
    if not row:
        raise HTTPException(status_code=404, detail="企业不存在")
    return _row_to_enterprise(row)


@router.put("/{enterprise_id}", summary="同步企业")
async def sync_enterprise(enterprise_id: str, body: SyncEnterpriseBody):
    created = False

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, config FROM tenant_registry WHERE tenant_id = %s",
                    (enterprise_id,),
                )
                row = await cur.fetchone()
                config = _merge_sync_config(row.get("config") if row else None, body)

                if row:
                    await cur.execute(
                        "UPDATE tenant_registry "
                        "SET tenant_name = %s, industry_code = COALESCE(%s, industry_code), "
                        "status = 1, config = %s::jsonb, updated_at = NOW() "
                        "WHERE tenant_id = %s",
                        (
                            body.name,
                            body.industry,
                            json.dumps(config, ensure_ascii=False),
                            enterprise_id,
                        ),
                    )
                else:
                    created = True
                    await cur.execute(
                        "INSERT INTO tenant_registry "
                        "(tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code, status, config) "
                        "VALUES (%s, %s, %s, 'token', 'pending', %s, 1, %s::jsonb)",
                        (
                            enterprise_id,
                            body.name,
                            "http://localhost:8200",
                            body.industry,
                            json.dumps(config, ensure_ascii=False),
                        ),
                    )
            await conn.commit()
    except Exception as e:
        logger.error("同步企业 %s 失败: %s", enterprise_id, e)
        raise HTTPException(status_code=500, detail="同步企业失败") from e

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
        patch["diagnosis_trigger_mode"] = normalize_diagnosis_trigger_mode(
            config["auto_diagnosis_frequency"]
        )
    if "solution_sort_strategy" in config:
        patch["solution_sort_strategy"] = config["solution_sort_strategy"]

    if patch:
        await update_tenant_config(enterprise_id, patch)

    updated_row = await _get_tenant_row(enterprise_id)
    return _row_to_enterprise(updated_row) if updated_row else {}
