"""效果追踪复盘报告端点。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.services import review_service, tracking_service

router = APIRouter()


@router.get("/{tracking_id}/review/progress", summary="复盘进度(兼容)")
async def compat_review_progress(tracking_id: str):
    return await review_service.build_review_progress(tracking_id)


@router.get("/{tracking_id}/report", summary="复盘报告")
async def get_report(tracking_id: str):
    try:
        return await tracking_service.get_compat_review_report(tracking_id)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
