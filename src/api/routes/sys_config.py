"""企业诊断配置 API — 读写 tenant_registry.config JSONB。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from src.core.tenant_config import get_tenant_config, update_tenant_config, sync_tenant

router = APIRouter(prefix="/api/tenant-config", tags=["tenant-config"])


class SyncTenantRequest(BaseModel):
    tenant_id: str = Field(..., description="企业ID")
    tenant_name: str = Field(..., description="企业名称")
    industry_code: str = Field(..., description="行业编码")
    team_size: int = Field(..., description="团队人数")
    store_id: str | None = Field(default=None, description="店铺ID，不传则仅同步企业信息")
    store_name: str | None = Field(default=None, description="店铺名称")


class StoreItem(BaseModel):
    store_id: str
    store_name: str


class UpdateTenantConfigRequest(BaseModel):
    diagnosis_trigger_mode: Literal["manual", "auto", "both"] | None = Field(
        default=None, description="诊断触发模式: manual=仅手动, auto=定时自动, both=手动+自动",
    )
    analysis_period_days: Literal[30, 60, 90] | None = Field(
        default=None, description="数据分析周期(天)",
    )
    stores: list[StoreItem] | None = Field(
        default=None, description="企业店铺列表",
    )


@router.get("/{tenant_id}")
async def get_config(tenant_id: str):
    """获取企业诊断配置。"""
    config = await get_tenant_config(tenant_id)
    return {
        "tenant_id": tenant_id,
        "config": {
            "diagnosis_trigger_mode": {
                "value": config["diagnosis_trigger_mode"],
                "options": ["manual", "auto", "both"],
                "description": "诊断触发模式: manual=仅手动, auto=定时自动, both=手动+自动",
            },
            "analysis_period_days": {
                "value": config["analysis_period_days"],
                "options": [30, 60, 90],
                "description": "数据分析周期(天)",
            },
            "stores": config.get("stores", []),
        },
    }


@router.put("/{tenant_id}")
async def update_config(tenant_id: str, request: UpdateTenantConfigRequest):
    """更新企业诊断配置（只传需要修改的字段）。"""
    patch = {}
    if request.diagnosis_trigger_mode is not None:
        patch["diagnosis_trigger_mode"] = request.diagnosis_trigger_mode
    if request.analysis_period_days is not None:
        patch["analysis_period_days"] = request.analysis_period_days
    if request.stores is not None:
        patch["stores"] = [s.model_dump() for s in request.stores]
    if not patch:
        raise HTTPException(status_code=400, detail="至少提供一个配置项")
    updated = await update_tenant_config(tenant_id, patch)
    return {"tenant_id": tenant_id, "config": updated}


@router.post("/sync")
async def sync_tenant_info(request: SyncTenantRequest):
    """
    同步企业信息（供第三方企业 App 调用，每次进入调用）。
    首次进入自动创建企业，后续进入更新信息。
    """
    result = await sync_tenant(
        tenant_id=request.tenant_id,
        tenant_name=request.tenant_name,
        industry_code=request.industry_code,
        team_size=request.team_size,
        store_id=request.store_id or None,
        store_name=request.store_name or None,
    )
    return result
