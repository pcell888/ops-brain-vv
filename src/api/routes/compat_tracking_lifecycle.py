"""效果追踪生命周期端点 — 启动/列表/摘要/完成/取消。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.services import tracking_service

router = APIRouter()


@router.post("/start", summary="启动效果追踪")
async def start_tracking(data: dict):
    try:
        enterprise_id = data.get("enterprise_id", "")
        plan_id = data.get("plan_id", "")
        interval_days = data.get("tracking_interval_days", 7)
        return await tracking_service.start_effect_tracking(enterprise_id, plan_id, interval_days)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/list", summary="追踪列表")
async def list_trackings(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    diagnosis_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await tracking_service.list_tracking_items(
        enterprise_id=enterprise_id,
        status=status,
        diagnosis_id=diagnosis_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{tracking_id}", summary="追踪摘要")
async def get_tracking_summary(tracking_id: str):
    try:
        return await tracking_service.get_tracking_summary_payload(tracking_id)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{tracking_id}/complete", summary="完成追踪")
async def complete_tracking(tracking_id: str):
    try:
        return await tracking_service.submit_complete_tracking(tracking_id)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{tracking_id}/cancel", summary="取消追踪")
async def cancel_tracking(tracking_id: str):
    try:
        return await tracking_service.cancel_tracking_request(tracking_id)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
