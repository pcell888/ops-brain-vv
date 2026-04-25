"""诊断/方案等实时进度缓存（内存 + Redis），与传输层无关。"""

from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis

from src.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_PROGRESS_TTL_SECONDS = 60 * 60
_PROGRESS_HISTORY_LIMIT = 50


class ProgressStore:
    """进度存储：内存 + Redis（跨实例共享）。"""

    def __init__(self):
        self._local: dict[str, dict] = {}
        self._local_history: dict[str, list[dict]] = {}
        self._thread_write_locks: dict[str, asyncio.Lock] = {}
        self._thread_write_locks_mutex = asyncio.Lock()

    async def _thread_write_lock(self, thread_id: str) -> asyncio.Lock:
        async with self._thread_write_locks_mutex:
            lock = self._thread_write_locks.get(thread_id)
            if lock is None:
                lock = asyncio.Lock()
                self._thread_write_locks[thread_id] = lock
            return lock

    def _key(self, thread_id: str) -> str:
        return f"opsbrain:progress:{thread_id}"

    def _history_key(self, thread_id: str) -> str:
        return f"opsbrain:progress:history:{thread_id}"

    def _append_local_history(self, thread_id: str, payload: dict) -> None:
        history = self._local_history.setdefault(thread_id, [])
        history.append(dict(payload))
        if len(history) > _PROGRESS_HISTORY_LIMIT:
            del history[:-_PROGRESS_HISTORY_LIMIT]

    async def _get_redis(self) -> aioredis.Redis | None:
        try:
            return await get_redis()
        except Exception as e:
            logger.warning("获取 Redis 连接失败: %s", e)
            return None

    async def aget(self, thread_id: str) -> dict | None:
        rd = await self._get_redis()
        if rd is not None:
            try:
                raw = await rd.get(self._key(thread_id))
                if raw:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        # 跨进程场景优先 Redis 真值，避免本地内存陈旧导致进度卡住。
                        self._local[thread_id] = data
                        return data
            except Exception as e:
                logger.debug("读取 Redis 进度失败 thread=%s: %s", thread_id, e)
        return self._local.get(thread_id)

    async def aget_history(self, thread_id: str, limit: int = _PROGRESS_HISTORY_LIMIT) -> list[dict]:
        limit = max(1, min(int(limit), _PROGRESS_HISTORY_LIMIT))
        rd = await self._get_redis()
        if rd is not None:
            try:
                raw_items = await rd.lrange(self._history_key(thread_id), -limit, -1)
                if raw_items:
                    items: list[dict] = []
                    for raw in raw_items:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict):
                            items.append(parsed)
                    if items:
                        self._local_history[thread_id] = items[-_PROGRESS_HISTORY_LIMIT:]
                        return items[-limit:]
            except Exception as e:
                logger.debug("读取 Redis 进度历史失败 thread=%s: %s", thread_id, e)
        history = self._local_history.get(thread_id, [])
        return history[-limit:]

    async def aclear_run(self, thread_id: str) -> None:
        """同一 thread 再次执行诊断等任务前调用：清空快照与历史，避免轮询混入上一轮末尾。"""
        lock = await self._thread_write_lock(thread_id)
        async with lock:
            self._local.pop(thread_id, None)
            self._local_history.pop(thread_id, None)
            rd = await self._get_redis()
            if rd is not None:
                try:
                    await rd.delete(self._history_key(thread_id), self._key(thread_id))
                except Exception as e:
                    logger.debug("清除 Redis 进度 thread=%s: %s", thread_id, e)

    async def aset(self, thread_id: str, payload: dict, ttl: int = _PROGRESS_TTL_SECONDS) -> None:
        lock = await self._thread_write_lock(thread_id)
        async with lock:
            self._local[thread_id] = payload
            self._append_local_history(thread_id, payload)
            rd = await self._get_redis()
            if rd is None:
                return
            try:
                payload_json = json.dumps(payload, ensure_ascii=False)
                async with rd.pipeline(transaction=False) as pipe:
                    pipe.set(self._key(thread_id), payload_json, ex=ttl)
                    pipe.rpush(self._history_key(thread_id), payload_json)
                    pipe.ltrim(self._history_key(thread_id), -_PROGRESS_HISTORY_LIMIT, -1)
                    pipe.expire(self._history_key(thread_id), ttl)
                    await pipe.execute()
            except Exception as e:
                logger.debug("写入 Redis 进度失败 thread=%s: %s", thread_id, e)

    def get(self, thread_id: str, default=None):
        return self._local.get(thread_id, default)

    def __setitem__(self, thread_id: str, payload: dict):
        self._local[thread_id] = payload
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.aset(thread_id, payload))
        except RuntimeError:
            pass


progress_cache = ProgressStore()


def write_progress_cache(thread_id: str, payload: dict) -> None:
    """写入实时进度缓存。"""
    progress_cache[thread_id] = payload
