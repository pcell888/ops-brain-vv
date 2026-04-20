"""执行业务逻辑服务层。

封装执行计划和任务相关的核心业务逻辑，供 API 路由层调用。
"""

from __future__ import annotations

import logging
from datetime import timedelta

from psycopg.rows import dict_row

from src.core.datetime_cn import serialize_instant_cn, to_utc_aware
from src.core.db_pool import get_conn

logger = logging.getLogger(__name__)


# ── 辅助函数 ──────────────────────────────────────────────────


def _implementation_steps_from_related(related) -> list[str]:
    """从 related_resources 提取实施步骤。"""
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
    """派发状态以 related_resources.dispatch_status 为准，缺省为待派发。"""
    if isinstance(related, dict):
        ds = related.get("dispatch_status")
        if isinstance(ds, str) and ds.strip():
            return ds.strip().lower()[:32]
    return "pending"


def _recipient_from_row(row: dict) -> str:
    """接收者：优先业务用户 ID，否则部门 ID。"""
    uid = row.get("assignee_user_id")
    did = row.get("assignee_dept_id")
    if uid is not None:
        return str(uid)
    if did:
        return str(did)
    return ""


def _calculate_plan_status(completed: int, running: int, failed: int, pending: int, total: int) -> str:
    """根据任务统计计算计划状态。"""
    if completed == total:
        return "completed"
    elif running > 0:
        return "running"
    elif failed > 0 and pending == 0 and running == 0:
        return "failed"
    else:
        return "pending"


def _calculate_plan_progress(completed: int, total: int) -> int:
    """计算计划进度百分比。"""
    return round(completed / total * 100) if total > 0 else 0


# ── 核心业务逻辑 ──────────────────────────────────────────────


def task_row_to_dict(row: dict, *, include_plan_meta: bool = False) -> dict:
    """将任务数据库行转换为 API 响应格式。
    
    Args:
        row: 数据库查询结果行
        include_plan_meta: 是否包含 plan_id 和 thread_id
        
    Returns:
        格式化的任务字典
    """
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
        "scheduled_start": serialize_instant_cn(row["created_at"]) if row.get("created_at") else None,
        "scheduled_end": serialize_instant_cn(row["deadline"]) if row.get("deadline") not in (None, "") else None,
        "progress": _task_progress_percent(task_status, related),
        "assigned_to": recipient,
        "recipient": recipient,
        "dispatch_status": _dispatch_status_from_related(related),
        "dispatch_time": serialize_instant_cn(row["created_at"]) if row.get("created_at") else None,
    }
    
    if include_plan_meta:
        item["plan_id"] = row["plan_id"]
        item["thread_id"] = row["thread_id"]
    
    return item


async def get_execution_plans(
    tenant_id: str | None = None,
    thread_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """获取执行计划列表。
    
    Args:
        tenant_id: 租户ID
        thread_id: 诊断ID
        status: 计划状态过滤
        skip: 跳过记录数
        limit: 返回记录数
        
    Returns:
        (plans, total) - 计划列表和总数
    """
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_clauses = []
                params: list = []
                
                if tenant_id:
                    where_clauses.append("tenant_id = %s")
                    params.append(tenant_id)
                if thread_id:
                    where_clauses.append("thread_id = %s")
                    params.append(thread_id)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                # 查询计划列表
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

                # 查询总数
                await cur.execute(
                    f"SELECT COUNT(DISTINCT plan_id) FROM ai_exec_task {where_sql}",
                    params,
                )
                total = (await cur.fetchone() or {}).get("count", 0)

        # 构建计划列表
        items = []
        for row in rows:
            total_t = row["total_tasks"]
            completed_t = row["completed_tasks"]
            running_t = row["running_tasks"]
            failed_t = row["failed_tasks"]
            pending_t = row["pending_tasks"]

            plan_status = _calculate_plan_status(completed_t, running_t, failed_t, pending_t, total_t)
            progress = _calculate_plan_progress(completed_t, total_t)

            # 状态过滤
            if status and plan_status != status:
                continue

            created = row["created_at"]
            planned_end = None
            if created:
                planned_end = serialize_instant_cn(to_utc_aware(created) + timedelta(days=30))
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
                "planned_start": serialize_instant_cn(created) if created else None,
                "planned_end": planned_end,
            })

        return items, total
    except Exception:
        logger.exception("查询执行计划列表失败")
        return [], 0


