from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from urllib.parse import urlparse

try:
    from arq import create_pool  # pyright: ignore[reportMissingImports]
    from arq.connections import ArqRedis, RedisSettings  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
    create_pool = None
    ArqRedis = Any  # type: ignore[assignment,misc]
    RedisSettings = None
    _ARQ_IMPORT_ERROR = exc
else:
    _ARQ_IMPORT_ERROR = None

from src.core.config import get_settings
from src.core.job_meta_rotate import rotate_async_job_id_in_meta

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


def _redis_settings_from_url(redis_url: str) -> dict[str, Any]:
    u = urlparse(redis_url)
    ssl = u.scheme == "rediss"
    db = 0
    if u.path and u.path.strip("/"):
        try:
            db = int(u.path.strip("/"))
        except ValueError:
            db = 0
    return {
        "host": u.hostname or "localhost",
        "port": u.port or 6379,
        "database": db,
        "password": u.password,
        "ssl": ssl,
    }


def _ensure_arq_available() -> None:
    if _ARQ_IMPORT_ERROR is None:
        return
    raise RuntimeError(
        "缺少 arq 依赖，请先安装项目依赖（例如：uv sync 或 pip install -e .）。"
    ) from _ARQ_IMPORT_ERROR


async def get_arq_pool() -> ArqRedis:
    _ensure_arq_available()
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            settings = get_settings()
            redis_settings = RedisSettings(**_redis_settings_from_url(settings.redis_url))
            _pool = await create_pool(redis_settings)
        return _pool


async def enqueue_diagnosis_job(payload: dict[str, Any]) -> str:
    thread_id = str(payload["thread_id"])
    job_id = _make_job_id("diag", thread_id)
    payload_with_job = dict(payload)
    payload_with_job["job_id"] = job_id
    await _enqueue(job_name="job_run_diagnosis", payload=payload_with_job, job_id=job_id)
    return job_id


async def enqueue_adoption_job(*, thread_id: str) -> str:
    job_id = _make_job_id("adopt", thread_id)
    await _enqueue(
        job_name="job_resume_after_adoption",
        payload={"thread_id": thread_id, "job_id": job_id},
        job_id=job_id,
    )
    return job_id


async def enqueue_review_job(*, thread_id: str) -> str:
    job_id = _make_job_id("review", thread_id)
    await _enqueue(
        job_name="job_resume_track_effects",
        payload={"thread_id": thread_id, "job_id": job_id},
        job_id=job_id,
    )
    return job_id


def _job_id_prefix_for_kind(job_kind: str) -> str:
    if job_kind == "diagnosis":
        return "diag"
    if job_kind == "adoption":
        return "adopt"
    if job_kind == "review":
        return "review"
    raise ValueError(f"unknown job_kind: {job_kind}")


def _job_name_for_kind(job_kind: str) -> str:
    if job_kind == "diagnosis":
        return "job_run_diagnosis"
    if job_kind == "adoption":
        return "job_resume_after_adoption"
    if job_kind == "review":
        return "job_resume_track_effects"
    raise ValueError(f"unknown job_kind: {job_kind}")


async def reenqueue_job(*, job_kind: str, payload: dict[str, Any], job_id: str) -> str:
    """重新入队；若 arq 因 Redis 上旧 job_id 残留拒绝入队，则换新 job_id 并更新 PG。返回实际使用的 job_id。"""
    payload_with_job = dict(payload)
    payload_with_job["job_id"] = job_id
    job_name = _job_name_for_kind(job_kind)
    enqueued = await _enqueue_returning(job_name=job_name, payload=payload_with_job, job_id=job_id)
    if enqueued:
        return job_id
    thread_id = str(payload_with_job.get("thread_id") or "")
    if not thread_id:
        logger.error("reenqueue_job 无法轮换 job_id：payload 缺少 thread_id job_kind=%s", job_kind)
        raise RuntimeError("reenqueue_job: missing thread_id for job_id rotation")
    prefix = _job_id_prefix_for_kind(job_kind)
    new_job_id = _make_job_id(prefix, thread_id)
    logger.warning(
        "arq 拒绝重复 job_id=%s（多为历史 result 键未过期），已换新 id=%s 并入队",
        job_id,
        new_job_id,
    )
    await rotate_async_job_id_in_meta(old_job_id=job_id, new_job_id=new_job_id, thread_id=thread_id)
    payload_with_job["job_id"] = new_job_id
    if not await _enqueue_returning(job_name=job_name, payload=payload_with_job, job_id=new_job_id):
        raise RuntimeError(f"arq enqueue failed after job_id rotation new_id={new_job_id}")
    return new_job_id


def _make_job_id(prefix: str, thread_id: str) -> str:
    return f"{prefix}:{thread_id}:{time.time_ns()}"


async def _enqueue(*, job_name: str, payload: dict[str, Any], job_id: str) -> None:
    ok = await _enqueue_returning(job_name=job_name, payload=payload, job_id=job_id)
    if not ok:
        raise RuntimeError(f"arq refused enqueue job_name={job_name} job_id={job_id}")


async def _enqueue_returning(*, job_name: str, payload: dict[str, Any], job_id: str) -> bool:
    pool = await get_arq_pool()
    job = await pool.enqueue_job(job_name, payload, _job_id=job_id)
    return job is not None

