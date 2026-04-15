"""LangGraph 应用单例与 astream 重试封装。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Mapping
from datetime import datetime
from typing import Any

from psycopg import OperationalError as PsycopgOperationalError

from src.core.config import CN_TZ

logger = logging.getLogger(__name__)

_graph_app = None
_graph_init_lock = asyncio.Lock()


async def reset_graph_app():
    """关闭 LangGraph checkpoint 连接并清空缓存（用于连接失效后重连）。"""
    global _graph_app
    async with _graph_init_lock:
        if _graph_app is None:
            return
        from src.agent.graph import close_checkpointer

        await close_checkpointer()
        _graph_app = None


async def get_graph_app():
    global _graph_app
    if _graph_app is not None:
        return _graph_app
    async with _graph_init_lock:
        if _graph_app is None:
            from src.agent.graph import compile_graph

            _graph_app = await compile_graph()
        return _graph_app


async def astream_events_with_retry(
    initial_state: Any,
    config: Mapping[str, Any],
) -> AsyncIterator[dict]:
    """包装 astream_events：检查点连接被关闭时，在未产出任何事件前可自动重连并重试一次。"""
    for attempt in range(2):
        yielded = False
        try:
            app = await get_graph_app()
            async for event in app.astream_events(initial_state, config=config, version="v2"):
                yielded = True
                yield event
            return
        except PsycopgOperationalError as e:
            msg = str(e).lower()
            if (
                attempt == 0
                and not yielded
                and ("connection is closed" in msg or "server closed the connection" in msg)
            ):
                logger.warning("LangGraph checkpoint 连接失效，重新初始化: %s", e)
                await reset_graph_app()
                continue
            raise


def generate_thread_id() -> str:
    return f"diag_{datetime.now(CN_TZ).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
