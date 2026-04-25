"""Graph 执行公共辅助 — 不统一执行流程，只提取可复用的状态校验和消息发送。"""

from __future__ import annotations

from src.runtime.graph_app import get_graph_app


async def get_graph_state_values(thread_id: str) -> tuple[dict, list[str]]:
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}
    next_nodes = list(state.next) if state and state.next else []
    return values, next_nodes


def is_node_in_next(node_name: str, next_nodes: list[str]) -> bool:
    return node_name in next_nodes
