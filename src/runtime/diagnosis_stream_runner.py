"""流式执行诊断 LangGraph 并推送进度（编排 graph / 进度 / WS，供 Worker 等调用）。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.agent.progress import clear_progress_sender, set_progress_sender
from src.core.config import CN_TZ, log_diagnosis_run_context
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.core.phases import WORKFLOW_NODES
from src.core.tracing import get_tracer

from .diagnosis_ws_manager import manager
from .graph_app import astream_events_with_retry, get_graph_app
from .progress_store import progress_cache, write_progress_cache
from .running_tasks import running_tasks

logger = logging.getLogger(__name__)
tracer = get_tracer("diagnosis")

_NODE_START_PERCENT = {
    "collect_data": 5,
    "diagnose": 35,
    "generate_solutions": 70,
}

_NODE_COMPLETE_PERCENT = {
    "collect_data": 35,
    "diagnose": 70,
    "generate_solutions": 100,
}

_NODE_START_MESSAGE = {
    "collect_data": "开始采集运营数据",
    "diagnose": "开始诊断分析",
    "generate_solutions": "正在生成优化方案",
}

_NODE_COMPLETE_MESSAGE = {
    "collect_data": "数据采集完成",
    "diagnose": "根因分析完成",
    "generate_solutions": "方案生成完成",
}


async def run_diagnosis_with_stream(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
    auth_token: str | None = None,
) -> None:
    """流式运行 LangGraph 并推送进度。"""
    log_diagnosis_run_context(
        logger,
        thread_id=thread_id,
        tenant_id=tenant_id,
        store_id=store_id,
        trigger_type=trigger_type,
    )
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": trigger_type,
        "triggered_by": triggered_by,
        "selected_dimensions": selected_dimensions,
        "selected_indicators": selected_indicators,
        "auth_token": auth_token,
        "progress_messages": [],
    }

    try:
        with tracer.start_as_current_span(
            "diagnosis.run",
            attributes={
                "diagnosis.thread_id": thread_id,
                "diagnosis.tenant_id": tenant_id,
                "diagnosis.store_id": store_id,
                "diagnosis.trigger_type": trigger_type,
            },
        ) as _:
            await progress_cache.aclear_run(thread_id)
            set_progress_sender(thread_id, manager, write_progress_cache)
            started_ts = datetime.now(CN_TZ).isoformat()
            write_progress_cache(
                thread_id,
                {
                    "type": "progress",
                    "message": "已启动诊断任务",
                    "percent": 5,
                    "timestamp": started_ts,
                },
            )
            await manager.send_progress(
                thread_id,
                {
                    "type": "progress",
                    "message": "已启动诊断任务",
                    "percent": 5,
                    "timestamp": started_ts,
                },
            )
            async for event in astream_events_with_retry(initial_state, config):
                if await running_tasks.is_cancel_requested(thread_id):
                    raise asyncio.CancelledError()
                kind = event["event"]

                if kind == "on_chain_start":
                    node_name = event.get("name", "")
                    if node_name in WORKFLOW_NODES:
                        payload = {
                            "type": "node_start",
                            "node": node_name,
                            "timestamp": datetime.now(CN_TZ).isoformat(),
                        }
                        if node_name in _NODE_START_PERCENT:
                            payload["percent"] = _NODE_START_PERCENT[node_name]
                        if node_name in _NODE_START_MESSAGE:
                            payload["message"] = _NODE_START_MESSAGE[node_name]
                            # 上述节点的首条/边界进度由节点内 emit，避免 on_chain_* 晚于节点内 emit
                            if node_name not in ("generate_solutions", "diagnose"):
                                write_progress_cache(
                                    thread_id,
                                    {
                                        "type": "progress",
                                        "message": _NODE_START_MESSAGE[node_name],
                                        "percent": payload.get("percent"),
                                        "timestamp": payload["timestamp"],
                                    },
                                )
                        await manager.send_progress(thread_id, payload)

                elif kind == "on_chain_end":
                    node_name = event.get("name", "")
                    output = event.get("data", {}).get("output", {})

                    if node_name not in WORKFLOW_NODES:
                        continue

                    if isinstance(output, dict) and "progress_messages" in output:
                        for msg in output["progress_messages"]:
                            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                            payload = {
                                "type": "progress",
                                "message": content,
                                "timestamp": datetime.now(CN_TZ).isoformat(),
                            }
                            if isinstance(msg, dict) and msg.get("percent") is not None:
                                payload["percent"] = msg.get("percent")
                            await manager.send_progress(thread_id, payload)

                    payload = {
                        "type": "node_complete",
                        "node": node_name,
                        "timestamp": datetime.now(CN_TZ).isoformat(),
                    }
                    if node_name in _NODE_COMPLETE_PERCENT:
                        payload["percent"] = _NODE_COMPLETE_PERCENT[node_name]
                    if node_name in _NODE_COMPLETE_MESSAGE:
                        payload["message"] = _NODE_COMPLETE_MESSAGE[node_name]
                        # collect_data 完成 / diagnose 完成由节点返回前 emit，避免 on_chain_end 晚于下一节点
                        if node_name not in ("diagnose", "collect_data"):
                            write_progress_cache(
                                thread_id,
                                {
                                    "type": "progress",
                                    "message": _NODE_COMPLETE_MESSAGE[node_name],
                                    "percent": payload.get("percent"),
                                    "timestamp": payload["timestamp"],
                                },
                            )
                    await manager.send_progress(thread_id, payload)

                    if node_name == "diagnose" and isinstance(output, dict) and "health_score" in output:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "diagnosis_result",
                                "health_score": output["health_score"],
                                "anomaly_count": len(output.get("anomalies", [])),
                                "dimension_scores": output.get("dimension_scores"),
                            },
                        )

                    if node_name == "generate_solutions" and isinstance(output, dict) and "solution_plans" in output:
                        await manager.send_progress(
                            thread_id,
                            {
                                "type": "solutions_ready",
                                "plans": output["solution_plans"],
                            },
                        )

    except asyncio.CancelledError:
        logger.info("诊断流程已取消: thread=%s", thread_id)
        raise
    except Exception as e:
        logger.exception("诊断流程异常 thread=%s", thread_id)
        err_msg = public_diagnosis_error_message(e)
        await progress_cache.aset(
            thread_id,
            {
                "type": "error",
                "message": err_msg,
                "percent": 0,
                "timestamp": datetime.now(CN_TZ).isoformat(),
            },
        )
        await manager.send_progress(
            thread_id,
            {
                "type": "error",
                "message": err_msg,
                "timestamp": datetime.now(CN_TZ).isoformat(),
            },
        )
        raise
    finally:
        clear_progress_sender()

    app = await get_graph_app()
    state = await app.aget_state(config)
    if state.next and "wait_adoption" in state.next:
        await manager.send_progress(
            thread_id,
            {
                "type": "completed",
                "message": "方案已生成，请选择需要采纳的方案",
                "percent": 100,
            },
        )
    elif state.next and "track_effects" in state.next:
        await manager.send_progress(
            thread_id,
            {
                "type": "completed",
                "message": "方案执行任务已全部创建，效果追踪已调度",
                "percent": 100,
            },
        )
    else:
        await manager.send_progress(
            thread_id,
            {
                "type": "completed",
                "message": "诊断流程已完成",
                "percent": 100,
            },
        )
