"""诊断相关 HTTP 接口。"""

from __future__ import annotations

import asyncio
import logging

from datetime import datetime

from fastapi import APIRouter, Query

from src.core.models import DiagnosisRequest, DiagnosisStartResponse, AdoptPlansRequest
from src.core.calculator import list_available_indicators
from src.api.deps import get_graph_app, manager, generate_thread_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])


@router.get("/indicators")
async def get_available_indicators(
    dimensions: list[str] | None = Query(default=None, description="按维度筛选，如 ?dimensions=crm&dimensions=marketing"),
):
    """返回所有可选指标清单（按维度分组），供前端构建选择 UI。"""
    grouped = list_available_indicators(dimensions)
    flat = [ind for inds in grouped.values() for ind in inds]
    return {
        "total": len(flat),
        "dimensions": list(grouped.keys()),
        "by_dimension": grouped,
    }


async def _run_diagnosis_with_stream(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
):
    """核心: 流式运行 LangGraph 并推送进度。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": trigger_type,
        "triggered_by": triggered_by,
        "selected_dimensions": selected_dimensions,
        "selected_indicators": selected_indicators,
        "progress_messages": [],
    }

    try:
        async for event in app.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]

            if kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name and not node_name.startswith("__"):
                    await manager.send_progress(thread_id, {
                        "type": "node_start",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                    })

            elif kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event.get("data", {}).get("output", {})

                if not node_name or node_name.startswith("__"):
                    continue

                if isinstance(output, dict) and "progress_messages" in output:
                    for msg in output["progress_messages"]:
                        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                        await manager.send_progress(thread_id, {
                            "type": "progress",
                            "message": content,
                            "timestamp": datetime.now().isoformat(),
                        })

                await manager.send_progress(thread_id, {
                    "type": "node_complete",
                    "node": node_name,
                    "timestamp": datetime.now().isoformat(),
                })

                if node_name == "diagnose" and isinstance(output, dict) and "health_score" in output:
                    await manager.send_progress(thread_id, {
                        "type": "diagnosis_result",
                        "health_score": output["health_score"],
                        "anomaly_count": len(output.get("anomalies", [])),
                        "dimension_scores": output.get("dimension_scores"),
                    })

                if node_name == "generate_solutions" and isinstance(output, dict) and "solution_plans" in output:
                    await manager.send_progress(thread_id, {
                        "type": "solutions_ready",
                        "plans": output["solution_plans"],
                    })

    except Exception as e:
        logger.error("诊断流程异常: %s", e, exc_info=True)
        await manager.send_progress(thread_id, {
            "type": "error",
            "message": f"诊断流程出错: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        })
        return

    state = await app.aget_state(config)
    if state.next:
        await manager.send_progress(thread_id, {
            "type": "waiting_adoption",
            "message": "方案已生成，请选择需要采纳的方案",
        })
    else:
        await manager.send_progress(thread_id, {
            "type": "completed",
            "message": "诊断流程已完成",
        })


@router.post("/start", response_model=DiagnosisStartResponse)
async def start_diagnosis(request: DiagnosisRequest):
    """启动诊断流程，返回 thread_id 和 WebSocket URL。"""
    thread_id = generate_thread_id()

    asyncio.create_task(
        _run_diagnosis_with_stream(
            thread_id,
            request.tenant_id,
            request.store_id,
            request.trigger_type,
            request.triggered_by,
            request.selected_dimensions,
            request.selected_indicators,
        )
    )

    return DiagnosisStartResponse(
        thread_id=thread_id,
        ws_url=f"/ws/diagnosis/{thread_id}",
    )


@router.post("/{thread_id}/adopt")
async def adopt_plans(thread_id: str, request: AdoptPlansRequest):
    """用户采纳方案后继续执行。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}

    await app.aupdate_state(config, {"adopted_plan_ids": request.plan_ids})

    asyncio.create_task(_resume_after_adoption(thread_id, config))

    return {"status": "resumed", "adopted_plan_ids": request.plan_ids}


async def _resume_after_adoption(thread_id: str, config: dict):
    """Resume LangGraph 执行。"""
    app = await get_graph_app()

    try:
        async for event in app.astream_events(None, config=config, version="v2"):
            kind = event["event"]
            if kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event.get("data", {}).get("output", {})

                if not node_name or node_name.startswith("__"):
                    continue

                if isinstance(output, dict) and "progress_messages" in output:
                    for msg in output["progress_messages"]:
                        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                        await manager.send_progress(thread_id, {
                            "type": "progress",
                            "message": content,
                            "timestamp": datetime.now().isoformat(),
                        })

                await manager.send_progress(thread_id, {
                    "type": "node_complete",
                    "node": node_name,
                    "timestamp": datetime.now().isoformat(),
                })
    except Exception as e:
        logger.error("恢复执行异常: %s", e, exc_info=True)
        await manager.send_progress(thread_id, {
            "type": "error",
            "message": f"执行出错: {str(e)}",
        })
        return

    await manager.send_progress(thread_id, {
        "type": "completed",
        "message": "方案执行任务已全部创建",
    })


@router.get("/{thread_id}/state")
async def get_diagnosis_state(thread_id: str):
    """获取当前诊断流程状态。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)

    return {
        "thread_id": thread_id,
        "next_nodes": list(state.next) if state.next else [],
        "values": {
            k: v for k, v in state.values.items()
            if k != "progress_messages"
        },
    }
