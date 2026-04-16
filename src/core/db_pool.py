"""全局异步连接池 — 替代所有裸 AsyncConnection.connect 调用。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from src.core.uri_utils import get_conninfo, postgres_target_for_logs

logger = logging.getLogger(__name__)


def _conninfo_append_connect_timeout(conninfo: str, seconds: int) -> str:
    if "connect_timeout=" in conninfo:
        return conninfo
    return f"{conninfo} connect_timeout={seconds}".strip()

_pool: AsyncConnectionPool | None = None


async def open_pool(*, min_size: int = 2, max_size: int = 10) -> None:
    """启动全局连接池（FastAPI lifespan 中调用）。"""
    global _pool
    if _pool is not None:
        return
    conninfo = get_conninfo()
    target = postgres_target_for_logs()
    # 先探测：失败时给出 refused/timeout 等明确原因；避免仅靠 PoolTimeout 后 worker 里 CancelledError 打空日志
    try:
        async with await AsyncConnection.connect(
            _conninfo_append_connect_timeout(conninfo, 5)
        ):
            pass
    except Exception as e:
        logger.error(
            "无法连接 PostgreSQL（目标 %s）。请确认服务已启动，例如：`make infra` 或 "
            "`docker compose up -d postgres`。错误：%s: %s",
            target,
            type(e).__name__,
            e,
        )
        raise RuntimeError(
            f"PostgreSQL 不可达（{target}）：{e}。请先启动数据库或检查 POSTGRES_URI。"
        ) from e

    pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=min_size,
        max_size=max_size,
        open=False,
    )
    try:
        # wait=True：等到 min_size 条连接就绪再返回，避免 PG 未起仍误报「已启动」
        await pool.open(wait=True, timeout=30.0)
    except PoolTimeout as e:
        logger.error(
            "PostgreSQL 连接池在 30s 内未达到 min_size=%d（目标 %s）。若数据库已启动，"
            "可能是库过载或网络过慢；超时后池内建连任务被取消，psycopg 可能打出空的 "
            "`error connecting` 警告，可忽略。",
            min_size,
            target,
        )
        try:
            await pool.close()
        except Exception:
            logger.debug("关闭未就绪连接池时忽略异常", exc_info=True)
        raise RuntimeError(
            f"PostgreSQL 连接池初始化超时（{target}），{min_size} 条连接未在 30s 内就绪。"
        ) from e
    except BaseException:
        try:
            await pool.close()
        except Exception:
            logger.debug("关闭未就绪连接池时忽略异常", exc_info=True)
        raise

    _pool = pool
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
