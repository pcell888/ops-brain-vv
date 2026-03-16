"""MCP Client 封装 — 通过 stdio 传输调用各 MCP Server 的 Tool。"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any

# 由 API 在流式运行前设置，用于 emit_progress 时实时推送到 WebSocket
_progress_sender: ContextVar[tuple[str, Any] | None] = ContextVar("progress_sender", default=None)


def set_progress_sender(thread_id: str, manager: Any) -> None:
    """设置当前诊断任务的进度推送目标（thread_id, manager）。"""
    _progress_sender.set((thread_id, manager))


def clear_progress_sender() -> None:
    _progress_sender.set(None)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

MCP_SERVER_MODULES: dict[str, str] = {
    "metrics-server": "src.mcp_servers.metrics_server",
    "crm-server": "src.mcp_servers.crm_server",
    "benchmark-server": "src.mcp_servers.benchmark_server",
    "task-server": "src.mcp_servers.task_server",
    "notify-server": "src.mcp_servers.notify_server",
}

_sessions: dict[str, ClientSession] = {}
_shutdown_events: dict[str, asyncio.Event] = {}
_bg_tasks: dict[str, asyncio.Task] = {}
_init_locks: dict[str, asyncio.Lock] = {}


async def _server_lifecycle(server_name: str, module: str, ready: asyncio.Event):
    """后台 Task：持有 stdio context manager 生命周期，直到收到 shutdown 信号。"""
    shutdown_event = asyncio.Event()
    _shutdown_events[server_name] = shutdown_event

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
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


async def _get_session(server_name: str) -> ClientSession:
    """获取或创建到指定 MCP Server 的 stdio session。"""
    if server_name in _sessions:
        return _sessions[server_name]

    if server_name not in _init_locks:
        _init_locks[server_name] = asyncio.Lock()

    async with _init_locks[server_name]:
        if server_name in _sessions:
            return _sessions[server_name]

        module = MCP_SERVER_MODULES.get(server_name)
        if not module:
            raise ValueError(f"未知的 MCP Server: {server_name}")

        ready = asyncio.Event()
        task = asyncio.create_task(_server_lifecycle(server_name, module, ready))
        _bg_tasks[server_name] = task
        try:
            await asyncio.wait_for(ready.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            task.cancel()
            _bg_tasks.pop(server_name, None)
            raise RuntimeError(f"MCP 服务 {server_name} 启动超时(30s)")

        if server_name not in _sessions:
            raise RuntimeError(f"MCP 服务 {server_name} 启动失败")

        return _sessions[server_name]


async def close_all_sessions():
    """关闭所有 MCP stdio session（应用退出时调用）。"""
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


# 单次 tool 调用超时，避免 stdio 阻塞导致流程卡死
MCP_CALL_TIMEOUT = 120.0


async def mcp_call(server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
    """通过 stdio 调用 MCP Server 的 Tool。"""
    session = await _get_session(server_name)

    try:
        result = await asyncio.wait_for(
            session.call_tool(tool_name, arguments),
            timeout=MCP_CALL_TIMEOUT,
        )

        if result.content:
            text = result.content[0].text
            try:
                return json.loads(text)
            except (json.JSONDecodeError, AttributeError):
                return text

        return {}

    except Exception as e:
        logger.error("MCP调用失败: %s.%s -> %s", server_name, tool_name, e)
        raise RuntimeError(
            f"MCP 服务 {server_name} 调用失败: {e}"
        ) from e


def emit_progress(state: dict, message: str):
    """向 state 中追加进度消息（会被 LangGraph add_messages reducer 合并）；若已 set_progress_sender 则同时实时推送到 WS。"""
    state.setdefault("progress_messages", [])
    ts = datetime.now().isoformat()
    state["progress_messages"].append({
        "type": "human",
        "content": message,
        "timestamp": ts,
    })
    sender = _progress_sender.get()
    if sender:
        thread_id, manager = sender
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.send_progress(thread_id, {
                "type": "progress",
                "message": message,
                "timestamp": ts,
            }))
        except RuntimeError:
            pass
