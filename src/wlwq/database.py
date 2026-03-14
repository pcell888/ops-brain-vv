"""MySQL 连接池 — aiomysql。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiomysql

from src.wlwq.config import get_mysql_config

logger = logging.getLogger(__name__)

_pool: aiomysql.Pool | None = None


async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        cfg = get_mysql_config()
        _pool = await aiomysql.create_pool(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            db=cfg["db"],
            autocommit=cfg["autocommit"],
            minsize=1,
            maxsize=10,
        )
        logger.info("wlwq MySQL pool created: %s@%s:%s/%s", cfg["user"], cfg["host"], cfg["port"], cfg["db"])
    return _pool


@asynccontextmanager
async def get_cursor():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            yield cur


async def close_pool():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        logger.info("wlwq MySQL pool closed")
