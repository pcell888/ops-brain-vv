"""服务启动时的异步任务恢复（queued/running 入队；failed 且未占用过启动重试的再入队一次）。"""

from __future__ import annotations

import logging

from src.core.async_job_meta_repo import (
    claim_failed_job_startup_retry,
    list_recoverable_jobs,
)
from src.runtime.running_tasks import running_tasks
from src.runtime.thread_enterprise import register_thread_enterprise
from src.worker.arq_queue import reenqueue_job

logger = logging.getLogger(__name__)


async def reconcile_pending_jobs(limit: int = 200) -> int:
    jobs = await list_recoverable_jobs(limit=limit)
    recovered = 0
    for job in jobs:
        job_id = str(job.get("job_id") or "")
        thread_id = str(job.get("thread_id") or "")
        tenant_id = str(job.get("tenant_id") or "")
        job_kind = str(job.get("job_kind") or "")
        status = str(job.get("status") or "").strip().lower()
        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        if not (job_id and thread_id and tenant_id and job_kind):
            continue
        if status == "failed":
            if not await claim_failed_job_startup_retry(job_id):
                continue
        if not payload:
            payload = {"thread_id": thread_id, "tenant_id": tenant_id}
        try:
            actual_job_id = await reenqueue_job(job_kind=job_kind, payload=payload, job_id=job_id)
            await running_tasks.register_job(thread_id, tenant_id, actual_job_id)
            if job_kind == "diagnosis":
                register_thread_enterprise(thread_id, tenant_id)
            recovered += 1
        except Exception as e:
            logger.warning("恢复任务失败 job_id=%s kind=%s err=%s", job_id, job_kind, e)
    if recovered:
        logger.info("已恢复异步任务 %d 个", recovered)
    return recovered

