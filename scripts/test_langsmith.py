#!/usr/bin/env python3
"""验证 LangSmith 追踪：直连 LLM 与 LangGraph 内嵌 LLM 对比。

在仓库根目录执行:
  uv run python scripts/test_langsmith.py                  # 直连 ChatOpenAI（默认）
  uv run python scripts/test_langsmith.py --mode langgraph      # 迷你图 + ainvoke + llm_traced_ainvoke
  uv run python scripts/test_langsmith.py --mode langgraph-raw  # 迷你图 + ainvoke + 仅 llm.ainvoke(config=)
  uv run python scripts/test_langsmith.py --mode langgraph-stream   # 迷你图 + astream_events v2（对齐诊断 HTTP 流式）
  uv run python scripts/test_langsmith.py --check-only

依赖根目录 .env 中的 LangSmith 与 LLM 配置（与主应用一致）。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, TypedDict


def _bootstrap() -> None:
    """必须在 import langchain_openai 之前执行。"""
    from src.core.tracing import apply_langsmith_env

    apply_langsmith_env()


_bootstrap()

from langchain_core.runnables import RunnableConfig  # noqa: E402
from langchain_core.tracers.langchain import wait_for_all_tracers  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from langsmith.utils import tracing_is_enabled  # noqa: E402

from src.core.config import get_settings  # noqa: E402


def _print_env_status() -> None:
    keys = (
        "LANGSMITH_TRACING_V2",
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_PROJECT",
        "LANGCHAIN_PROJECT",
    )
    for k in keys:
        v = os.environ.get(k, "")
        if "KEY" in k and v:
            v = "(已设置)"
        print(f"  {k}={v or '(empty)'}")


class _MiniState(TypedDict, total=False):
    """与诊断图类似：节点更新部分字段。"""

    reply: str


def _make_mini_graph_llms(*, raw_only: bool) -> Any:
    """返回已 compile() 的迷你图（无 checkpointer）。"""
    from langgraph.graph import END, StateGraph

    from src.core.tracing import llm_traced_ainvoke

    s = get_settings()
    llm = ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        temperature=0,
        max_tokens=64,
        timeout=s.llm_httpx_timeout(),
    )

    async def llm_node(state: _MiniState, config: RunnableConfig) -> dict:
        messages = [{"role": "user", "content": "只回复一个词：pong"}]
        if raw_only:
            resp = await llm.ainvoke(messages, config=config)
        else:
            resp = await llm_traced_ainvoke(llm, messages, runnable_config=config)
        text = getattr(resp, "content", str(resp))
        return {"reply": text}

    graph = StateGraph(_MiniState)
    graph.add_node("llm_node", llm_node)
    graph.set_entry_point("llm_node")
    graph.add_edge("llm_node", END)
    return graph.compile()


async def _run_llm_direct() -> int:
    s = get_settings()
    if not s.llm_api_key.strip():
        print("错误: LLM_API_KEY 为空，无法调用模型。", file=sys.stderr)
        return 1

    llm = ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        temperature=0,
        max_tokens=64,
        timeout=s.llm_httpx_timeout(),
    )
    resp = await llm.ainvoke([{"role": "user", "content": "只回复一个词：pong"}])
    content = getattr(resp, "content", resp)
    print("[direct] LLM 回复:", (content[:300] + "…") if isinstance(content, str) and len(content) > 300 else content)
    wait_for_all_tracers()
    print("[direct] 已 flush。请在 LangSmith 对应 Project 查看 Traces。")
    return 0


async def _run_langgraph(*, raw_only: bool) -> int:
    s = get_settings()
    if not s.llm_api_key.strip():
        print("错误: LLM_API_KEY 为空。", file=sys.stderr)
        return 1

    app = _make_mini_graph_llms(raw_only=raw_only)
    tag = "langgraph-raw" if raw_only else "langgraph+llm_traced_ainvoke"
    print(f"[{tag}] 运行 ainvoke …")
    cfg: RunnableConfig = {"configurable": {"thread_id": "test_langsmith_smoke"}}
    out = await app.ainvoke({}, config=cfg)
    print(f"[{tag}] graph 输出: {out!r}")
    wait_for_all_tracers()
    print(f"[{tag}] 已 flush。请在 LangSmith 查看 trace。")
    return 0


async def _run_langgraph_stream(*, raw_only: bool) -> int:
    """与 diagnosis 路由一致：astream_events(initial_state, config, version="v2")。"""
    s = get_settings()
    if not s.llm_api_key.strip():
        print("错误: LLM_API_KEY 为空。", file=sys.stderr)
        return 1

    app = _make_mini_graph_llms(raw_only=raw_only)
    tag = "langgraph-stream-raw" if raw_only else "langgraph-stream+llm_traced_ainvoke"
    print(f"[{tag}] 运行 astream_events (v2) …")
    cfg: RunnableConfig = {"configurable": {"thread_id": "test_langsmith_smoke_stream"}}
    n_events = 0
    async for _event in app.astream_events({}, config=cfg, version="v2"):
        n_events += 1
    print(f"[{tag}] astream_events 收包数: {n_events}")
    wait_for_all_tracers()
    print(f"[{tag}] 已 flush。请在 LangSmith 查看 trace。")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="LangSmith：直连 vs LangGraph vs 流式图")
    p.add_argument(
        "--check-only",
        action="store_true",
        help="只打印环境变量与 tracing_is_enabled()",
    )
    p.add_argument(
        "--mode",
        choices=("direct", "langgraph", "langgraph-raw", "langgraph-stream", "langgraph-stream-raw"),
        default="direct",
        help=(
            "direct=仅 ChatOpenAI；"
            "langgraph/langgraph-raw=ainvoke；"
            "langgraph-stream*=astream_events v2（对齐诊断流式）"
        ),
    )
    args = p.parse_args()

    print("LangSmith / LangChain 环境（脱敏）:")
    _print_env_status()
    on = tracing_is_enabled()
    print(f"tracing_is_enabled() -> {on}")
    if not on:
        print("提示: 若为 False，请检查 .env 中追踪开关与 API Key。", file=sys.stderr)
    if args.check_only:
        return 0 if on else 1
    if not on:
        return 1

    if args.mode == "direct":
        return asyncio.run(_run_llm_direct())
    if args.mode == "langgraph":
        return asyncio.run(_run_langgraph(raw_only=False))
    if args.mode == "langgraph-raw":
        return asyncio.run(_run_langgraph(raw_only=True))
    if args.mode == "langgraph-stream":
        return asyncio.run(_run_langgraph_stream(raw_only=False))
    return asyncio.run(_run_langgraph_stream(raw_only=True))


if __name__ == "__main__":
    sys.exit(main())
