"""方案相关 HTTP 接口（兼容层）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.services import solution_service

router = APIRouter(prefix="/solutions", tags=["方案"])


@router.get("/generate/active/{diagnosis_id}", summary="活跃生成任务")
async def compat_active_generation(diagnosis_id: str):
    return solution_service.compat_active_generation_payload(diagnosis_id)


@router.get("/list/{diagnosis_id}", summary="方案列表")
async def compat_solution_list(diagnosis_id: str):
    return await solution_service.build_compat_solution_list(diagnosis_id)


@router.put("/{solution_id}/adopt", summary="采纳方案")
async def compat_adopt_solution(solution_id: str):
    try:
        thread_id = await solution_service.resolve_thread_id_for_plan(solution_id, prefer_wait_adoption=True)
        return await solution_service.adopt_plan_and_enqueue(thread_id, solution_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{solution_id}/adopt/progress", summary="采纳方案执行进度")
async def compat_adopt_execution_progress(solution_id: str):
    try:
        thread_id = await solution_service.resolve_thread_id_for_plan(solution_id, prefer_wait_adoption=True)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    data = await solution_service.get_adopt_execution_progress_payload(thread_id)
    data["solution_id"] = solution_id
    return data


@router.get("/detail/{solution_id}", summary="方案详情")
async def compat_solution_detail(solution_id: str):
    try:
        return await solution_service.build_compat_solution_detail(solution_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{thread_id}/plans/{plan_id}/redistribute", summary="重新派发任务")
async def redistribute_tasks(thread_id: str, plan_id: str):
    """手动重新派发指定方案的任务（仅派发 pending/failed 状态的任务）。"""
    try:
        return await solution_service.redistribute_plan_tasks(thread_id, plan_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
