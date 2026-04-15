"""每日任务到期/超期检查 — 扫描未完成的执行任务，推送提醒。"""

from __future__ import annotations

import asyncio
import logging

import psycopg.rows

from src.agent.tools import mcp_call

logger = logging.getLogger(__name__)


async def _get_approaching_tasks() -> list[dict]:
    """获取距截止日 <=1 天且尚未完成的任务（需业务库 ai_diagnosis_task 表支持）。"""
    from src.core.db_pool import get_conn
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT task_id, tenant_id, store_id, task_name,
                           assignee_user_id, assignee_account_id, deadline
                    FROM ai_diagnosis_task
                    WHERE status NOT IN ('completed', 'cancelled')
                      AND deadline IS NOT NULL
                      AND deadline BETWEEN NOW() AND NOW() + INTERVAL '1 day'
                    """
                )
                return await cur.fetchall()
    except Exception as e:
        logger.warning("查询即将到期任务失败（表可能不存在）: %s", e)
        return []


async def _get_overdue_tasks() -> list[dict]:
    """获取已超期且尚未完成的任务。"""
    from src.core.db_pool import get_conn
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT task_id, tenant_id, store_id, task_name,
                           assignee_user_id, assignee_account_id, deadline
                    FROM ai_diagnosis_task
                    WHERE status NOT IN ('completed', 'cancelled')
                      AND deadline IS NOT NULL
                      AND deadline < NOW()
                    """
                )
                return await cur.fetchall()
    except Exception as e:
        logger.warning("查询超期任务失败（表可能不存在）: %s", e)
        return []


async def _send_reminders(tasks: list[dict], reminder_type: str):
    for t in tasks:
        tenant_id = t.get("tenant_id", "")
        account_id = t.get("assignee_account_id") or str(t.get("assignee_user_id", ""))
        if not account_id:
            continue
        try:
            await mcp_call("notify-server", "send_task_reminder", {
                "tenant_id": tenant_id,
                "user_id": t.get("assignee_user_id", 0),
                "account_id": account_id,
                "task_id": t.get("task_id", ""),
                "reminder_type": reminder_type,
                "message": f"任务「{t.get('task_name', '')}」{'已超过截止日期' if reminder_type == 'overdue' else '即将到期'}，请及时处理。",
            })
        except Exception as e:
            logger.warning("发送%s提醒失败 [%s]: %s", reminder_type, t.get("task_id"), e)


async def check_task_deadlines():
    """每日任务截止日期检查入口。"""
    logger.info("===== 开始每日任务到期检查 =====")

    approaching, overdue = await asyncio.gather(
        _get_approaching_tasks(),
        _get_overdue_tasks(),
    )

    if approaching:
        logger.info("发现 %d 个即将到期任务", len(approaching))
        await _send_reminders(approaching, "approaching_deadline")

    if overdue:
        logger.info("发现 %d 个已超期任务", len(overdue))
        await _send_reminders(overdue, "overdue")

    logger.info("===== 每日任务到期检查完成 =====")
