"""统一 Redis 异步客户端 — 单例 + 生命周期管理。"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

from src.core.config import get_settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            get_settings().redis_url,
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as e:
            logger.warning("关闭 Redis 连接失败: %s", e)
        finally:
            _redis = None
