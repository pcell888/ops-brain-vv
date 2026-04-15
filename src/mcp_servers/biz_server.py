"""
biz-server: 业务系统 MCP 工具聚合（原 crm / metrics / notify / task 四进程合一）
传输: stdio
"""

from __future__ import annotations

from mcp.server import FastMCP

from src.mcp_servers.biz import register_all

server = FastMCP("biz-server")
register_all(server)


def main() -> None:
    from src.core.logging_setup import setup_logging

    setup_logging("mcp-servers", console=False)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
