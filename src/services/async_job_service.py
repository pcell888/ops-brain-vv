"""异步任务元数据 — 供路由与 worker 统一通过 Service 写入，避免直连 repo。"""

from __future__ import annotations

from typing import Any

from src.repositories.async_job_meta import create_job, mark_cancelled_by_thread


async def register_enqueued_job(
    *,
    job_id: str,
    thread_id: str,
    tenant_id: str,
    job_kind: str,
    payload: dict[str, Any],
) -> None:
    await create_job(
        job_id=job_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
        job_kind=job_kind,
        payload=payload,
    )


async def mark_jobs_cancelled_for_thread(thread_id: str, reason: str = "cancel_requested") -> None:
    await mark_cancelled_by_thread(thread_id, reason)
