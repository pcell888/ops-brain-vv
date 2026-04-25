"""MCP 会话管理 — stdio 子进程生命周期、连接/重连、关闭。"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.config import get_settings
from src.core.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("mcp_client")


class MCPToolInvocationError(RuntimeError):
    pass


def mcp_stdio_env() -> dict[str, str]:
    st = get_settings()
    out: dict[str, str] = {k: str(v) for k, v in os.environ.items() if v is not None and v != ""}
    log_dir = Path(st.log_dir).expanduser()
    if not log_dir.is_absolute():
        log_dir = Path.cwd() / log_dir
    out["LOG_DIR"] = str(log_dir.resolve())
    out["POSTGRES_URI"] = st.postgres_uri
    out["REDIS_URL"] = st.redis_url
    if (st.platform_center_api_base or "").strip():
        out["PLATFORM_CENTER_API_BASE"] = st.platform_center_api_base.strip()
    out["PLATFORM_CENTER_AUTH_TYPE"] = st.platform_center_auth_type or "token"
    if st.platform_center_auth_credential:
        out["PLATFORM_CENTER_AUTH_CREDENTIAL"] = st.platform_center_auth_credential
    if st.llm_api_key:
        out["LLM_API_KEY"] = st.llm_api_key
    out["LLM_MODEL"] = st.llm_model
    out["LLM_BASE_URL"] = st.llm_base_url
    out["TENANT_CACHE_TTL"] = str(st.tenant_cache_ttl)
    if not (out.get("PYTHONPATH") or "").strip():
        out["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return out


MCP_SERVER_MODULES: dict[str, str] = {
    "biz-server": "src.mcp_servers.biz_server",
    "benchmark-server": "src.mcp_servers.benchmark_server",
}

MCP_SERVER_ALIASES: dict[str, str] = {
    "crm-server": "biz-server",
    "metrics-server": "biz-server",
    "task-server": "biz-server",
    "notify-server": "biz-server",
}


def mcp_session_server_name(server_name: str) -> str:
    return MCP_SERVER_ALIASES.get(server_name, server_name)


_sessions: dict[str, ClientSession] = {}
_shutdown_events: dict[str, asyncio.Event] = {}
_bg_tasks: dict[str, asyncio.Task] = {}
_init_locks: dict[str, asyncio.Lock] = {}


async def _server_lifecycle(server_name: str, module: str, ready: asyncio.Event):
    shutdown_event = asyncio.Event()
    _shutdown_events[server_name] = shutdown_event

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=mcp_stdio_env(),
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                _sessions[server_name] = session
                logger.info("MCP stdio session 已建立: %s", server_name)
                ready.set()
                await shutdown_event.wait()
    except Exception as e:
        logger.error("MCP stdio session 异常退出: %s -> %s", server_name, e)
        ready.set()
    finally:
        _sessions.pop(server_name, None)


async def get_session(server_name: str) -> ClientSession:
    canonical = mcp_session_server_name(server_name)
    if canonical in _sessions:
        return _sessions[canonical]

    if canonical not in _init_locks:
        _init_locks[canonical] = asyncio.Lock()

    async with _init_locks[canonical]:
        if canonical in _sessions:
            return _sessions[canonical]

        module = MCP_SERVER_MODULES.get(canonical)
        if not module:
            raise ValueError(f"未知的 MCP Server: {server_name}")

        ready = asyncio.Event()
        task = asyncio.create_task(_server_lifecycle(canonical, module, ready))
        _bg_tasks[canonical] = task
        try:
            await asyncio.wait_for(ready.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            task.cancel()
            _bg_tasks.pop(canonical, None)
            raise RuntimeError(f"MCP 服务 {canonical} 启动超时(30s)")

        if canonical not in _sessions:
            raise RuntimeError(f"MCP 服务 {canonical} 启动失败")

        return _sessions[canonical]


async def close_all_sessions():
    for event in _shutdown_events.values():
        event.set()
    for name, task in _bg_tasks.items():
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
        logger.info("MCP stdio session 已关闭: %s", name)
    _sessions.clear()
    _shutdown_events.clear()
    _bg_tasks.clear()
    _init_locks.clear()


def is_connection_like_error(err: Exception) -> bool:
    msg = str(err).lower()
    hints = (
        "connection is closed",
        "server closed the connection",
        "session is closed",
        "broken pipe",
        "connection reset",
        "eof",
        "closed resource",
        "transport is closed",
        "stream closed",
    )
    return any(h in msg for h in hints)


def invalidate_session(server_name: str, reason: Exception) -> None:
    canonical = mcp_session_server_name(server_name)
    _sessions.pop(canonical, None)

    shutdown_event = _shutdown_events.pop(canonical, None)
    if shutdown_event is not None:
        shutdown_event.set()

    bg_task = _bg_tasks.pop(canonical, None)
    if bg_task is not None and not bg_task.done():
        bg_task.cancel()

    logger.warning("MCP session 已标记失效，等待重建: %s (%s)", canonical, reason)
