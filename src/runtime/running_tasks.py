"""运行中诊断任务存储（本地 Task + Redis 标记）。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import redis.asyncio as aioredis

from src.core.config import CN_TZ
from src.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_TASK_TTL_SECONDS = 6 * 60 * 60
_TENANT_ACTIVE_TTL_SECONDS = 6 * 60 * 60
_TASK_CANCEL_LOCK_TTL_SECONDS = 30
_TASK_CANCEL_REQUEST_TTL_SECONDS = _TASK_TTL_SECONDS


class RunningTaskStore:
    """任务存储：本地 Task + Redis 运行标记/分布式锁。"""

    def __init__(self):
        self._local_tasks: dict[str, asyncio.Task] = {}
        self._local_thread_tenant: dict[str, str] = {}
        self._local_cancel_requested_until: dict[str, float] = {}

    def _task_key(self, thread_id: str) -> str:
        return f"opsbrain:task:running:{thread_id}"

    def _tenant_active_key(self, tenant_id: str) -> str:
        return f"opsbrain:task:tenant-active:{tenant_id}"

    def _tenant_threads_key(self, tenant_id: str) -> str:
        return f"opsbrain:task:tenant-threads:{tenant_id}"

    def _cancel_lock_key(self, thread_id: str) -> str:
        return f"opsbrain:task:cancel-lock:{thread_id}"

    def _cancel_requested_key(self, thread_id: str) -> str:
        return f"opsbrain:task:cancel-requested:{thread_id}"

    async def _get_redis(self) -> aioredis.Redis | None:
        try:
            return await get_redis()
        except Exception as e:
            logger.warning("获取 Redis 连接失败: %s", e)
            return None

    def get(self, thread_id: str):
        return self._local_tasks.get(thread_id)

    def __contains__(self, thread_id: str):
        task = self._local_tasks.get(thread_id)
        return bool(task and not task.done())

    def __setitem__(self, thread_id: str, task: asyncio.Task):
        self._local_tasks[thread_id] = task

    def pop(self, thread_id: str, default=None):
        self._local_thread_tenant.pop(thread_id, None)
        self._local_cancel_requested_until.pop(thread_id, None)
        return self._local_tasks.pop(thread_id, default)

    async def try_claim_tenant(self, tenant_id: str, thread_id: str) -> tuple[bool, str | None]:
        rd = await self._get_redis()
        if rd is None:
            for tid, ten in self._local_thread_tenant.items():
                if ten != tenant_id:
                    continue
                task = self._local_tasks.get(tid)
                if task is not None and not task.done():
                    return False, tid
            return True, None
        key = self._tenant_active_key(tenant_id)
        try:
            ok = await rd.set(key, thread_id, ex=_TENANT_ACTIVE_TTL_SECONDS, nx=True)
            if ok:
                return True, None
            existing = await rd.get(key)
            return False, existing
        except Exception as e:
            logger.debug("租户任务抢占失败 tenant=%s: %s", tenant_id, e)
            return True, None

    async def release_tenant_claim(self, tenant_id: str, thread_id: str) -> None:
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            key = self._tenant_active_key(tenant_id)
            current = await rd.get(key)
            if current == thread_id:
                await rd.delete(key)
        except Exception:
            pass

    async def register_task(self, thread_id: str, task: asyncio.Task, tenant_id: str | None = None) -> None:
        self._local_tasks[thread_id] = task
        if tenant_id:
            self._local_thread_tenant[thread_id] = tenant_id
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            payload = {"thread_id": thread_id, "tenant_id": tenant_id, "ts": datetime.now(CN_TZ).isoformat()}
            await rd.set(self._task_key(thread_id), json.dumps(payload, ensure_ascii=False), ex=_TASK_TTL_SECONDS)
            if tenant_id:
                await rd.set(self._tenant_active_key(tenant_id), thread_id, ex=_TENANT_ACTIVE_TTL_SECONDS)
                tenant_threads_key = self._tenant_threads_key(tenant_id)
                await rd.sadd(tenant_threads_key, thread_id)
                await rd.expire(tenant_threads_key, _TENANT_ACTIVE_TTL_SECONDS)
        except Exception as e:
            logger.debug("注册运行任务失败 thread=%s: %s", thread_id, e)

    async def register_job(self, thread_id: str, tenant_id: str, job_id: str) -> None:
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            payload = {
                "thread_id": thread_id,
                "tenant_id": tenant_id,
                "job_id": job_id,
                "ts": datetime.now(CN_TZ).isoformat(),
            }
            await rd.set(self._task_key(thread_id), json.dumps(payload, ensure_ascii=False), ex=_TASK_TTL_SECONDS)
            await rd.set(self._tenant_active_key(tenant_id), thread_id, ex=_TENANT_ACTIVE_TTL_SECONDS)
            tenant_threads_key = self._tenant_threads_key(tenant_id)
            await rd.sadd(tenant_threads_key, thread_id)
            await rd.expire(tenant_threads_key, _TENANT_ACTIVE_TTL_SECONDS)
            self._local_thread_tenant[thread_id] = tenant_id
        except Exception as e:
            logger.debug("注册运行任务(job)失败 thread=%s: %s", thread_id, e)

    async def unregister_task(self, thread_id: str) -> None:
        tenant_id = self._local_thread_tenant.pop(thread_id, None)
        self._local_tasks.pop(thread_id, None)
        self._local_cancel_requested_until.pop(thread_id, None)
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            if not tenant_id:
                raw = await rd.get(self._task_key(thread_id))
                if raw:
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict):
                            tenant_id = parsed.get("tenant_id")
                    except Exception:
                        pass
            await rd.delete(self._task_key(thread_id))
            await rd.delete(self._cancel_requested_key(thread_id))
            if tenant_id:
                key = self._tenant_active_key(tenant_id)
                current = await rd.get(key)
                if current == thread_id:
                    await rd.delete(key)
                tenant_threads_key = self._tenant_threads_key(tenant_id)
                await rd.srem(tenant_threads_key, thread_id)
        except Exception as e:
            logger.debug("反注册运行任务失败 thread=%s: %s", thread_id, e)

    async def is_running(self, thread_id: str) -> bool:
        task = self._local_tasks.get(thread_id)
        if task is not None and not task.done():
            return True
        rd = await self._get_redis()
        if rd is None:
            return False
        try:
            return bool(await rd.exists(self._task_key(thread_id)))
        except Exception:
            return False

    async def get_active_thread_for_tenant(self, tenant_id: str) -> str | None:
        rd = await self._get_redis()
        if rd is None:
            for tid, ten in self._local_thread_tenant.items():
                if ten != tenant_id:
                    continue
                task = self._local_tasks.get(tid)
                if task is not None and not task.done():
                    return tid
            return None
        try:
            return await rd.get(self._tenant_active_key(tenant_id))
        except Exception:
            return None

    async def get_running_threads_for_tenant(self, tenant_id: str) -> list[str]:
        local: list[str] = []
        for tid, ten in self._local_thread_tenant.items():
            if ten != tenant_id:
                continue
            task = self._local_tasks.get(tid)
            if task is not None and not task.done():
                local.append(tid)

        rd = await self._get_redis()
        if rd is None:
            return local
        try:
            tenant_threads_key = self._tenant_threads_key(tenant_id)
            members = await rd.smembers(tenant_threads_key)
            if not members:
                return local
            remote_running: list[str] = []
            for tid in members:
                if await rd.exists(self._task_key(tid)):
                    remote_running.append(tid)
                else:
                    await rd.srem(tenant_threads_key, tid)
            merged = set(local)
            merged.update(remote_running)
            return list(merged)
        except Exception:
            return local

    async def acquire_cancel_lock(self, thread_id: str) -> bool:
        rd = await self._get_redis()
        if rd is None:
            return True
        try:
            ok = await rd.set(self._cancel_lock_key(thread_id), "1", ex=_TASK_CANCEL_LOCK_TTL_SECONDS, nx=True)
            return bool(ok)
        except Exception:
            return True

    async def request_cancel(self, thread_id: str) -> None:
        now = asyncio.get_running_loop().time()
        self._local_cancel_requested_until[thread_id] = now + _TASK_CANCEL_REQUEST_TTL_SECONDS
        local_task = self._local_tasks.get(thread_id)
        if local_task is not None and not local_task.done():
            local_task.cancel()
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            await rd.set(self._cancel_requested_key(thread_id), "1", ex=_TASK_CANCEL_REQUEST_TTL_SECONDS)
        except Exception:
            pass

    async def is_cancel_requested(self, thread_id: str) -> bool:
        now = asyncio.get_running_loop().time()
        until = self._local_cancel_requested_until.get(thread_id)
        if until is not None:
            if until > now:
                return True
            self._local_cancel_requested_until.pop(thread_id, None)
        rd = await self._get_redis()
        if rd is None:
            return False
        try:
            return bool(await rd.exists(self._cancel_requested_key(thread_id)))
        except Exception:
            return False

    async def release_cancel_lock(self, thread_id: str) -> None:
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            await rd.delete(self._cancel_lock_key(thread_id))
        except Exception:
            pass


running_tasks = RunningTaskStore()
