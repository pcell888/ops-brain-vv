"""前端兼容层 — /enterprises 系列接口，底层读 tenant_registry。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Body
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo
from src.core.tenant_config import get_tenant_config, update_tenant_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enterprises", tags=["企业(兼容层)"])


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

    return {
        "id": row["tenant_id"],
        "name": row.get("tenant_name") or row["tenant_id"],
        "industry": row.get("industry_code") or "general",
        "scale": raw_config.get("scale"),
        "team_size": raw_config.get("team_size"),
        "config": {
            "analysis_period_days": raw_config.get("analysis_period_days", 30),
            "auto_diagnosis_frequency": _trigger_mode_to_frequency(
                raw_config.get("diagnosis_trigger_mode", "manual")
            ),
            "solution_sort_strategy": raw_config.get("solution_sort_strategy", "balanced"),
        },
        "stores": raw_config.get("stores", []),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _trigger_mode_to_frequency(mode: str) -> str:
    return {"auto": "weekly", "both": "weekly"}.get(mode, "manual")


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


@router.patch("/{enterprise_id}/config", summary="更新企业配置")
async def update_enterprise_config(enterprise_id: str, config: dict = Body(...)):
    row = await _get_tenant_row(enterprise_id)
    if not row:
        raise HTTPException(status_code=404, detail="企业不存在")

    patch: dict = {}
    if "analysis_period_days" in config:
        patch["analysis_period_days"] = config["analysis_period_days"]
    if "auto_diagnosis_frequency" in config:
        freq = config["auto_diagnosis_frequency"]
        patch["diagnosis_trigger_mode"] = "manual" if freq == "manual" else "auto"
    if "solution_sort_strategy" in config:
        patch["solution_sort_strategy"] = config["solution_sort_strategy"]

    if patch:
        await update_tenant_config(enterprise_id, patch)

    updated_row = await _get_tenant_row(enterprise_id)
    return _row_to_enterprise(updated_row) if updated_row else {}
