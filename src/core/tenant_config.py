"""租户诊断配置读写 — tenant_registry.config JSONB 字段。"""

from __future__ import annotations

import json
import logging

from src.core.db_pool import get_conn

logger = logging.getLogger(__name__)

CONFIG_DEFAULTS = {
    "diagnosis_trigger_mode": "manual",
    "analysis_period_days": 30,
    "stores": [],
}

LEGACY_AUTO_TRIGGER_MODES = {"auto", "both", "daily", "weekly", "monthly"}


def normalize_diagnosis_trigger_mode(value: object) -> str:
    """将历史/兼容枚举统一收敛为 auto 或 manual。"""
    if isinstance(value, str) and value.lower() in LEGACY_AUTO_TRIGGER_MODES:
        return "auto"
    return "manual"


def normalize_tenant_config(raw: dict | None) -> dict:
    """合并默认值并归一化关键配置项。"""
    config = {**CONFIG_DEFAULTS, **(raw or {})}
    config["diagnosis_trigger_mode"] = normalize_diagnosis_trigger_mode(
        config.get("diagnosis_trigger_mode")
    )
    stores = config.get("stores")
    config["stores"] = stores if isinstance(stores, list) else []
    return config


async def get_tenant_config(tenant_id: str) -> dict:
    """读取租户配置，合并默认值。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT config FROM tenant_registry WHERE tenant_id = %s AND status = 1",
                    (tenant_id,),
                )
                row = await cur.fetchone()
        raw = (row[0] if row else None) or {}
        if isinstance(raw, str):
            raw = json.loads(raw)
    except Exception as e:
        logger.warning("读取租户 %s 配置失败: %s", tenant_id, e)
        raw = {}
    return normalize_tenant_config(raw)


async def sync_tenant(
    tenant_id: str,
    tenant_name: str,
    industry_code: str,
    team_size: int,
    store_id: str | None = None,
    store_name: str | None = None,
    api_base_url: str = "http://localhost:8200",
) -> dict:
    """第三方企业同步：首次创建，后续更新。返回完整企业信息。"""
    store_entry = {"store_id": store_id, "store_name": store_name or ""} if store_id else None

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT tenant_id, config FROM tenant_registry WHERE tenant_id = %s",
                (tenant_id,),
            )
            row = await cur.fetchone()

            if row:
                raw = row[1] or {}
                if isinstance(raw, str):
                    raw = json.loads(raw)
                config = normalize_tenant_config(raw)
                config["team_size"] = team_size

                if store_entry:
                    stores = config.get("stores", [])
                    existing_ids = {s["store_id"] for s in stores}
                    if store_id not in existing_ids:
                        stores.append(store_entry)
                    else:
                        stores = [store_entry if s["store_id"] == store_id else s for s in stores]
                    config["stores"] = stores

                await cur.execute(
                    "UPDATE tenant_registry "
                    "SET tenant_name = %s, industry_code = %s, config = %s::jsonb, updated_at = NOW() "
                    "WHERE tenant_id = %s",
                    (tenant_name, industry_code, json.dumps(config, ensure_ascii=False), tenant_id),
                )
            else:
                config = normalize_tenant_config(
                    {
                        "team_size": team_size,
                        "stores": [store_entry] if store_entry else [],
                    }
                )
                await cur.execute(
                    "INSERT INTO tenant_registry "
                    "(tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code, status, config) "
                    "VALUES (%s, %s, %s, 'token', 'pending', %s, 1, %s::jsonb)",
                    (tenant_id, tenant_name, api_base_url, industry_code, json.dumps(config, ensure_ascii=False)),
                )
        await conn.commit()

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "industry_code": industry_code,
        "team_size": team_size,
        "stores": config.get("stores", []),
        "diagnosis_trigger_mode": config["diagnosis_trigger_mode"],
        "analysis_period_days": config["analysis_period_days"],
    }


async def update_tenant_config(tenant_id: str, patch: dict) -> dict:
    """更新租户配置（增量合并）。"""
    current = await get_tenant_config(tenant_id)
    current.update(patch)
    current = normalize_tenant_config(current)
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE tenant_registry SET config = %s::jsonb, updated_at = NOW() WHERE tenant_id = %s AND status = 1",
                (json.dumps(current, ensure_ascii=False), tenant_id),
            )
        await conn.commit()
    return current
