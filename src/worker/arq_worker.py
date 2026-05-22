from __future__ import annotations

import asyncio

from arq.connections import RedisSettings

from src.core.logging_setup import setup_logging, setup_mcp_logging

# Worker 进程同样需要初始化日志，否则推送日志不会落盘
setup_logging("ops-brain")
setup_mcp_logging()
from urllib.parse import urlparse

from src.runtime.running_tasks import running_tasks
from src.repositories.async_job_meta import (
    mark_cancelled,
    mark_failed,
    mark_running,
    mark_succeeded,
)
from src.core.config import get_settings


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    u = urlparse(settings.redis_url)
    ssl = u.scheme == "rediss"
    db = 0
    if u.path and u.path.strip("/"):
        try:
            db = int(u.path.strip("/"))
        except ValueError:
            db = 0
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        database=db,
        password=u.password,
        ssl=ssl,
    )


async def _mark_job_after_run_or_cancel(thread_id: str, job_id: str) -> None:
    """正常跑完主体后：按是否请求取消标记 succeeded / cancelled。"""
    if not job_id:
        return
    if await running_tasks.is_cancel_requested(thread_id):
        await mark_cancelled(job_id)
    else:
        await mark_succeeded(job_id)


async def _mark_job_on_async_cancel(thread_id: str, job_id: str) -> None:
    """asyncio.CancelledError：区分用户取消与进程中断，禁止误标 succeeded。"""
    if not job_id:
        return
    if await running_tasks.is_cancel_requested(thread_id):
        await mark_cancelled(job_id)
    else:
        await mark_failed(job_id, "任务已被中断（例如 Worker 关闭或收到停止信号）")


async def job_run_diagnosis(ctx: dict, payload: dict) -> None:
    from src.runtime.diagnosis_stream_runner import run_diagnosis_with_stream
    from src.runtime.thread_enterprise import unregister_thread

    thread_id = str(payload["thread_id"])
    job_id = str(payload.get("job_id") or "")
    try:
        if job_id:
            await mark_running(job_id)
        await run_diagnosis_with_stream(
            thread_id=thread_id,
            tenant_id=str(payload["tenant_id"]),
            store_id=str(payload["store_id"]),
            trigger_type=str(payload["trigger_type"]),
            triggered_by=payload.get("triggered_by"),
            selected_dimensions=payload.get("selected_dimensions"),
            selected_indicators=payload.get("selected_indicators"),
            auth_token=payload.get("auth_token"),
        )
        await _mark_job_after_run_or_cancel(thread_id, job_id)
    except asyncio.CancelledError:
        await _mark_job_on_async_cancel(thread_id, job_id)
        raise
    except Exception as e:
        if job_id:
            await mark_failed(job_id, str(e))
        raise
    finally:
        await running_tasks.unregister_task(thread_id)
        unregister_thread(thread_id)


async def job_resume_after_adoption(ctx: dict, payload: dict) -> None:
    from src.services.solution_service import resume_after_adoption
    from src.runtime.thread_enterprise import unregister_thread

    thread_id = str(payload["thread_id"])
    job_id = str(payload.get("job_id") or "")
    try:
        if job_id:
            await mark_running(job_id)
        await resume_after_adoption(thread_id)
        await _mark_job_after_run_or_cancel(thread_id, job_id)
    except asyncio.CancelledError:
        await _mark_job_on_async_cancel(thread_id, job_id)
        raise
    except Exception as e:
        if job_id:
            await mark_failed(job_id, str(e))
        raise
    finally:
        await running_tasks.unregister_task(thread_id)
        unregister_thread(thread_id)


async def job_resume_track_effects(ctx: dict, payload: dict) -> None:
    from src.services import review_service
    from src.runtime.thread_enterprise import unregister_thread

    thread_id = str(payload["thread_id"])
    job_id = str(payload.get("job_id") or "")
    try:
        if job_id:
            await mark_running(job_id)
        await review_service.resume_track_effects(thread_id)
        await _mark_job_after_run_or_cancel(thread_id, job_id)
    except asyncio.CancelledError:
        await _mark_job_on_async_cancel(thread_id, job_id)
        raise
    except Exception as e:
        if job_id:
            await mark_failed(job_id, str(e))
        raise
    finally:
        await running_tasks.unregister_task(thread_id)
        unregister_thread(thread_id)


class WorkerSettings:
    functions = [job_run_diagnosis, job_resume_after_adoption, job_resume_track_effects]
    redis_settings = _redis_settings()
    job_timeout = 60 * 60 * 2
    max_tries = 1

