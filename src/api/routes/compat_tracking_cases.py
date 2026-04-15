"""效果追踪案例搜索端点。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.services import tracking_service

router = APIRouter()


@router.get("/cases/search", summary="案例搜索")
async def search_cases(
    plan_name: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await tracking_service.search_tracking_cases(plan_name=plan_name, skip=skip, limit=limit)


@router.get("/cases/similar", summary="相似案例")
async def get_similar_cases(
    indicators: str = Query(default=""),
    industry: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
):
    return await tracking_service.list_similar_tracking_cases(indicators, industry, limit)


@router.get("/cases/{case_id}", summary="案例详情")
async def get_case_detail(case_id: str):
    try:
        return await tracking_service.get_tracking_case_detail(case_id)
    except tracking_service.TrackingServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
