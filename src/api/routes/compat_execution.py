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


def _implementation_steps_from_related(related) -> list[str]:
    if isinstance(related, dict):
        steps = related.get("implementation_steps")
        if isinstance(steps, list):
            return [str(s).strip() for s in steps if str(s).strip()]
    return []


def _execution_type_from_related(related) -> str:
    """任务类型以后端落库的 related_resources 为准，缺省为 manual。"""
    if isinstance(related, dict):
        et = related.get("execution_type")
        if isinstance(et, str) and et.strip():
            return et.strip().lower()[:32]
    return "manual"


def _task_progress_percent(status: str | None, related) -> int:
    """进度：优先 related_resources.progress（0–100），否则按状态 completed=100、其余=0。"""
    if isinstance(related, dict):
        p = related.get("progress")
        if isinstance(p, (int, float)) and 0 <= float(p) <= 100:
            return int(round(float(p)))
    st = (status or "pending").lower()
    return 100 if st == "completed" else 0


def _dispatch_status_from_related(related) -> str:
    """派发状态：落库成功即视为已派发；可扩展 dispatch_failed 等。"""
    if isinstance(related, dict):
        ds = related.get("dispatch_status")
        if isinstance(ds, str) and ds.strip():
            return ds.strip().lower()[:32]
    return "dispatched"


def _recipient_from_row(row: dict) -> str:
    """接收者：优先业务用户 ID，否则部门 ID。"""
    uid = row.get("assignee_user_id")
    did = row.get("assignee_dept_id")
    if uid is not None:
        return str(uid)
    if did:
        return str(did)
    return ""


def _task_row_to_api_item(row: dict, *, include_plan_meta: bool) -> dict:
    """统一任务行序列化，避免列表与计划详情两套逻辑不一致。"""
    related = row.get("related_resources")
    task_status = row["status"] or "pending"
    recipient = _recipient_from_row(row)
    item: dict = {
        "id": row["task_id"],
        "task_key": row["task_id"],
        "name": row["task_name"] or "",
        "description": row["description"] or "",
        "implementation_steps": _implementation_steps_from_related(related),
        "status": task_status,
        "execution_type": _execution_type_from_related(related),
        "dependencies": [],
        "scheduled_start": row["created_at"].isoformat() if row.get("created_at") else None,
        "scheduled_end": row["deadline"],
        "progress": _task_progress_percent(task_status, related),
        "assigned_to": recipient,
        "recipient": recipient,
        "dispatch_status": _dispatch_status_from_related(related),
        "dispatch_time": row["created_at"].isoformat() if row.get("created_at") else None,
    }
    if include_plan_meta:
        item["plan_id"] = row["plan_id"]
        item["thread_id"] = row["thread_id"]
    return item


