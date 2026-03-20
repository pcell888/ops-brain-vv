"""前端兼容层 — /execution 系列接口。

基于 ai_exec_task 表提供执行计划和任务管理接口。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Body
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/execution", tags=["执行(兼容层)"])


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


@router.get("/plans", summary="执行计划列表(兼容)")
async def list_execution_plans(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """兼容前端 GET /execution/plans。

    从 ai_exec_task 表按 plan_id 分组，构造执行计划列表。
    """
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_clauses = []
                params: list = []
                if enterprise_id:
                    where_clauses.append("tenant_id = %s")
                    params.append(enterprise_id)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                await cur.execute(
                    f"""
                    SELECT plan_id, thread_id, tenant_id,
                           MIN(task_name) AS first_task_name,
                           COUNT(*) AS total_tasks,
                           COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
                           COUNT(*) FILTER (WHERE status = 'running') AS running_tasks,
                           COUNT(*) FILTER (WHERE status = 'failed') AS failed_tasks,
                           COUNT(*) FILTER (WHERE status = 'pending') AS pending_tasks,
                           MIN(created_at) AS created_at
                    FROM ai_exec_task
                    {where_sql}
                    GROUP BY plan_id, thread_id, tenant_id
                    ORDER BY MIN(created_at) DESC
                    OFFSET %s LIMIT %s
                    """,
                    params + [skip, limit],
                )
                rows = await cur.fetchall()

                await cur.execute(
                    f"SELECT COUNT(DISTINCT plan_id) FROM ai_exec_task {where_sql}",
                    params,
                )
                total = (await cur.fetchone() or {}).get("count", 0)

        items = []
        for row in rows:
            total_t = row["total_tasks"]
            completed_t = row["completed_tasks"]
            running_t = row["running_tasks"]
            failed_t = row["failed_tasks"]
            pending_t = row["pending_tasks"]

            if completed_t == total_t:
                plan_status = "completed"
            elif running_t > 0:
                plan_status = "running"
            elif failed_t > 0 and pending_t == 0 and running_t == 0:
                plan_status = "failed"
            else:
                plan_status = "pending"

            progress = round(completed_t / total_t * 100) if total_t > 0 else 0

            if status and plan_status != status:
                continue

            created = row["created_at"]
            items.append({
                "plan_id": row["plan_id"],
                "solution_id": row["plan_id"],
                "name": f"执行计划 - {row['plan_id'][:8]}",
                "status": plan_status,
                "progress": progress,
                "task_stats": {
                    "pending": pending_t,
                    "ready": 0,
                    "running": running_t,
                    "paused": 0,
                    "completed": completed_t,
                    "failed": failed_t,
                    "cancelled": 0,
                },
                "planned_start": created.isoformat() if created else None,
                "planned_end": (created + timedelta(days=30)).isoformat() if created else None,
            })

        return {"items": items, "total": total}
    except Exception as e:
        logger.error("查询执行计划列表失败: %s", e)
        return {"items": [], "total": 0}


@router.get("/plans/{plan_id}", summary="执行计划摘要(兼容)")
async def get_plan_summary(plan_id: str):
    """兼容前端 GET /execution/plans/{planId}。"""
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT plan_id, thread_id, tenant_id,
                           COUNT(*) AS total_tasks,
                           COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
                           COUNT(*) FILTER (WHERE status = 'running') AS running_tasks,
                           COUNT(*) FILTER (WHERE status = 'failed') AS failed_tasks,
                           COUNT(*) FILTER (WHERE status = 'pending') AS pending_tasks,
                           MIN(created_at) AS created_at
                    FROM ai_exec_task
                    WHERE plan_id = %s
                    GROUP BY plan_id, thread_id, tenant_id
                    """,
                    (plan_id,),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="执行计划不存在")

        total_t = row["total_tasks"]
        completed_t = row["completed_tasks"]
        running_t = row["running_tasks"]
        failed_t = row["failed_tasks"]
        pending_t = row["pending_tasks"]

        if completed_t == total_t:
            plan_status = "completed"
        elif running_t > 0:
            plan_status = "running"
        elif failed_t > 0 and pending_t == 0:
            plan_status = "failed"
        else:
            plan_status = "pending"

        progress = round(completed_t / total_t * 100) if total_t > 0 else 0
        created = row["created_at"]

        return {
            "plan_id": plan_id,
            "solution_id": plan_id,
            "name": f"执行计划 - {plan_id[:8]}",
            "status": plan_status,
            "progress": progress,
            "task_stats": {
                "pending": pending_t,
                "ready": 0,
                "running": running_t,
                "paused": 0,
                "completed": completed_t,
                "failed": failed_t,
                "cancelled": 0,
            },
            "planned_start": created.isoformat() if created else None,
            "planned_end": (created + timedelta(days=30)).isoformat() if created else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("查询执行计划失败: %s", e)
        raise HTTPException(status_code=500, detail="查询失败") from e


@router.get("/plans/{plan_id}/tasks", summary="计划任务列表(兼容)")
async def list_plan_tasks(plan_id: str, status: str | None = Query(default=None)):
    """兼容前端 GET /execution/plans/{planId}/tasks。"""
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where = "WHERE plan_id = %s"
                params: list = [plan_id]
                if status:
                    where += " AND status = %s"
                    params.append(status)

                await cur.execute(
                    f"""
                    SELECT task_id, task_name, description, priority, status,
                           assignee_user_id, assignee_dept_id, deadline, created_at
                    FROM ai_exec_task
                    {where}
                    ORDER BY created_at
                    """,
                    params,
                )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            task_status = row["status"] or "pending"
            items.append({
                "id": row["task_id"],
                "task_key": row["task_id"],
                "name": row["task_name"] or "",
                "description": row["description"] or "",
                "status": task_status,
                "execution_type": "manual",
                "dependencies": [],
                "scheduled_start": row["created_at"].isoformat() if row.get("created_at") else None,
                "scheduled_end": row["deadline"],
                "progress": 100 if task_status == "completed" else 0,
                "assigned_to": str(row.get("assignee_user_id") or row.get("assignee_dept_id") or ""),
            })

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error("查询任务列表失败: %s", e)
        return {"items": [], "total": 0}


@router.post("/plans/{plan_id}/start", summary="启动执行计划(兼容)")
async def start_plan(plan_id: str):
    """将计划下所有 pending 任务标记为 running。"""
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = 'running' WHERE plan_id = %s AND status = 'pending'",
                    (plan_id,),
                )
            await conn.commit()
        return {"status": "ok", "message": "计划已启动"}
    except Exception as e:
        logger.error("启动计划失败: %s", e)
        raise HTTPException(status_code=500, detail="启动失败") from e


