"""诊断/方案等实时进度缓存（内存 + Redis），与传输层无关。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import redis.asyncio as aioredis

from src.core.config import CN_TZ, get_settings

logger = logging.getLogger(__name__)

_PROGRESS_TTL_SECONDS = 60 * 60


class ProgressStore:
    """进度存储：内存 + Redis（跨实例共享）。"""

    def __init__(self):
        self._local: dict[str, dict] = {}
        self._redis: aioredis.Redis | None = None
        self._redis_lock = asyncio.Lock()

    def _key(self, thread_id: str) -> str:
        return f"opsbrain:progress:{thread_id}"

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is not None:
            return self._redis
        async with self._redis_lock:
            if self._redis is not None:
                return self._redis
            try:
                self._redis = aioredis.from_url(
                    get_settings().redis_url,
                    decode_responses=True,
                )
            except Exception as e:
                logger.warning("初始化 Redis ProgressStore 失败: %s", e)
                self._redis = None
        return self._redis

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

    async def aset(self, thread_id: str, payload: dict, ttl: int = _PROGRESS_TTL_SECONDS) -> None:
        self._local[thread_id] = payload
        rd = await self._get_redis()
        if rd is None:
            return
        try:
            await rd.set(self._key(thread_id), json.dumps(payload, ensure_ascii=False), ex=ttl)
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
