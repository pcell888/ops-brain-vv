"""方案相关 HTTP 接口（获取方案列表、采纳方案、重新派发任务）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core.models import AdoptPlanRequest
from src.services import solution_service

router = APIRouter(prefix="/solutions", tags=["方案"])


@router.get("/{thread_id}", summary="获取方案列表")
async def get_diagnosis_solutions(thread_id: str):
    """
    获取方案列表（含对比数据、采纳状态、AI推荐）。
    - 诊断完成后调用：展示所有方案 + 对比 + 推荐，status=pending_adoption
    - 已采纳后调用：展示所有方案 + 标记哪些已采纳，status=adopted
    """
    return await solution_service.get_solutions_payload(thread_id)


@router.post("/{thread_id}/adopt", summary="用户采纳方案")
async def adopt_plan(thread_id: str, request: AdoptPlanRequest):
    """用户采纳唯一方案（互斥）后继续执行。"""
    try:
        return await solution_service.adopt_plan_and_enqueue(thread_id, request.plan_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{thread_id}/adopt-progress", summary="查询采纳方案执行进度")
async def get_adopt_execution_progress(thread_id: str):
    """轮询采纳后的任务派发与执行进度（与 WebSocket 推送同源缓存）。"""
    return await solution_service.get_adopt_execution_progress_payload(thread_id)


async def _resume_after_adoption(thread_id: str, config: dict):
    """兼容 worker：实际执行逻辑已下沉到 service 层。"""
    await solution_service.resume_after_adoption(thread_id, config)


@router.post("/{thread_id}/plans/{plan_id}/redistribute", summary="重新派发任务")
async def redistribute_tasks(thread_id: str, plan_id: str):
    """手动重新派发指定方案的任务（仅派发 pending/failed 状态的任务）。"""
    try:
        return await solution_service.redistribute_plan_tasks(thread_id, plan_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
