"""效果追踪快照端点 — 采集/列表/看板。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services import tracking_service

router = APIRouter()


class SnapshotBody(BaseModel):
    enterprise_id: str | None = Field(default=None, description="租户/企业 ID")
    auth_token: str | None = Field(default=None, description="可选业务 API 鉴权")


@router.post("/{tracking_id}/snapshot", summary="采集快照")
async def take_snapshot(tracking_id: str, body: SnapshotBody | None = None):
    b = body or SnapshotBody()
    auth_token = b.auth_token.strip() if b.auth_token and str(b.auth_token).strip() else None
    try:
        return await tracking_service.take_tracking_snapshot(
            tracking_id,
            enterprise_id=b.enterprise_id,
            auth_token=auth_token,
        )
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{tracking_id}/snapshots", summary="快照列表")
async def get_snapshots(tracking_id: str):
    return await tracking_service.list_tracking_snapshots_view(tracking_id)


@router.get("/snapshots/{snapshot_id}/dashboard", summary="快照看板")
async def get_snapshot_dashboard(snapshot_id: str):
    try:
        return await tracking_service.get_snapshot_dashboard_payload(snapshot_id)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
