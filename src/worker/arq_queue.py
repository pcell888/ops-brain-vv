from __future__ import annotations

import asyncio
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


async def reenqueue_job(*, job_kind: str, payload: dict[str, Any], job_id: str) -> None:
    payload_with_job = dict(payload)
    payload_with_job["job_id"] = job_id
    if job_kind == "diagnosis":
        await _enqueue(job_name="job_run_diagnosis", payload=payload_with_job, job_id=job_id)
        return
    if job_kind == "adoption":
        await _enqueue(job_name="job_resume_after_adoption", payload=payload_with_job, job_id=job_id)
        return
    if job_kind == "review":
        await _enqueue(job_name="job_resume_track_effects", payload=payload_with_job, job_id=job_id)
        return
    raise ValueError(f"unknown job_kind: {job_kind}")


def _make_job_id(prefix: str, thread_id: str) -> str:
    return f"{prefix}:{thread_id}:{time.time_ns()}"


async def _enqueue(*, job_name: str, payload: dict[str, Any], job_id: str) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job(job_name, payload, _job_id=job_id)

