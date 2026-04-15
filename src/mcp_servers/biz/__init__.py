"""业务域 MCP 工具（CRM / 指标 / 通知 / 任务），由 biz_server 单一 stdio 进程加载。"""

from __future__ import annotations

from mcp.server import FastMCP


def register_all(server: FastMCP) -> None:
    from src.mcp_servers.biz import crm, metrics, notify, task

    crm.register(server)
    metrics.register(server)
    notify.register(server)
    task.register(server)
