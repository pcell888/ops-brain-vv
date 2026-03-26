"""LangGraph StateGraph 定义与编译。"""

from __future__ import annotations

from urllib.parse import urlparse

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.agent.state import DiagnosisState
from src.agent.nodes import (
    collect_data_node,
    diagnose_node,
    generate_solutions_node,
    execute_plans_node,
    track_effects_node,
)
from src.core.config import get_settings

_GRAPH_SETTINGS = None


def route_after_solutions(state: DiagnosisState) -> str:
    if not state.get("anomalies"):
        return END
    return "wait_adoption"


def route_after_adoption(state: DiagnosisState) -> str:
    if state.get("adopted_plan_ids"):
        return "execute_plans"
    return END


def _wait_adoption_node(state: DiagnosisState) -> dict:
    """占位节点 — interrupt_before 会在这里暂停等待用户采纳。"""
    return {}


def build_graph() -> StateGraph:
    graph = StateGraph(DiagnosisState)

    graph.add_node("collect_data", collect_data_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("generate_solutions", generate_solutions_node)
    graph.add_node("wait_adoption", _wait_adoption_node)
    graph.add_node("execute_plans", execute_plans_node)
    graph.add_node("track_effects", track_effects_node)

    graph.set_entry_point("collect_data")

    graph.add_edge("collect_data", "diagnose")
    graph.add_edge("diagnose", "generate_solutions")

    graph.add_conditional_edges(
        "generate_solutions",
        route_after_solutions,
        {"wait_adoption": "wait_adoption", END: END},
    )

    graph.add_conditional_edges(
        "wait_adoption",
        route_after_adoption,
        {"execute_plans": "execute_plans", END: END},
    )

    graph.add_edge("execute_plans", "track_effects")
    graph.add_edge("track_effects", END)

    return graph


_checkpointer_cm = None


def _postgres_uri_to_conninfo(uri: str) -> str:
    """将 postgresql:// 或 postgresql+asyncpg:// URL 转为 psycopg conninfo。"""
    uri = uri.strip()
    if len(uri) >= 2 and uri[0] == uri[-1] and uri[0] in ("'", '"'):
        uri = uri[1:-1].strip()
    parsed = urlparse(uri)
    if parsed.scheme not in ("postgresql", "postgres", "postgresql+asyncpg"):
        return uri
    parts = []
    if parsed.hostname:
        parts.append(f"host={parsed.hostname}")
    if parsed.port:
        parts.append(f"port={parsed.port}")
    if parsed.path and parsed.path != "/":
        parts.append(f"dbname={parsed.path.lstrip('/')}")
    if parsed.username:
        parts.append(f"user={parsed.username}")
    if parsed.password:
        parts.append(f"password={parsed.password}")
    base = " ".join(parts)
    if not base:
        return uri
    # 降低长时间空闲后服务端关闭 TCP 导致 checkpoint 连接失效的概率（Docker / Pg 默认超时）
    return (
        f"{base} keepalives=1 keepalives_idle=60 "
        f"keepalives_interval=10 keepalives_count=3"
    )


async def compile_graph():
    """编译并返回可运行的 LangGraph app。"""
    global _checkpointer_cm
    settings = get_settings()
    conninfo = _postgres_uri_to_conninfo(settings.postgres_uri)
    cm = AsyncPostgresSaver.from_conn_string(conninfo)
    checkpointer = await cm.__aenter__()
    _checkpointer_cm = cm
    await checkpointer.setup()

    graph = build_graph()
    interrupts = ["wait_adoption"]
    if settings.effect_track_delay_days > 0:
        interrupts.append("track_effects")
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupts,
    )


async def close_checkpointer():
    """应用关闭时释放 checkpointer 连接。"""
    global _checkpointer_cm
    if _checkpointer_cm is not None:
        await _checkpointer_cm.__aexit__(None, None, None)
        _checkpointer_cm = None
