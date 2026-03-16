"""PostgreSQL 连接池 — asyncpg，模拟业务库。"""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from src.wlwq.config import get_wlwq_postgres_uri

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


def _psql_placeholders(sql: str, params: tuple) -> tuple[str, tuple]:
    """把 MySQL 风格 %s 占位符转为 PostgreSQL $1,$2,..."""
    if not params:
        return sql, params
    n = 0
    def repl(_m):
        nonlocal n
        n += 1
        return f"${n}"
    new_sql = re.sub(r"%s", repl, sql)
    return new_sql, params


class _CursorCompat:
    """兼容 aiomysql DictCursor：execute(sql, args), fetchone(), fetchall() 返回 dict/list[dict]。"""
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn
        self._rows: list[dict[str, Any]] = []

    async def execute(self, sql: str, args: tuple = ()) -> None:
        sql, args = _psql_placeholders(sql, args)
        self._rows = [dict(r) for r in await self._conn.fetch(sql, *args)]

    async def fetchone(self) -> dict[str, Any] | None:
        if not self._rows:
            return None
        return self._rows.pop(0)

    async def fetchall(self) -> list[dict[str, Any]]:
        out, self._rows = self._rows, []
        return out


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        uri = get_wlwq_postgres_uri()
        dsn = uri.replace("postgresql+asyncpg://", "postgresql://", 1)
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        logger.info("wlwq PostgreSQL pool created: %s", dsn.split("@")[-1] if "@" in dsn else dsn)
    return _pool


@asynccontextmanager
async def get_cursor():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield _CursorCompat(conn)


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("wlwq PostgreSQL pool closed")
