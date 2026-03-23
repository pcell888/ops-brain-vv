"""执行任务落库 — 诊断系统本地 Postgres，留存方案执行任务明细。"""

from __future__ import annotations

import json
import logging
import uuid

import psycopg

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_exec_task

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


def _gen_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


async def save_exec_tasks(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    plan_id: str,
    tasks: list[dict],
) -> None:
    """批量写入执行任务到本地库。tasks 中每项可有 task_id（来自业务端）或由本处生成。"""
    if not tasks:
        return
    await ensure_ai_exec_task()
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                for t in tasks:
                    task_id = t.get("task_id") or _gen_task_id()
                    deadline = t.get("deadline")
                    if isinstance(deadline, str):
                        deadline_str = deadline[:200]
                    else:
                        deadline_str = None
                    related = t.get("related_resources")
                    related_json = json.dumps(related if isinstance(related, (list, dict)) else [], ensure_ascii=False)
                    # 采纳方案后任务已推送业务侧，与 execute 节点一致：落库即为执行中（待人完成）
                    task_status = (t.get("status") or "running")[:20]
                    await cur.execute(
                        """
                        INSERT INTO ai_exec_task
                        (task_id, thread_id, tenant_id, store_id, plan_id, task_name, description,
                         assignee_user_id, assignee_account_id, assignee_dept_id, deadline, priority, status, related_resources)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (task_id) DO UPDATE SET
                            task_name = EXCLUDED.task_name,
                            description = EXCLUDED.description,
                            assignee_user_id = EXCLUDED.assignee_user_id,
                            assignee_account_id = EXCLUDED.assignee_account_id,
                            assignee_dept_id = EXCLUDED.assignee_dept_id,
                            deadline = EXCLUDED.deadline,
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
                            str(t.get("priority", ""))[:20],
                            task_status,
                            related_json,
                        ),
                    )
            await conn.commit()
    except Exception as e:
        logger.warning("执行任务落库失败: %s", e)