@router.get("/plans", summary="执行计划列表(兼容)")
async def list_execution_plans(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    diagnosis_id: str | None = Query(default=None, description="诊断 thread_id，筛选该次诊断下的执行计划"),
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
                if diagnosis_id:
                    where_clauses.append("thread_id = %s")
                    params.append(diagnosis_id)

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
                "diagnosis_id": row["thread_id"],
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
    except Exception:
        logger.exception("查询执行计划列表失败")
        return {"items": [], "total": 0}


@router.get("/tasks", summary="执行任务列表(兼容)")
async def list_tasks(
    enterprise_id: str | None = Query(default=None),
    thread_id: str | None = Query(default=None, description="诊断 thread_id，筛选该次诊断下的任务"),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """按企业/诊断拉平查询 ai_exec_task，供「任务执行」列表页展示任务行（非计划聚合）。"""
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_clauses = []
                params: list = []
                if enterprise_id:
                    where_clauses.append("tenant_id = %s")
                    params.append(enterprise_id)
                if thread_id:
                    where_clauses.append("thread_id = %s")
                    params.append(thread_id)
                if status:
                    where_clauses.append("status = %s")
                    params.append(status)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                await cur.execute(
                    f"""
                    SELECT COUNT(*) AS cnt FROM ai_exec_task {where_sql}
                    """,
                    params,
                )
                total_row = await cur.fetchone()
                total = int(total_row["cnt"]) if total_row else 0

                await cur.execute(
                    f"""
                    SELECT COALESCE(status, 'pending') AS st, COUNT(*)::int AS cnt
                    FROM ai_exec_task
                    {where_sql}
                    GROUP BY COALESCE(status, 'pending')
                    """,
                    params,
                )
                stat_rows = await cur.fetchall()
                stats: dict[str, int] = {
                    "pending": 0,
                    "ready": 0,
                    "running": 0,
                    "paused": 0,
                    "completed": 0,
                    "failed": 0,
                    "cancelled": 0,
                }
                for sr in stat_rows or []:
                    k = str(sr["st"]).lower()
                    if k in stats:
                        stats[k] = int(sr["cnt"])

                await cur.execute(
                    f"""
                    SELECT task_id, plan_id, thread_id, task_name, description, priority, status,
                           assignee_user_id, assignee_dept_id, deadline, created_at, related_resources
                    FROM ai_exec_task
                    {where_sql}
                    ORDER BY created_at DESC
                    OFFSET %s LIMIT %s
                    """,
                    params + [skip, limit],
                )
                rows = await cur.fetchall()

        items = [_task_row_to_api_item(row, include_plan_meta=True) for row in rows]

        return {"items": items, "total": total, "stats": stats}
    except Exception:
        logger.exception("查询执行任务列表失败")
        return {
            "items": [],
            "total": 0,
            "stats": {
                "pending": 0,
                "ready": 0,
                "running": 0,
                "paused": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
            },
        }


@router.get("/tasks/{task_id}", summary="执行任务详情(兼容)")
async def get_task_detail(task_id: str):
    """单条任务完整信息，供详情页展示业务内容（标题、说明、实施步骤、指派等）。"""
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT task_id, plan_id, thread_id, tenant_id, store_id, task_name, description,
                           priority, status, assignee_user_id, assignee_dept_id, deadline, created_at,
                           related_resources
                    FROM ai_exec_task
                    WHERE task_id = %s
                    """,
                    (task_id,),
                )
                row = await cur.fetchone()
    except Exception as e:
        logger.exception("查询任务详情失败")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试") from e

    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    base = _task_row_to_api_item(row, include_plan_meta=True)
    related = row.get("related_resources")
    rr = related if isinstance(related, dict) else {}
    return {
        **base,
        "tenant_id": row.get("tenant_id"),
        "store_id": row.get("store_id"),
        "priority": row.get("priority"),
        "related_resources": rr,
    }


@router.get("/plans/{plan_id}", summary="执行计划摘要(兼容)")
async def get_plan_summary(plan_id: str):
    """兼容前端 GET /execution/plans/{planId}。

    计划状态由 ai_exec_task 行聚合得到；采纳方案后任务由 execute 节点自动创建/派发，无单独「启动计划」步骤。
    """
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
        logger.exception("查询执行计划失败")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试") from e


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
                    SELECT task_id, plan_id, thread_id, task_name, description, priority, status,
                           assignee_user_id, assignee_dept_id, deadline, created_at, related_resources
                    FROM ai_exec_task
                    {where}
                    ORDER BY created_at
                    """,
                    params,
                )
                rows = await cur.fetchall()

        items = [_task_row_to_api_item(row, include_plan_meta=True) for row in rows]

        return {"items": items, "total": len(items)}
    except Exception:
        logger.exception("查询任务列表失败")
        return {"items": [], "total": 0}


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
        logger.exception("完成任务失败 task_id=%s", task_id)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试") from e


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
        logger.exception("标记任务失败时出错 task_id=%s", task_id)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试") from e


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
        logger.exception("重试任务失败 task_id=%s", task_id)
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试") from e