async def get_execution_tasks(
    tenant_id: str | None = None,
    thread_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[dict], int, dict[str, int]]:
    """获取执行任务列表。
    
    Args:
        tenant_id: 租户ID
        thread_id: 诊断ID
        status: 任务状态过滤
        skip: 跳过记录数
        limit: 返回记录数
        
    Returns:
        (tasks, total, stats) - 任务列表、总数和统计信息
    """
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_clauses = []
                params: list = []
                
                if tenant_id:
                    where_clauses.append("tenant_id = %s")
                    params.append(tenant_id)
                if thread_id:
                    where_clauses.append("thread_id = %s")
                    params.append(thread_id)
                if status:
                    where_clauses.append("status = %s")
                    params.append(status)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                # 查询总数
                await cur.execute(
                    f"SELECT COUNT(*) AS cnt FROM ai_exec_task {where_sql}",
                    params,
                )
                total_row = await cur.fetchone()
                total = int(total_row["cnt"]) if total_row else 0

                # 查询统计信息
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

                # 查询任务列表
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

        items = [task_row_to_dict(row, include_plan_meta=True) for row in rows]

        return items, total, stats
    except Exception:
        logger.exception("查询执行任务列表失败")
        return [], 0, {
            "pending": 0,
            "ready": 0,
            "running": 0,
            "paused": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }


async def get_task_detail(task_id: str) -> dict | None:
    """获取任务详情。
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务详情字典，如果不存在返回 None
    """
    try:
        async with get_conn() as conn:
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
    except Exception:
        logger.exception("查询任务详情失败")
        return None

    if not row:
        return None

    base = task_row_to_dict(row, include_plan_meta=True)
    related = row.get("related_resources")
    rr = related if isinstance(related, dict) else {}
    
    return {
        **base,
        "tenant_id": row.get("tenant_id"),
        "store_id": row.get("store_id"),
        "priority": row.get("priority"),
        "related_resources": rr,
    }


async def get_plan_summary(plan_id: str) -> dict | None:
    """获取执行计划摘要。
    
    Args:
        plan_id: 计划ID
        
    Returns:
        计划摘要字典，如果不存在返回 None
    """
    try:
        async with get_conn() as conn:
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
    except Exception:
        logger.exception("查询执行计划失败")
        return None

    if not row:
        return None

    total_t = row["total_tasks"]
    completed_t = row["completed_tasks"]
    running_t = row["running_tasks"]
    failed_t = row["failed_tasks"]
    pending_t = row["pending_tasks"]

    plan_status = _calculate_plan_status(completed_t, running_t, failed_t, pending_t, total_t)
    progress = _calculate_plan_progress(completed_t, total_t)
    created = row["created_at"]
    planned_end = None
    if created:
        planned_end = serialize_instant_cn(to_utc_aware(created) + timedelta(days=30))

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
        "planned_start": serialize_instant_cn(created) if created else None,
        "planned_end": planned_end,
    }


async def get_plan_tasks(plan_id: str, status: str | None = None) -> tuple[list[dict], int]:
    """获取计划下的任务列表。
    
    Args:
        plan_id: 计划ID
        status: 任务状态过滤
        
    Returns:
        (tasks, total) - 任务列表和总数
    """
    try:
        async with get_conn() as conn:
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

        items = [task_row_to_dict(row, include_plan_meta=True) for row in rows]

        return items, len(items)
    except Exception:
        logger.exception("查询任务列表失败")
        return [], 0


async def update_task_status(task_id: str, new_status: str) -> bool:
    """更新任务状态。
    
    Args:
        task_id: 任务ID
        new_status: 新状态（completed, failed, running 等）
        
    Returns:
        是否更新成功
    """
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = %s WHERE task_id = %s",
                    (new_status, task_id),
                )
            await conn.commit()
        return True
    except Exception:
        logger.exception("更新任务状态失败 task_id=%s, status=%s", task_id, new_status)
        return False
