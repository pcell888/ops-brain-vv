"""公共辅助 — 从 diagnosis_session / diagnosis_report 读取诊断状态。"""

from __future__ import annotations

from src.repositories.diagnosis_session import get_session
from src.repositories.diagnosis_report import get_report
from src.core.diagnosis_engine import phase_to_next_nodes


async def get_graph_state_values(thread_id: str) -> tuple[dict, list[str]]:
    """读取诊断状态：优先从 diag_sessions，fallback 到 diag_reports。

    Returns:
        (values, next_nodes) — values 为状态字典，next_nodes 为待执行节点列表。
    """
    session = await get_session(thread_id)
    if session:
        state_json = session.get("state_json")
        if isinstance(state_json, str):
            import json
            try:
                state_json = json.loads(state_json)
            except (json.JSONDecodeError, TypeError):
                state_json = {}
        values = state_json if isinstance(state_json, dict) else {}
        next_nodes = phase_to_next_nodes(session.get("phase"))
        return values, next_nodes
    report = await get_report(thread_id)
    if report:
        return report, []
    return {}, []


def is_node_in_next(node_name: str, next_nodes: list[str]) -> bool:
    return node_name in next_nodes
