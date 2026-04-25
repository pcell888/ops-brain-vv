"""待复盘调度记录管理 — 记录哪些诊断会话需要延迟执行效果追踪。"""

from __future__ import annotations

import logging
from datetime import datetime

import psycopg.rows

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def save_pending_review(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    review_due_date: datetime,
) -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_pending_review (thread_id, tenant_id, store_id, review_due_date)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        review_due_date = EXCLUDED.review_due_date,
                        status = 'pending'
                    """,
                    (thread_id[:128], tenant_id[:32], store_id[:32], review_due_date),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("待复盘记录保存失败", thread_id=thread_id, tenant_id=tenant_id) from e


async def get_due_reviews() -> list[dict]:
    """返回复盘已到期（review_due_date <= 当前时刻）且 status='pending' 的记录。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT thread_id, tenant_id, store_id, review_due_date
                    FROM ai_pending_review
                    WHERE status = 'pending'
                      AND review_due_date <= NOW()
                    """
                )
                return await cur.fetchall()
    except Exception as e:
        raise AppError("查询到期复盘记录失败") from e


async def mark_review_done(thread_id: str) -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_pending_review SET status = 'completed' WHERE thread_id = %s",
                    (thread_id,),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("更新复盘状态失败", thread_id=thread_id) from e


async def get_pending_review(tenant_id: str, thread_id: str) -> dict | None:
    """返回 status=pending 的待复盘记录（用于效果追踪列表展示「待到期」行）。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT thread_id, tenant_id, review_due_date, status, created_at
                    FROM ai_pending_review
                    WHERE tenant_id = %s AND thread_id = %s AND status = 'pending'
                    """,
                    (tenant_id[:32], thread_id[:128]),
                )
                row = await cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        raise AppError("查询待复盘记录失败", tenant_id=tenant_id, thread_id=thread_id) from e


async def get_pending_review_by_thread(thread_id: str) -> dict | None:
    """按 thread_id 查 pending（摘要接口无 tenant 上下文）。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT thread_id, tenant_id, review_due_date, status, created_at
                    FROM ai_pending_review
                    WHERE thread_id = %s AND status = 'pending'
                    """,
                    (thread_id[:128],),
                )
                row = await cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        raise AppError("查询待复盘记录失败", thread_id=thread_id) from e


async def cancel_pending_review(thread_id: str) -> bool:
    """取消待复盘记录，返回是否实际取消了记录。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_pending_review SET status = 'cancelled' "
                    "WHERE thread_id = %s AND status = 'pending' RETURNING thread_id",
                    (thread_id,),
                )
                row = await cur.fetchone()
            await conn.commit()
            return row is not None
    except Exception as e:
        raise AppError("取消复盘失败", thread_id=thread_id) from e
