"""异步任务元数据仓储（PG 真相源）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from psycopg.rows import dict_row

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"

ACTIVE_STATUSES = (JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)

RECONCILE_AUTO_RETRY_PAYLOAD_KEY = "_reconcile_auto_retry_used"


async def create_job(
    *,
    job_id: str,
    thread_id: str,
    tenant_id: str,
    job_kind: str,
    payload: dict[str, Any],
) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_async_job_meta (job_id, thread_id, tenant_id, job_kind, status, payload)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (job_id) DO UPDATE SET
                        thread_id = EXCLUDED.thread_id,
                        tenant_id = EXCLUDED.tenant_id,
                        job_kind = EXCLUDED.job_kind,
                        status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        error = NULL,
                        updated_at = NOW()
                    """,
                    (job_id, thread_id, tenant_id, job_kind, JOB_STATUS_QUEUED, payload_json),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("创建异步任务失败", job_id=job_id, thread_id=thread_id, job_kind=job_kind) from e


async def mark_running(job_id: str) -> None:
    await _mark(job_id, JOB_STATUS_RUNNING, error=None)


async def mark_succeeded(job_id: str) -> None:
    await _mark(job_id, JOB_STATUS_SUCCEEDED, error=None)


async def mark_failed(job_id: str, error: str) -> None:
    await _mark(job_id, JOB_STATUS_FAILED, error=error[:2000])


async def mark_cancelled(job_id: str, reason: str = "cancel_requested") -> None:
    await _mark(job_id, JOB_STATUS_CANCELLED, error=reason[:2000])


async def mark_cancelled_by_thread(thread_id: str, reason: str = "cancel_requested") -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE ai_async_job_meta
                       SET status = %s, error = %s, updated_at = NOW()
                     WHERE thread_id = %s AND status IN ('queued', 'running')
                    """,
                    (JOB_STATUS_CANCELLED, reason[:2000], thread_id),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("取消线程任务失败", thread_id=thread_id, reason=reason) from e


async def list_recoverable_jobs(limit: int = 200) -> list[dict]:
    """列出需在启动时重新入队的任务：queued/running，或尚未做过一次启动重试的 failed。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT job_id, thread_id, tenant_id, job_kind, status, payload, created_at, updated_at
                      FROM ai_async_job_meta
                     WHERE status IN ('queued', 'running')
                        OR (
                            status = 'failed'
                            AND COALESCE(payload->>%s, '') NOT IN ('true', '1')
                        )
                     ORDER BY updated_at ASC
                     LIMIT %s
                    """,
                    (RECONCILE_AUTO_RETRY_PAYLOAD_KEY, limit),
                )
                rows = await cur.fetchall()
                out: list[dict] = []
                for row in rows:
                    payload = row.get("payload")
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except Exception:
                            payload = {}
                    if not isinstance(payload, dict):
                        payload = {}
                    d = dict(row)
                    d["payload"] = payload
                    out.append(d)
                return out
    except Exception as e:
        raise AppError("查询可恢复任务失败", limit=limit) from e


async def claim_failed_job_startup_retry(job_id: str) -> bool:
    """将 failed 任务改为 queued 并打上「已用掉一次启动重试」；用于避免无限重试。成功返回 True。"""
    patch_json = json.dumps({RECONCILE_AUTO_RETRY_PAYLOAD_KEY: True}, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE ai_async_job_meta
                       SET status = %s,
                           error = NULL,
                           payload = payload || %s::jsonb,
                           updated_at = NOW()
                     WHERE job_id = %s
                       AND status = 'failed'
                       AND COALESCE(payload->>%s, '') NOT IN ('true', '1')
                    RETURNING job_id
                    """,
                    (
                        JOB_STATUS_QUEUED,
                        patch_json,
                        job_id,
                        RECONCILE_AUTO_RETRY_PAYLOAD_KEY,
                    ),
                )
                row = await cur.fetchone()
            await conn.commit()
        return row is not None
    except Exception as e:
        raise AppError("认领失败任务重试失败", job_id=job_id) from e


async def get_latest_job_by_thread(thread_id: str) -> dict | None:
    """按 thread_id 获取最新异步任务元数据。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT job_id, thread_id, tenant_id, job_kind, status, error, payload, created_at, updated_at
                      FROM ai_async_job_meta
                     WHERE thread_id = %s
                     ORDER BY updated_at DESC
                     LIMIT 1
                    """,
                    (thread_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                payload = row.get("payload")
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}
                if not isinstance(payload, dict):
                    payload = {}
                out = dict(row)
                out["payload"] = payload
                return out
    except Exception as e:
        raise AppError("查询最新异步任务失败", thread_id=thread_id) from e


async def _mark(job_id: str, status: str, error: str | None) -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE ai_async_job_meta
                       SET status = %s, error = %s, updated_at = NOW()
                     WHERE job_id = %s
                    """,
                    (status, error, job_id),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("更新任务状态失败", job_id=job_id, status=status) from e
