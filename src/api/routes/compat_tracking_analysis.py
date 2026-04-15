"""效果追踪分析端点 — 趋势/分析/看板。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.services import tracking_service

router = APIRouter()


@router.get("/{tracking_id}/analyze", summary="效果分析")
async def analyze_tracking(tracking_id: str):
    return await tracking_service.analyze_tracking_payload(tracking_id)


@router.get("/{tracking_id}/trends", summary="指标趋势")
async def get_trends(tracking_id: str):
    return await tracking_service.get_tracking_trends_payload(tracking_id)


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
