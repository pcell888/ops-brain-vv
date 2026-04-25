"""MCP debug UI and endpoints."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.agent.mcp_client import MCP_SERVER_MODULES, mcp_stdio_env
from src.agent.tools import mcp_call

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPCallRequest(BaseModel):
    server: str = Field(..., description="Server name, e.g., metrics-server")
    tool: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


def _extract_input_schema(tool: Any) -> dict | None:
    for attr in ("inputSchema", "input_schema"):
        value = getattr(tool, attr, None)
        if value:
            return value
    return None


def _schema_placeholder(schema: dict) -> Any:
    if "default" in schema:
        return schema["default"]
    if "const" in schema:
        return schema["const"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        for preferred in ("object", "array", "string", "integer", "number", "boolean", "null"):
            if preferred in schema_type:
                schema_type = preferred
                break
        else:
            schema_type = schema_type[0] if schema_type else None

    if schema_type == "string":
        return ""
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            return [_schema_placeholder(items)]
        return []
    if schema_type == "object":
        props = schema.get("properties", {}) or {}
        return {k: _schema_placeholder(v) for k, v in props.items()}
    return None


async def _list_tools(module: str) -> list[dict[str, Any]]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=mcp_stdio_env(),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            items = []
            for t in tools.tools:
                items.append({
                    "name": t.name,
                    "description": t.description,
                    "input_schema": _extract_input_schema(t) or {},
                })
            return items


@router.get("/servers")
async def list_servers():
    return {"servers": sorted(MCP_SERVER_MODULES.keys())}


@router.get("/tools")
async def list_tools(server: str = Query(..., description="Server name")):
    if server not in MCP_SERVER_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown server: {server}")
    try:
        tools = await _list_tools(MCP_SERVER_MODULES[server])
        return {"server": server, "tools": tools}
    except Exception as e:
        logger.exception("MCP list_tools 失败 server=%s", server)
        raise HTTPException(status_code=500, detail="列出工具失败，请查看服务日志") from e


@router.get("/template")
async def get_template(
    server: str = Query(..., description="Server name"),
    tool: str = Query(..., description="Tool name"),
):
    if server not in MCP_SERVER_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown server: {server}")
    try:
        tools = await _list_tools(MCP_SERVER_MODULES[server])
        entry = next((t for t in tools if t["name"] == tool), None)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool}")
        schema = entry.get("input_schema") or {}
        template = _schema_placeholder(schema) or {}
        return {"server": server, "tool": tool, "template": template}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("MCP get_template 失败 server=%s tool=%s", server, tool)
        raise HTTPException(
            status_code=500,
            detail="生成参数模板失败，请查看服务日志",
        ) from e


@router.post("/call")
async def call_tool(payload: MCPCallRequest):
    if payload.server not in MCP_SERVER_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown server: {payload.server}")
    try:
        result = await mcp_call(payload.server, payload.tool, payload.arguments)
        return {"result": result}
    except Exception as e:
        logger.exception(
            "MCP call 失败 server=%s tool=%s",
            payload.server,
            payload.tool,
        )
        raise HTTPException(status_code=500, detail="MCP 调用失败，请查看服务日志") from e


@router.get("/ui", response_class=HTMLResponse)
async def mcp_ui():
    html_path = Path(__file__).resolve().parents[1] / "static" / "mcp_ui.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="UI file not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
