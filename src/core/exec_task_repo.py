"""执行任务落库 — 诊断系统本地 Postgres，留存方案执行任务明细。"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from psycopg.rows import dict_row

from src.core.db_init import ensure_ai_exec_task
from src.core.db_pool import get_conn

logger = logging.getLogger(__name__)


def _gen_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


async def save_exec_tasks(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    plan_id: str,
    tasks: list[dict],
) -> list[str]:
    """批量写入执行任务到本地库。返回生成的 task_id 列表。"""
    if not tasks:
        return []
    await ensure_ai_exec_task()
    task_ids = []
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                for t in tasks:
                    task_id = t.get("task_id") or _gen_task_id()
                    task_ids.append(task_id)
                    deadline = t.get("deadline")
                    if isinstance(deadline, str):
                        deadline_str = deadline[:200]
                    else:
                        deadline_str = None
                    deadline_at = t.get("deadline_at")
                    deadline_at_dt = None
                    if isinstance(deadline_at, str) and deadline_at.strip():
                        try:
                            deadline_at_dt = datetime.fromisoformat(deadline_at.replace("Z", "+00:00"))
                        except ValueError:
                            deadline_at_dt = None
                    related = t.get("related_resources")
                    related_json = json.dumps(related if isinstance(related, dict) else {}, ensure_ascii=False)
                    task_status = (t.get("status") or "pending")[:20]
                    await cur.execute(
                        """
                        INSERT INTO ai_exec_task
                        (task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                         assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at, priority, status, related_resources)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (task_id) DO UPDATE SET
                            task_name = EXCLUDED.task_name,
                            description = EXCLUDED.description,
                            assignee_user_id = EXCLUDED.assignee_user_id,
                            assignee_account_id = EXCLUDED.assignee_account_id,
                            assignee_dept_id = EXCLUDED.assignee_dept_id,
                            deadline = EXCLUDED.deadline,
                            deadline_at = EXCLUDED.deadline_at,
                            priority = EXCLUDED.priority,
                            related_resources = EXCLUDED.related_resources
                        """,
                        (
                            task_id,
                            thread_id[:128],
                            tenant_id[:32],
                            store_id[:32],
                            plan_id[:32],
                            (t.get("task_name") or "")[:500],
                            (t.get("description") or "")[:10000] if t.get("description") else None,
                            t.get("assignee_user_id"),
                            str(t.get("assignee_account_id", ""))[:32],
                            str(t.get("assignee_dept_id", ""))[:32],
                            deadline_str,
                            deadline_at_dt,
                            str(t.get("priority", ""))[:20],
                            task_status,
                            related_json,
                        ),
                    )
            await conn.commit()
    except Exception as e:
        logger.warning("执行任务落库失败: %s", e)
    return task_ids


async def update_task_status(task_ids: list[str], status: str) -> None:
    """批量更新任务状态。"""
    if not task_ids:
        return
    await ensure_ai_exec_task()
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE ai_exec_task
                    SET status = %s
                    WHERE task_id = ANY(%s)
                    """,
                    (status[:20], task_ids),
                )
            await conn.commit()
    except Exception as e:
        logger.warning("更新任务状态失败: %s", e)


async def get_tasks_by_plan_id(tenant_id: str, store_id: str, plan_id: str, status: str | None = None) -> list[dict]:
    """获取指定方案的任务列表。"""
    await ensure_ai_exec_task()
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                if status:
                    await cur.execute(
                        """
                        SELECT task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                               assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at,
                               priority, status, related_resources, created_at
                        FROM ai_exec_task
                        WHERE tenant_id = %s AND store_id = %s AND plan_id = %s AND status = %s
                        ORDER BY created_at
                        """,
                        (tenant_id[:32], store_id[:32], plan_id[:32], status[:20]),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                               assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at,
                               priority, status, related_resources, created_at
                        FROM ai_exec_task
                        WHERE tenant_id = %s AND store_id = %s AND plan_id = %s
                        ORDER BY created_at
                        """,
                        (tenant_id[:32], store_id[:32], plan_id[:32]),
                    )
                rows = await cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.warning("获取任务列表失败: %s", e)
        return []


async def list_distinct_plan_ids_for_thread(thread_id: str) -> list[str]:
    """同一诊断下已落库的执行任务涉及的去重 plan_id（用于采纳互斥校验）。"""
    if not (thread_id or "").strip():
        return []
    await ensure_ai_exec_task()
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT DISTINCT plan_id FROM ai_exec_task
                    WHERE thread_id = %s AND COALESCE(TRIM(plan_id), '') <> ''
                    """,
                    (thread_id[:128],),
                )
                rows = await cur.fetchall()
    except Exception as e:
        logger.warning("查询诊断下 plan_id 列表失败 [%s]: %s", thread_id, e)
        return []
    out: list[str] = []
    for row in rows or []:
        pid = str((row or {}).get("plan_id") or "").strip()
        if pid and pid not in out:
            out.append(pid)
    return out


async def get_task_stats_by_thread(thread_id: str) -> dict[str, int]:
    """按 thread_id 聚合各状态任务数量。"""
    stats: dict[str, int] = {
        "pending": 0, "ready": 0, "running": 0, "paused": 0,
        "completed": 0, "failed": 0, "cancelled": 0,
    }
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COALESCE(status, 'pending') AS st, COUNT(*)::int AS cnt "
                    "FROM ai_exec_task WHERE thread_id = %s "
                    "GROUP BY COALESCE(status, 'pending')",
                    (thread_id,),
                )
                for row in await cur.fetchall():
                    key = str(row[0]).lower()
                    if key in stats:
                        stats[key] = int(row[1])
    except Exception as e:
        logger.warning("获取任务统计失败 [%s]: %s", thread_id, e)
    return stats


async def get_team_size_by_thread(thread_id: str) -> int:
    """按 thread_id 统计不同 assignee 数量。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(DISTINCT assignee_user_id)::int FROM ai_exec_task "
                    "WHERE thread_id = %s AND assignee_user_id IS NOT NULL",
                    (thread_id,),
                )
                row = await cur.fetchone()
                return int(row[0]) if row else 0
    except Exception as e:
        logger.warning("获取团队人数失败 [%s]: %s", thread_id, e)
        return 0


async def list_tasks_by_thread(
    thread_id: str,
    columns: str = "task_name, status, description, deadline",
) -> list[dict]:
    """按 thread_id 查询任务列表，默认仅返回复盘/报告所需字段。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT {columns} FROM ai_exec_task WHERE thread_id = %s ORDER BY created_at ASC",
                    (thread_id,),
                )
                rows = await cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                return [dict(zip(col_names, row)) for row in rows]
    except Exception as e:
        logger.warning("获取任务列表失败 [%s]: %s", thread_id, e)
        return []
