#!/usr/bin/env python3
"""
Simple MCP stdio CLI for calling a single tool.

Examples:
  python scripts/mcp_call.py --list-servers
  python scripts/mcp_call.py metrics-server --list-tools
  python scripts/mcp_call.py metrics-server get_crm_indicators --args '{"tenant_id":"wlwq_local","store_id":"st_001","start_date":"2026-03-01","end_date":"2026-03-17"}'
  python scripts/mcp_call.py metrics-server get_crm_indicators --arg tenant_id=wlwq_local --arg store_id=st_001 --arg start_date=2026-03-01 --arg end_date=2026-03-17
  cat params.json | python scripts/mcp_call.py metrics-server get_crm_indicators --args-stdin --pretty
  python scripts/mcp_call.py metrics-server get_crm_indicators --template
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.tools import MCP_SERVER_MODULES, mcp_stdio_env  # noqa: E402


def _parse_kv(text: str) -> tuple[str, Any]:
    if "=" not in text:
        raise ValueError(f"Invalid --arg format (expected key=value): {text}")
    key, raw = text.split("=", 1)
    key = key.strip()
    raw = raw.strip()
    if not key:
        raise ValueError(f"Invalid --arg key: {text}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    return key, value


def _read_stdin_json() -> dict[str, Any]:
    data = sys.stdin.read()
    if not data.strip():
        return {}
    return json.loads(data)


def _load_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.args_file:
        data = Path(args.args_file).read_text(encoding="utf-8")
        return json.loads(data)
    if args.args_json:
        return json.loads(args.args_json)
    if args.args_stdin:
        return _read_stdin_json()
    kvs = {}
    for item in args.arg or []:
        k, v = _parse_kv(item)
        kvs[k] = v
    if kvs:
        return kvs
    if not sys.stdin.isatty():
        return _read_stdin_json()
    return kvs


async def _with_session(module: str):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=mcp_stdio_env(),
    )
    return stdio_client(params)


async def list_tools(module: str) -> None:
    async with await _with_session(module) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for t in tools.tools:
                desc = (t.description or "").strip()
                line = f"{t.name}"
                if desc:
                    line += f"  -  {desc}"
                print(line)


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


def _extract_input_schema(tool: Any) -> dict | None:
    for attr in ("inputSchema", "input_schema"):
        value = getattr(tool, attr, None)
        if value:
            return value
    return None


async def print_template(module: str, tool_name: str, pretty: bool) -> int:
    async with await _with_session(module) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool = next((t for t in tools.tools if t.name == tool_name), None)
            if not tool:
                print(f"Tool not found: {tool_name}", file=sys.stderr)
                return 2
            schema = _extract_input_schema(tool) or {}
            template = _schema_placeholder(schema)
            if template is None:
                template = {}
            if pretty:
                print(json.dumps(template, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(template, ensure_ascii=False))
            return 0


async def call_tool(module: str, tool: str, arguments: dict[str, Any], timeout: float, pretty: bool) -> int:
    async with await _with_session(module) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await asyncio.wait_for(
                session.call_tool(tool, arguments),
                timeout=timeout,
            )
            if not result.content:
                print("{}")
                return 0
            text_parts = [c.text for c in result.content if hasattr(c, "text")]
            text = "".join(text_parts)
            if pretty:
                try:
                    parsed = json.loads(text)
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                except json.JSONDecodeError:
                    print(text)
            else:
                print(text)
            return 0


def _resolve_module(server: str | None, module: str | None) -> str:
    if module:
        return module
    if not server:
        raise ValueError("server is required unless --module is provided")
    if server not in MCP_SERVER_MODULES:
        raise ValueError(
            f"Unknown server '{server}'. Use --list-servers to see available names, or pass --module."
        )
    return MCP_SERVER_MODULES[server]


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP stdio CLI")
    parser.add_argument("server", nargs="?", help="Server name (e.g., metrics-server)")
    parser.add_argument("tool", nargs="?", help="Tool name to call")
    parser.add_argument("--module", help="Override module path, e.g., src.mcp_servers.metrics_server")
    parser.add_argument("--list-servers", action="store_true", help="List available server names")
    parser.add_argument("--list-tools", action="store_true", help="List tools for the server")
    parser.add_argument("--args", dest="args_json", help="Tool arguments as JSON string")
    parser.add_argument("--args-file", help="Tool arguments JSON file")
    parser.add_argument("--args-stdin", action="store_true", help="Read tool arguments JSON from stdin")
    parser.add_argument("--template", action="store_true", help="Print JSON template for the tool arguments")
    parser.add_argument(
        "--arg",
        action="append",
        help="Tool argument as key=value (value can be JSON literal). Can be repeated.",
    )
    parser.add_argument("--timeout", type=float, default=120.0, help="Tool call timeout seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output if possible")
    args = parser.parse_args()

    if args.list_servers:
        for name in sorted(MCP_SERVER_MODULES.keys()):
            print(name)
        return 0

    try:
        module = _resolve_module(args.server, args.module)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.list_tools:
        asyncio.run(list_tools(module))
        return 0

    if args.template:
        if not args.tool:
            print("tool is required when --template is used", file=sys.stderr)
            return 2
        return asyncio.run(print_template(module, args.tool, pretty=True))

    if not args.tool:
        print("tool is required unless --list-tools is used", file=sys.stderr)
        return 2

    try:
        arguments = _load_args(args)
    except Exception as e:
        print(f"Failed to parse args: {e}", file=sys.stderr)
        return 2

    try:
        return asyncio.run(call_tool(module, args.tool, arguments, args.timeout, args.pretty))
    except asyncio.TimeoutError:
        print(f"Timeout after {args.timeout}s", file=sys.stderr)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
