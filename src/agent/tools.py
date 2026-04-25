"""MCP Client 封装 — 通过 stdio 传输调用各 MCP Server 的 Tool。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.core.json_utils import strip_json_fence
from src.core.tracing import get_tracer

from src.agent.mcp_client import (
    MCPToolInvocationError,
    get_session,
    invalidate_session,
    is_connection_like_error,
)

logger = logging.getLogger(__name__)
tracer = get_tracer("mcp_client")

MCP_CALL_TIMEOUT = 120.0


def unwrap_mcp_json_value(val: Any, max_depth: int = 8) -> Any:
    cur = val
    for _ in range(max_depth):
        if not isinstance(cur, str):
            return cur
        t = strip_json_fence(cur)
        if not t:
            return {}
        try:
            cur = json.loads(t)
        except (json.JSONDecodeError, TypeError):
            return cur
    return cur


def _parse_call_tool_result(result: Any) -> Any:
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
        text = strip_json_fence(raw)
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

    merged = strip_json_fence("\n".join(blocks))
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
    with tracer.start_as_current_span(f"mcp.{server_name}.{tool_name}") as span:
        span.set_attribute("mcp.server", server_name)
        span.set_attribute("mcp.tool", tool_name)
        try:
            span.set_attribute("mcp.arguments", json.dumps(arguments, ensure_ascii=False)[:500])
        except (TypeError, ValueError):
            pass

        try:
            logger.info(
                "mcp_call %s.%s json=%s",
                server_name,
                tool_name,
                json.dumps(arguments, ensure_ascii=False),
            )
        except (TypeError, ValueError):
            logger.info("mcp_call %s.%s args=%r", server_name, tool_name, arguments)

        for attempt in range(2):
            try:
                session = await get_session(server_name)
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=MCP_CALL_TIMEOUT,
                )
                if attempt == 1:
                    logger.info("MCP session 重建后调用成功: %s.%s", server_name, tool_name)
                return unwrap_mcp_json_value(_parse_call_tool_result(result))
            except MCPToolInvocationError:
                span.record_exception(MCPToolInvocationError("MCP tool returned isError"))
                raise
            except Exception as e:
                span.record_exception(e)
                if attempt == 0 and is_connection_like_error(e):
                    invalidate_session(server_name, e)
                    logger.warning("MCP调用失败，正在重建并重试一次: %s.%s -> %s", server_name, tool_name, e)
                    continue
                logger.error("MCP调用失败: %s.%s -> %s", server_name, tool_name, e)
                raise RuntimeError(f"MCP 服务 {server_name} 调用失败: {e}") from e
