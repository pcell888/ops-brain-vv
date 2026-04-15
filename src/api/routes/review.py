"""复盘相关 HTTP 接口（立即开始复盘、进度轮询）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.services import review_service

router = APIRouter(prefix="/review", tags=["复盘"])


@router.post("/{thread_id}/start", summary="立即开始复盘")
async def start_review(thread_id: str):
    """立即开始复盘（跳过剩余等待期，恢复 graph 运行 track_effects）。"""
    try:
        return await review_service.start_immediate_review(thread_id)
    except review_service.ReviewServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{thread_id}/progress", summary="查询复盘进度")
async def get_review_progress(thread_id: str):
    """轮询效果追踪 / 复盘执行进度（与 WebSocket `stage=effect_track` 同源缓存）。"""
    return await review_service.build_review_progress(thread_id)


@router.get("/knowledge/list", summary="查询方案沉淀知识库")
async def get_solution_knowledge(
    tenant_id: str | None = Query(default=None),
    industry_code: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询方案沉淀知识库（分页）。"""
    return await review_service.list_solution_knowledge_page(tenant_id, industry_code, page, page_size)
