"""企业接口 — /enterprises 系列接口，底层读 tenant_registries。"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request

from src.services import enterprise_service
from src.services.enterprise_service import SyncEnterpriseBody

router = APIRouter(prefix="/enterprises", tags=["企业"])


@router.get("", summary="企业列表")
async def list_enterprises():
    try:
        return await enterprise_service.list_enterprises()
    except enterprise_service.EnterpriseServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{enterprise_id}", summary="企业详情")
async def get_enterprise(enterprise_id: str):
    try:
        return await enterprise_service.get_enterprise(enterprise_id)
    except enterprise_service.EnterpriseServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.put("/{enterprise_id}", summary="同步企业")
async def sync_enterprise(enterprise_id: str, body: SyncEnterpriseBody, request: Request):
    auth_override = getattr(request.state, "platform_token", None)
    try:
        return await enterprise_service.sync_enterprise(enterprise_id, body, auth_override)
    except enterprise_service.EnterpriseServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.patch("/{enterprise_id}/config", summary="更新企业配置")
async def update_enterprise_config(enterprise_id: str, config: dict = Body(...)):
    try:
        return await enterprise_service.patch_enterprise_config(enterprise_id, config)
    except enterprise_service.EnterpriseServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
