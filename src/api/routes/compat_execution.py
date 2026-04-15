"""前端兼容层 — /execution 系列接口。

薄适配器：仅负责参数映射和响应格式转换，业务逻辑委托给 Service 层。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from src.services import execution_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/execution", tags=["执行(兼容层)"])


@router.get("/plans", summary="执行计划列表(兼容)")
async def list_execution_plans(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    diagnosis_id: str | None = Query(default=None, description="诊断 thread_id，筛选该次诊断下的执行计划"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """兼容前端 GET /execution/plans。

    参数映射：enterprise_id -> tenant_id, diagnosis_id -> thread_id
    调用 Service 层获取数据。
    """
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


@router.get("/tasks", summary="执行任务列表(兼容)")
async def list_tasks(
    enterprise_id: str | None = Query(default=None),
    thread_id: str | None = Query(default=None, description="诊断 thread_id，筛选该次诊断下的任务"),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """按企业/诊断拉平查询 ai_exec_task，供「任务执行」列表页展示任务行（非计划聚合）。
    
    参数映射：enterprise_id -> tenant_id
    """
    # 参数映射
    tenant_id = enterprise_id

    # 调用 Service 层
    items, total, stats = await execution_service.get_execution_tasks(
        tenant_id=tenant_id,
        thread_id=thread_id,
        status=status,
        skip=skip,
        limit=limit,
    )

    return {"items": items, "total": total, "stats": stats}


@router.get("/tasks/{task_id}", summary="执行任务详情(兼容)")
async def get_task_detail(task_id: str):
    """单条任务完整信息，供详情页展示业务内容（标题、说明、实施步骤、指派等）。"""
    # 调用 Service 层
    task = await execution_service.get_task_detail(task_id)
    
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task


@router.get("/plans/{plan_id}", summary="执行计划摘要(兼容)")
async def get_plan_summary(plan_id: str):
    """兼容前端 GET /execution/plans/{planId}。

    计划状态由 ai_exec_task 行聚合得到；采纳方案后任务由 execute 节点自动创建/派发，无单独「启动计划」步骤。
    """
    # 调用 Service 层
    plan = await execution_service.get_plan_summary(plan_id)
    
    if plan is None:
        raise HTTPException(status_code=404, detail="执行计划不存在")
    
    return plan


@router.get("/plans/{plan_id}/tasks", summary="计划任务列表(兼容)")
async def list_plan_tasks(plan_id: str, status: str | None = Query(default=None)):
    """兼容前端 GET /execution/plans/{planId}/tasks。"""
    # 调用 Service 层
    items, total = await execution_service.get_plan_tasks(plan_id, status)
    
    return {"items": items, "total": total}


@router.post("/tasks/{task_id}/complete", summary="完成任务(兼容)")
async def complete_task(task_id: str):
    """标记任务为已完成。"""
    # 调用 Service 层
    success = await execution_service.update_task_status(task_id, "completed")
    
    if not success:
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
    
    return {"status": "ok"}


@router.post("/tasks/{task_id}/fail", summary="任务失败(兼容)")
async def fail_task(task_id: str):
    """标记任务为失败。"""
    # 调用 Service 层
    success = await execution_service.update_task_status(task_id, "failed")
    
    if not success:
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
    
    return {"status": "ok"}


@router.post("/tasks/{task_id}/retry", summary="重试任务(兼容)")
async def retry_task(task_id: str):
    """重试任务（设置为运行中状态）。"""
    # 调用 Service 层
    success = await execution_service.update_task_status(task_id, "running")
    
    if not success:
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
    
    return {"status": "ok"}
