"""全局异步连接池 — 替代所有裸 AsyncConnection.connect 调用。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from src.core.uri_utils import get_conninfo

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None


async def open_pool(*, min_size: int = 2, max_size: int = 10) -> None:
    """启动全局连接池（FastAPI lifespan 中调用）。"""
    global _pool
    if _pool is not None:
        return
    conninfo = get_conninfo()
    _pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=min_size,
        max_size=max_size,
        open=False,
    )
    await _pool.open()
    logger.info("PostgreSQL 连接池已启动 (min=%d, max=%d)", min_size, max_size)


async def close_pool() -> None:
    """关闭全局连接池（FastAPI lifespan 中调用）。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL 连接池已关闭")


def get_pool() -> AsyncConnectionPool:
    """获取全局连接池实例。池未初始化时抛出 RuntimeError。"""
    if _pool is None:
        raise RuntimeError("连接池尚未初始化，请先调用 open_pool()")
    return _pool


@asynccontextmanager
async def get_conn() -> AsyncIterator[AsyncConnection]:
    """从连接池获取连接的快捷上下文管理器。

    池已就绪时从池中借出连接；未初始化时降级为裸连接（兼容脚本/测试场景）。
    """
    if _pool is not None:
        async with _pool.connection() as conn:
            yield conn
    else:
        async with await AsyncConnection.connect(get_conninfo()) as conn:
            yield conn
