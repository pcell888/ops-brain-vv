"""前端兼容层 — /execution 系列接口。

薄适配器：仅负责参数映射和响应格式转换，业务逻辑委托给 Service 层。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from src.services import execution_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/execution", tags=["执行"])


@router.get("/plans", summary="执行计划列表")
async def list_execution_plans(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    diagnosis_id: str | None = Query(default=None, description="诊断 thread_id，筛选该次诊断下的执行计划"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    # 参数映射
    tenant_id = enterprise_id
    thread_id = diagnosis_id

    # 调用 Service 层
    items, total = await execution_service.get_execution_plans(
        tenant_id=tenant_id,
        thread_id=thread_id,
        status=status,
        skip=skip,
        limit=limit,
    )

    return {"items": items, "total": total}


@router.get("/tasks", summary="执行任务列表")
async def list_tasks(
    enterprise_id: str | None = Query(default=None),
    thread_id: str | None = Query(default=None, description="诊断 thread_id，筛选该次诊断下的任务"),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    tenant_id = enterprise_id
    items, total, stats = await execution_service.get_execution_tasks(
        tenant_id=tenant_id,
        thread_id=thread_id,
        status=status,
        skip=skip,
        limit=limit,
    )

    return {"items": items, "total": total, "stats": stats}


@router.get("/tasks/{task_id}", summary="执行任务详情")
async def get_task_detail(task_id: str):
    task = await execution_service.get_task_detail(task_id)
    
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task


@router.get("/plans/{plan_id}", summary="执行计划摘要")
async def get_plan_summary(plan_id: str):
    plan = await execution_service.get_plan_summary(plan_id)
    
    if plan is None:
        raise HTTPException(status_code=404, detail="执行计划不存在")
    
    return plan


@router.get("/plans/{plan_id}/tasks", summary="计划任务列表(兼容)")
async def list_plan_tasks(plan_id: str, status: str | None = Query(default=None)):
    # 调用 Service 层
    items, total = await execution_service.get_plan_tasks(plan_id, status)
    
    return {"items": items, "total": total}


@router.post("/tasks/{task_id}/complete", summary="完成任务")
async def complete_task(task_id: str):
    success = await execution_service.update_task_status(task_id, "completed")
    
    if not success:
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
    
    return {"status": "ok"}


@router.post("/tasks/{task_id}/fail", summary="任务失败")
async def fail_task(task_id: str):
    success = await execution_service.update_task_status(task_id, "failed")
    
    if not success:
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
    
    return {"status": "ok"}


@router.post("/tasks/{task_id}/retry", summary="重试任务")
async def retry_task(task_id: str):
    success = await execution_service.update_task_status(task_id, "running")
    
    if not success:
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
    
    return {"status": "ok"}
