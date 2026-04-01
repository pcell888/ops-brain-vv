"""MCP Client 封装 — 通过 stdio 传输调用各 MCP Server 的 Tool。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import CN_TZ, get_settings
from src.core.tracing import get_tracer

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
tracer = get_tracer("mcp_client")


def mcp_stdio_env() -> dict[str, str]:
    """stdio 子进程环境。须传父进程完整 os.environ：mcp 库会把 env 与极小的 get_default_environment 合并，
    若只传少量键，子进程仍缺 REDIS_URL 等，Settings 会回落到 localhost；与主进程不一致。
    """
    st = get_settings()
    # 复制父进程环境（字符串化），避免 None
    out: dict[str, str] = {k: str(v) for k, v in os.environ.items() if v is not None and v != ""}
    log_dir = Path(st.log_dir).expanduser()
    if not log_dir.is_absolute():
        log_dir = Path.cwd() / log_dir
    out["LOG_DIR"] = str(log_dir.resolve())
    out["POSTGRES_URI"] = st.postgres_uri
    out["REDIS_URL"] = st.redis_url
    if st.wlwq_business_api_base:
        out["WLWQ_BUSINESS_API_BASE"] = st.wlwq_business_api_base
    if st.wlwq_postgres_uri:
        out["WLWQ_POSTGRES_URI"] = st.wlwq_postgres_uri
    if (st.platform_center_api_base or "").strip():
        out["PLATFORM_CENTER_API_BASE"] = st.platform_center_api_base.strip()
    out["PLATFORM_CENTER_AUTH_TYPE"] = st.platform_center_auth_type or "token"
    if st.platform_center_auth_credential:
        out["PLATFORM_CENTER_AUTH_CREDENTIAL"] = st.platform_center_auth_credential
    if st.credential_encrypt_key:
        out["CREDENTIAL_ENCRYPT_KEY"] = st.credential_encrypt_key
    if st.llm_api_key:
        out["LLM_API_KEY"] = st.llm_api_key
    out["LLM_MODEL"] = st.llm_model
    out["LLM_BASE_URL"] = st.llm_base_url
    out["TENANT_CACHE_TTL"] = str(st.tenant_cache_ttl)
    if not (out.get("PYTHONPATH") or "").strip():
        out["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return out


class MCPToolInvocationError(RuntimeError):
    """MCP 工具返回 isError（子进程内业务失败等），调用方应中止而非当作空结果。"""


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


def _strip_json_fence(s: str) -> str:
    s = s.strip()
    if not s.startswith("```"):
        return s
    lines = s.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def unwrap_mcp_json_value(val: Any, max_depth: int = 8) -> Any:
    """将 MCP 可能返回的 JSON 字符串（含多重 string 编码、markdown 围栏）展开为 dict/list 等。"""
    cur = val
    for _ in range(max_depth):
        if not isinstance(cur, str):
            return cur
        t = _strip_json_fence(cur)
        if not t:
            return {}
        try:
            cur = json.loads(t)
        except (json.JSONDecodeError, TypeError):
            return cur
    return cur


def _parse_call_tool_result(result: Any) -> Any:
    """从 CallToolResult 取出结构化数据：优先 structuredContent（MCP 新版），否则解析 TextContent JSON。"""
    is_error = getattr(result, "isError", False)
    if is_error:
        parts: list[str] = []
        for block in getattr(result, "content", None) or []:
            t = getattr(block, "text", None)
            if isinstance(t, str) and t.strip():
                parts.append(t.strip())
        msg = " | ".join(parts) if parts else "unknown error"
        logger.error("MCP tool 返回 isError: %s", msg[:800])
        raise MCPToolInvocationError(msg[:4000] if msg else "MCP 工具返回错误（无详情）")

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return unwrap_mcp_json_value(structured)

    blocks: list[str] = []
    for block in getattr(result, "content", None) or []:
        t = getattr(block, "text", None)
        if isinstance(t, str) and t.strip():
            blocks.append(t)

    for raw in blocks:
        text = _strip_json_fence(raw)
        if not text:
            continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, str):
                try:
                    return json.loads(parsed)
                except (json.JSONDecodeError, TypeError):
                    return parsed
            return parsed
        except json.JSONDecodeError:
            continue

    merged = _strip_json_fence("\n".join(blocks))
    if merged:
        try:
            parsed = json.loads(merged)
            if isinstance(parsed, str):
                try:
                    return json.loads(parsed)
                except (json.JSONDecodeError, TypeError):
                    return parsed
            return parsed
        except json.JSONDecodeError:
            logger.warning("MCP 工具结果 JSON 解析失败，前 240 字: %s", merged[:240])
            return merged

    return {}


async def mcp_call(server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
    """通过 stdio 调用 MCP Server 的 Tool。"""
    with tracer.start_as_current_span(f"mcp.{server_name}.{tool_name}") as span:
        span.set_attribute("mcp.server", server_name)
        span.set_attribute("mcp.tool", tool_name)
        try:
            span.set_attribute("mcp.arguments", json.dumps(arguments, ensure_ascii=False)[:500])
        except (TypeError, ValueError):
            pass

        session = await _get_session(server_name)

        try:
            logger.info(
                "mcp_call %s.%s json=%s",
                server_name,
                tool_name,
                json.dumps(arguments, ensure_ascii=False),
            )
        except (TypeError, ValueError):
            logger.info("mcp_call %s.%s args=%r", server_name, tool_name, arguments)

        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=MCP_CALL_TIMEOUT,
            )

            return unwrap_mcp_json_value(_parse_call_tool_result(result))

        except MCPToolInvocationError:
            span.record_exception(MCPToolInvocationError("MCP tool returned isError"))
            raise
        except Exception as e:
            span.record_exception(e)
            logger.error("MCP调用失败: %s.%s -> %s", server_name, tool_name, e)
            raise RuntimeError(f"MCP 服务 {server_name} 调用失败: {e}") from e


def emit_progress(
    state: dict,
    message: str,
    percent: int | float | None = None,
    level: str = "info",
    *,
    for_adoption_ui: bool = True,
):
    """向 state 中追加进度消息（会被 LangGraph add_messages reducer 合并）；若已 set_progress_sender 则同时实时推送到 WS。

    level: 'info' | 'warning' | 'error'  —— warning/error 会透传到前端用于差异化展示。
    for_adoption_ui: 为 False 时（如效果追踪），WS 使用 stage=effect_track；默认真时 WS 使用 stage=execution，与采纳蒙层约定一致。
    """
    state.setdefault("progress_messages", [])
    ts = datetime.now(CN_TZ).isoformat()
    payload: dict[str, Any] = {
        "type": "human",
        "content": message,
        "timestamp": ts,
    }
    if percent is not None:
        payload["percent"] = percent
    if level and level != "info":
        payload["level"] = level
    if not for_adoption_ui:
        payload["stage"] = "effect_track"
    state["progress_messages"].append(payload)

    # 同步写入共享进度缓存，供 HTTP 轮询端点实时读取
    try:
        from src.api.deps import progress_cache

        thread_id_key = state.get("thread_id", "")
        if thread_id_key:
            cache_entry: dict[str, Any] = {"message": message, "percent": percent, "timestamp": ts}
            if level and level != "info":
                cache_entry["level"] = level
            if not for_adoption_ui:
                cache_entry["stage"] = "effect_track"
                cache_entry["type"] = "progress"
            progress_cache[thread_id_key] = cache_entry
    except Exception:
        pass

    sender = _progress_sender.get()
    if sender:
        thread_id, manager = sender
        try:
            loop = asyncio.get_running_loop()
            ws_payload: dict[str, Any] = {
                "type": "progress",
                "message": message,
                "timestamp": ts,
                "stage": "effect_track" if not for_adoption_ui else "execution",
            }
            if percent is not None:
                ws_payload["percent"] = percent
            if level and level != "info":
                ws_payload["level"] = level
            loop.create_task(manager.send_progress(thread_id, ws_payload))
        except RuntimeError:
            pass
