"""前端兼容层 — /solutions 系列接口。

将后端 plan-based 方案数据转换为前端 SolutionGenerateResponse 格式。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.routes.solutions import adopt_plan, get_adopt_execution_progress
from src.core.models import AdoptPlanRequest
from src.services import solution_service

router = APIRouter(prefix="/solutions", tags=["方案(兼容层)"])

@router.get("/generate/active/{diagnosis_id}", summary="活跃生成任务(兼容)")
async def compat_active_generation(diagnosis_id: str):
    return solution_service.compat_active_generation_payload(diagnosis_id)


@router.get("/list/{diagnosis_id}", summary="方案列表(兼容)")
async def compat_solution_list(diagnosis_id: str):
    return await solution_service.build_compat_solution_list(diagnosis_id)


@router.put("/{solution_id}/adopt", summary="采纳方案(兼容)")
async def compat_adopt_solution(solution_id: str):
    try:
        thread_id = await solution_service.resolve_thread_id_for_plan(solution_id, prefer_wait_adoption=True)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return await adopt_plan(thread_id, AdoptPlanRequest(plan_id=solution_id))


@router.get("/{solution_id}/adopt/progress", summary="采纳方案执行进度(兼容)")
async def compat_adopt_execution_progress(solution_id: str):
    try:
        thread_id = await solution_service.resolve_thread_id_for_plan(solution_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    data = await get_adopt_execution_progress(thread_id)
    data["solution_id"] = solution_id
    return data


@router.get("/detail/{solution_id}", summary="方案详情(兼容)")
async def compat_solution_detail(solution_id: str):
    try:
        return await solution_service.build_compat_solution_detail(solution_id)
    except solution_service.SolutionServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