@router.post("/plans/{plan_id}/pause", summary="暂停执行计划(兼容)")
async def pause_plan(plan_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = 'pending' WHERE plan_id = %s AND status = 'running'",
                    (plan_id,),
                )
            await conn.commit()
        return {"status": "ok", "message": "计划已暂停"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="暂停失败") from e


@router.post("/plans/{plan_id}/resume", summary="恢复执行计划(兼容)")
async def resume_plan(plan_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = 'running' WHERE plan_id = %s AND status = 'pending'",
                    (plan_id,),
                )
            await conn.commit()
        return {"status": "ok", "message": "计划已恢复"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="恢复失败") from e


@router.post("/tasks/{task_id}/complete", summary="完成任务(兼容)")
async def complete_task(task_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = 'completed' WHERE task_id = %s",
                    (task_id,),
                )
            await conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="操作失败") from e


@router.post("/tasks/{task_id}/fail", summary="任务失败(兼容)")
async def fail_task(task_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = 'failed' WHERE task_id = %s",
                    (task_id,),
                )
            await conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="操作失败") from e


@router.post("/tasks/{task_id}/retry", summary="重试任务(兼容)")
async def retry_task(task_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = 'running' WHERE task_id = %s",
                    (task_id,),
                )
            await conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="操作失败") from e
