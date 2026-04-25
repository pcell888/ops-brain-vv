"""效果追踪 HTTP 接口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.services.tracking_lifecycle import (
    cancel_tracking_request,
    get_tracking_summary_payload,
    list_tracking_items,
    start_effect_tracking,
    submit_complete_tracking,
)
from src.services.tracking_snapshot import (
    get_snapshot_dashboard_payload,
    list_tracking_snapshots_view,
    take_tracking_snapshot,
)
from src.services.tracking_report import get_compat_review_report
from src.services.tracking_case import (
    analyze_tracking_payload,
    get_tracking_case_detail,
    get_tracking_trends_payload,
    list_similar_tracking_cases,
    search_tracking_cases,
)
from src.services.tracking_error_service import TrackingServiceError
from src.services import review_service

router = APIRouter(prefix="/tracking", tags=["效果追踪"])


class SnapshotBody(BaseModel):
    enterprise_id: str | None = Field(default=None, description="租户/企业 ID")
    auth_token: str | None = Field(default=None, description="可选业务 API 鉴权")


@router.post("/start", summary="启动效果追踪")
async def start_tracking(data: dict):
    try:
        enterprise_id = data.get("enterprise_id", "")
        plan_id = data.get("plan_id", "")
        interval_days = data.get("tracking_interval_days", 7)
        return await start_effect_tracking(enterprise_id, plan_id, interval_days)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/list", summary="追踪列表")
async def list_trackings(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    diagnosis_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await list_tracking_items(
        enterprise_id=enterprise_id,
        status=status,
        diagnosis_id=diagnosis_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{tracking_id}", summary="追踪摘要")
async def get_tracking_summary(tracking_id: str):
    try:
        return await get_tracking_summary_payload(tracking_id)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{tracking_id}/complete", summary="完成追踪")
async def complete_tracking(tracking_id: str):
    try:
        return await submit_complete_tracking(tracking_id)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{tracking_id}/cancel", summary="取消追踪")
async def cancel_tracking(tracking_id: str):
    try:
        return await cancel_tracking_request(tracking_id)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{tracking_id}/snapshot", summary="采集快照")
async def take_snapshot(tracking_id: str, body: SnapshotBody | None = None):
    b = body or SnapshotBody()
    auth_token = b.auth_token.strip() if b.auth_token and str(b.auth_token).strip() else None
    try:
        return await take_tracking_snapshot(
            tracking_id,
            enterprise_id=b.enterprise_id,
            auth_token=auth_token,
        )
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{tracking_id}/snapshots", summary="快照列表")
async def get_snapshots(tracking_id: str):
    return await list_tracking_snapshots_view(tracking_id)


@router.get("/snapshots/{snapshot_id}/dashboard", summary="快照看板")
async def get_snapshot_dashboard(snapshot_id: str):
    try:
        return await get_snapshot_dashboard_payload(snapshot_id)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{tracking_id}/review/progress", summary="复盘进度")
async def review_progress(tracking_id: str):
    return await review_service.build_review_progress(tracking_id)


@router.get("/{tracking_id}/report", summary="复盘报告")
async def get_report(tracking_id: str):
    try:
        return await get_compat_review_report(tracking_id)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/cases/search", summary="案例搜索")
async def search_cases(
    plan_name: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await search_tracking_cases(plan_name=plan_name, skip=skip, limit=limit)


@router.get("/cases/similar", summary="相似案例")
async def get_similar_cases(
    indicators: str = Query(default=""),
    industry: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
):
    return await list_similar_tracking_cases(indicators, industry, limit)


@router.get("/cases/{case_id}", summary="案例详情")
async def get_case_detail(case_id: str):
    try:
        return await get_tracking_case_detail(case_id)
    except TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{tracking_id}/analyze", summary="效果分析")
async def analyze_tracking(tracking_id: str):
    return await analyze_tracking_payload(tracking_id)


@router.get("/{tracking_id}/trends", summary="指标趋势")
async def get_trends(tracking_id: str):
    return await get_tracking_trends_payload(tracking_id)


@router.get("/{tracking_id}/dashboard/funnel", summary="转化漏斗")
async def get_dashboard_funnel(tracking_id: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"tracking_id={tracking_id} 的转化漏斗尚未接入真实数据",
    )


@router.get("/{tracking_id}/dashboard/teams", summary="团队对比")
async def get_dashboard_teams(tracking_id: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"tracking_id={tracking_id} 的团队对比尚未接入真实数据",
    )


@router.get("/{tracking_id}/dashboard/ranking", summary="销售排名")
async def get_dashboard_ranking(tracking_id: str, limit: int = Query(default=10)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"tracking_id={tracking_id} 的销售排名尚未接入真实数据，limit={limit}",
    )


@router.get("/{tracking_id}/dashboard/summary", summary="看板汇总")
async def get_dashboard_summary(tracking_id: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"tracking_id={tracking_id} 的看板汇总尚未接入真实数据",
    )
