"""诊断相关 HTTP 接口。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException

from src.api.constants import API_PREFIX
from src.core.models import DiagnosisRequest, DiagnosisStartResponse
from src.core.calculator import list_available_indicators
from src.core.diagnosis_report_repo import list_reports, get_report as get_report_from_db
from src.api.deps import get_graph_app, manager, running_tasks, generate_thread_id
from src.agent.tools import set_progress_sender, clear_progress_sender

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnosis", tags=["诊断"])

# 仅处理图内节点事件，避免顶层 LangGraph 的 on_chain_end 重复推送整图 progress_messages
_WORKFLOW_NODES = frozenset({
    "collect_data", "diagnose", "generate_solutions", "wait_adoption",
    "execute_plans", "track_effects",
})


@router.get("/indicators", summary="获取可选指标清单")
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
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": trigger_type,
        "triggered_by": triggered_by,
        "selected_dimensions": selected_dimensions,
        "selected_indicators": selected_indicators,
        "progress_messages": [],
    }

    try:
        set_progress_sender(thread_id, manager)
        async for event in app.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]

            if kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name in _WORKFLOW_NODES:
                    await manager.send_progress(thread_id, {
                        "type": "node_start",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                    })

            elif kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event.get("data", {}).get("output", {})

                if node_name not in _WORKFLOW_NODES:
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

    except asyncio.CancelledError:
        logger.info("诊断流程已取消: thread=%s", thread_id)
        return
    except Exception as e:
        logger.error("诊断流程异常: %s", e, exc_info=True)
        await manager.send_progress(thread_id, {
            "type": "error",
            "message": f"诊断流程出错: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        })
        return
    finally:
        clear_progress_sender()

    state = await app.aget_state(config)
    if state.next and "wait_adoption" in state.next:
        await manager.send_progress(thread_id, {
            "type": "waiting_adoption",
            "message": "方案已生成，请选择需要采纳的方案",
        })
    elif state.next and "track_effects" in state.next:
        await manager.send_progress(thread_id, {
            "type": "completed",
            "message": "方案执行任务已全部创建，效果追踪已调度",
        })
    else:
        await manager.send_progress(thread_id, {
            "type": "completed",
            "message": "诊断流程已完成",
        })


@router.get("/history", summary="获取诊断历史列表")
async def get_diagnosis_history(
    tenant_id: str | None = Query(default=None, description="租户ID"),
    store_id: str | None = Query(default=None, description="门店ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取诊断历史列表（从诊断系统 PG 读取），按创建时间倒序。"""
    items, total = await list_reports(tenant_id, store_id, page, page_size)
    for row in items:
        if "created_at" in row and hasattr(row["created_at"], "isoformat"):
            row["created_at"] = row["created_at"].isoformat()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/start", response_model=DiagnosisStartResponse, summary="启动诊断流程")
async def start_diagnosis(request: DiagnosisRequest):
    """启动诊断流程，返回 thread_id 和 WebSocket URL。报告完成后落库到诊断系统 PG。"""
    thread_id = generate_thread_id()

    task = asyncio.create_task(
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
    running_tasks[thread_id] = task
    task.add_done_callback(lambda _: running_tasks.pop(thread_id, None))

    return DiagnosisStartResponse(
        thread_id=thread_id,
        ws_url=f"{API_PREFIX}/ws/diagnosis/{thread_id}",
    )


@router.post("/{thread_id}/cancel", summary="取消诊断流程")
async def cancel_diagnosis(thread_id: str):
    """取消正在运行的诊断流程。"""
    task = running_tasks.get(thread_id)
    if task is None or task.done():
        raise HTTPException(status_code=400, detail="该诊断未在运行中")

    task.cancel()
    running_tasks.pop(thread_id, None)

    await manager.send_progress(thread_id, {
        "type": "cancelled",
        "message": "诊断流程已取消",
        "timestamp": datetime.now().isoformat(),
    })

    return {"status": "cancelled", "thread_id": thread_id}


@router.get("/{thread_id}/report", summary="获取诊断报告")
async def get_diagnosis_report(thread_id: str):
    """获取单次诊断报告（优先从诊断系统 PG 读，无则从 LangGraph state 读）。"""
    report = await get_report_from_db(thread_id)
    if report is not None:
        return report
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    if state and state.values:
        report = state.values.get("diagnosis_report")
        if report is not None:
            return report
    raise HTTPException(status_code=404, detail="该次诊断报告不存在或尚未生成")


@router.get("/{thread_id}/anomalies/{indicator_code}", summary="获取异常指标详情")
async def get_anomaly_detail(thread_id: str, indicator_code: str):
    """获取单次诊断中某个异常指标的详情（含根因、钻取明细等）。"""
    report = await get_report_from_db(thread_id)
    if report is None:
        app = await get_graph_app()
        config = {"configurable": {"thread_id": thread_id}}
        state = await app.aget_state(config)
        if state and state.values:
            report = state.values.get("diagnosis_report")
    if report is None:
        raise HTTPException(status_code=404, detail="该次诊断报告不存在或尚未生成")
    anomalies = report.get("anomalies") or []
    for a in anomalies:
        if a.get("indicator_code") == indicator_code:
            return a
    raise HTTPException(status_code=404, detail=f"未找到异常指标: {indicator_code}")


@router.get("/{thread_id}/state", summary="获取诊断流程状态")
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
