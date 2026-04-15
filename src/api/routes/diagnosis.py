"""诊断相关 HTTP 接口。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Query, HTTPException, Request
from pydantic import BaseModel

from src.api.constants import API_PREFIX
from src.core.models import DiagnosisRequest, DiagnosisStartResponse
from src.core.config import CN_TZ, log_diagnosis_run_context
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.services import async_job_service, diagnosis_service
from src.api.deps import (
    astream_events_with_retry,
    get_graph_app,
    manager,
    running_tasks,
    generate_thread_id,
    progress_cache,
    write_progress_cache,
)
from src.runtime.thread_enterprise import (
    get_active_diagnosis_thread_for_tenant,
    register_thread_enterprise,
    unregister_thread,
)
from src.agent.tools import set_progress_sender, clear_progress_sender
from src.api.token_sync import resolve_biz_auth_token
from src.core.tracing import get_tracer
from src.api.routes.drill_down import router as drill_down_router
from src.api.routes.progress import build_steps
from src.worker.arq_queue import enqueue_diagnosis_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnosis", tags=["诊断"])
router.include_router(drill_down_router)
tracer = get_tracer("diagnosis")


class CompatStartDiagnosisRequest(BaseModel):
    """兼容旧版 /diagnosis/start 请求体。"""

    enterprise_id: str
    trigger_type: str = "manual"
    dimensions: list[str] | None = None
    async_mode: bool = True


class CompatDiagnosisStatusResponse(BaseModel):
    """兼容旧版启动诊断响应。"""

    diagnosis_id: str
    status: str
    progress: int
    message: str | None = None
    health_score: float | None = None


# 同一 tenant 并发「立即诊断」时串行化，避免检查与注册之间插入第二个任务
_diagnosis_start_locks: dict[str, asyncio.Lock] = {}
_diagnosis_start_lock_mutex = asyncio.Lock()


async def _get_tenant_diagnosis_start_lock(tenant_id: str) -> asyncio.Lock:
    async with _diagnosis_start_lock_mutex:
        if tenant_id not in _diagnosis_start_locks:
            _diagnosis_start_locks[tenant_id] = asyncio.Lock()
        return _diagnosis_start_locks[tenant_id]


def _normalize_trigger_type(trigger_type: str | None) -> str:
    normalized = (trigger_type or "").strip().lower()
    if normalized in {"scheduled", "schedule", "auto", "automatic", "cron", "system"}:
        return "scheduled"
    return "manual"


def _extract_health_score_value(report: dict | None) -> float | None:
    if not report:
        return None
    raw = report.get("health_score")
    if isinstance(raw, dict):
        raw = raw.get("total_score")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


# 仅处理图内节点事件，避免顶层 LangGraph 的 on_chain_end 重复推送整图 progress_messages
_WORKFLOW_NODES = frozenset(
    {
        "collect_data",
        "diagnose",
        "generate_solutions",
        "wait_adoption",
        "execute_plans",
        "track_effects",
    }
)

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


async def _run_diagnosis_with_stream(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
    auth_token: str | None = None,
):
    """核心: 流式运行 LangGraph 并推送进度。"""
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
        with tracer.start_as_current_span("diagnosis.run", attributes={
            "diagnosis.thread_id": thread_id,
            "diagnosis.tenant_id": tenant_id,
            "diagnosis.store_id": store_id,
            "diagnosis.trigger_type": trigger_type,
        }) as _:
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
                    if node_name in _WORKFLOW_NODES:
                        payload = {
                            "type": "node_start",
                            "node": node_name,
                            "timestamp": datetime.now(CN_TZ).isoformat(),
                        }
                        if node_name in _NODE_START_PERCENT:
                            payload["percent"] = _NODE_START_PERCENT[node_name]
                        if node_name in _NODE_START_MESSAGE:
                            payload["message"] = _NODE_START_MESSAGE[node_name]
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

                    if node_name not in _WORKFLOW_NODES:
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
        return
    except Exception as e:
        logger.exception("诊断流程异常 thread=%s", thread_id)
        err_msg = public_diagnosis_error_message(e)
        await progress_cache.aset(thread_id, {
            "message": err_msg,
            "percent": 0,
            "timestamp": datetime.now(CN_TZ).isoformat(),
        })
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


@router.get("/history", summary="获取诊断历史列表")
async def get_diagnosis_history(
    tenant_id: str | None = Query(default=None, description="租户ID"),
    store_id: str | None = Query(default=None, description="门店ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取诊断历史列表（从诊断系统 PG 读取），按创建时间倒序。"""
    # 调用 Service 层获取列表（不包含运行中任务，标准接口只返回已入库记录）
    skip = (page - 1) * page_size
    items, total = await diagnosis_service.get_diagnosis_list_items(
        tenant_id=tenant_id,
        skip=skip,
        limit=page_size,
        store_id=store_id,
        include_running=False,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def _create_diagnosis_task(
    request: DiagnosisRequest,
) -> tuple[str, bool]:
    lock = await _get_tenant_diagnosis_start_lock(request.tenant_id)
    async with lock:
        existing = await get_active_diagnosis_thread_for_tenant(request.tenant_id)
        if existing:
            return existing, True

        thread_id = generate_thread_id()
        claimed, claimed_tid = await running_tasks.try_claim_tenant(request.tenant_id, thread_id)
        if not claimed:
            tid = claimed_tid or thread_id
            return tid, True

        payload = {
            "thread_id": thread_id,
            "tenant_id": request.tenant_id,
            "store_id": request.store_id,
            "trigger_type": request.trigger_type,
            "triggered_by": request.triggered_by,
            "selected_dimensions": request.selected_dimensions,
            "selected_indicators": request.selected_indicators,
            "auth_token": request.auth_token,
        }
        try:
            job_id = await enqueue_diagnosis_job(payload)
            await async_job_service.register_enqueued_job(
                job_id=job_id,
                thread_id=thread_id,
                tenant_id=request.tenant_id,
                job_kind="diagnosis",
                payload=payload,
            )
            await running_tasks.register_job(thread_id, request.tenant_id, job_id)
        except Exception:
            await running_tasks.release_tenant_claim(request.tenant_id, thread_id)
            raise
        register_thread_enterprise(thread_id, request.tenant_id)
        return thread_id, False


async def _wait_diagnosis_finish(thread_id: str, timeout_seconds: int = 1800) -> bool:
    started = asyncio.get_running_loop().time()
    while True:
        if not await running_tasks.is_running(thread_id):
            return True
        if asyncio.get_running_loop().time() - started >= timeout_seconds:
            return False
        await asyncio.sleep(1)


async def _get_report_snapshot(thread_id: str) -> dict | None:
    report = await diagnosis_service.get_diagnosis_report_data(thread_id)
    if report is not None:
        return report
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    if state and state.values:
        report = state.values.get("diagnosis_report")
        if isinstance(report, dict):
            return report
    return None


@router.post(
    "/start",
    response_model=DiagnosisStartResponse | CompatDiagnosisStatusResponse,
    summary="启动诊断流程",
)
async def start_diagnosis(
    http_request: Request,
    request: DiagnosisRequest | CompatStartDiagnosisRequest = Body(...),
):
    """启动诊断流程，同时兼容新版与旧版前端请求/响应结构。"""
    if isinstance(request, CompatStartDiagnosisRequest):
        compat_request = DiagnosisRequest(
            tenant_id=request.enterprise_id,
            store_id="",
            trigger_type=_normalize_trigger_type(request.trigger_type),
            selected_dimensions=request.dimensions,
        )
        token_header = http_request.headers.get("Token")
        compat_request = compat_request.model_copy(
            update={"auth_token": resolve_biz_auth_token(token_header, compat_request.auth_token)}
        )
        thread_id, already_running = await _create_diagnosis_task(compat_request)
        if already_running:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "该企业已有诊断正在执行，请等待完成后再发起",
                    "diagnosis_id": thread_id,
                },
            )

        if request.async_mode:
            return CompatDiagnosisStatusResponse(
                diagnosis_id=thread_id,
                status="pending",
                progress=0,
                message="诊断任务已提交",
            )

        done = await _wait_diagnosis_finish(thread_id)
        if not done:
            return CompatDiagnosisStatusResponse(
                diagnosis_id=thread_id,
                status="running",
                progress=0,
                message="诊断任务仍在执行中",
            )
        report = await _get_report_snapshot(thread_id)
        if report is None:
            return CompatDiagnosisStatusResponse(
                diagnosis_id=thread_id,
                status="failed",
                progress=0,
                message="诊断流程执行失败",
            )

        return CompatDiagnosisStatusResponse(
            diagnosis_id=thread_id,
            status="completed",
            progress=100,
            message="诊断完成",
            health_score=_extract_health_score_value(report),
        )

    token_header = http_request.headers.get("Token")
    request = request.model_copy(
        update={"auth_token": resolve_biz_auth_token(token_header, request.auth_token)}
    )
    thread_id, already_running = await _create_diagnosis_task(request)
    if already_running:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "该企业已有诊断正在执行，请等待完成后再发起",
                "diagnosis_id": thread_id,
            },
        )
    return DiagnosisStartResponse(
        thread_id=thread_id,
        ws_url=f"{API_PREFIX}/ws/diagnosis/{thread_id}",
        already_running=False,
    )


@router.post("/{thread_id}/cancel", summary="取消诊断流程")
async def cancel_diagnosis(thread_id: str):
    """取消正在运行的诊断流程。"""
    if not await running_tasks.acquire_cancel_lock(thread_id):
        raise HTTPException(status_code=409, detail="任务正在被其他请求取消，请稍后重试")
    try:
        if not await running_tasks.is_running(thread_id):
            raise HTTPException(status_code=400, detail="该诊断未在运行中")
        await running_tasks.request_cancel(thread_id)
        await async_job_service.mark_jobs_cancelled_for_thread(thread_id)

        await manager.send_progress(
            thread_id,
            {
                "type": "cancelled",
                "message": "诊断流程已取消",
                "timestamp": datetime.now(CN_TZ).isoformat(),
            },
        )

        return {"status": "cancelled", "thread_id": thread_id}
    finally:
        await running_tasks.release_cancel_lock(thread_id)


@router.get("/{thread_id}/report", summary="获取诊断报告")
async def get_diagnosis_report(thread_id: str):
    """获取单次诊断报告（优先从诊断系统 PG 读，无则从 LangGraph state 读）。"""
    # 调用 Service 层获取报告数据
    report = await diagnosis_service.get_diagnosis_report_data(thread_id)
    if report is None:
        status_data = await diagnosis_service.get_diagnosis_status(thread_id)
        status = str(status_data.get("status") or "").strip().lower()
        message = str(status_data.get("message") or "").strip()
        if status == "failed":
            raise HTTPException(status_code=409, detail=message or "诊断执行失败")
        if status in {"pending", "running"}:
            raise HTTPException(status_code=409, detail=message or "诊断尚未完成")
        if status == "not_found":
            raise HTTPException(status_code=404, detail="该次诊断不存在")
        raise HTTPException(status_code=404, detail="该次诊断报告不存在或尚未生成")
    return report


@router.get("/{thread_id}/anomalies/{indicator_code}", summary="获取异常指标详情")
async def get_anomaly_detail(thread_id: str, indicator_code: str):
    """获取单次诊断中某个异常指标的详情（含根因、钻取明细等）。"""
    # 调用 Service 层获取报告数据
    report = await diagnosis_service.get_diagnosis_report_data(thread_id)
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
        "values": {k: v for k, v in state.values.items() if k != "progress_messages"},
    }


@router.get("/{thread_id}/progress", summary="查询诊断进度")
async def get_diagnosis_progress(thread_id: str):
    """返回按流程节点组织的诊断进度，供前端轮询渲染步骤条。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}
    next_nodes = list(state.next) if state and state.next else []
    messages = values.get("progress_messages") or []

    # 如果任务仍在运行且 checkpoint 中无进度，尝试从实时缓存补充
    task = running_tasks.get(thread_id)
    is_running = (task is not None and not task.done()) or await running_tasks.is_running(thread_id)
    if is_running and not messages:
        cached = await progress_cache.aget(thread_id)
        if cached:
            messages = [
                {
                    "type": "human",
                    "content": cached.get("message", ""),
                    "percent": cached.get("percent"),
                    "timestamp": cached.get("timestamp"),
                }
            ]

    steps = build_steps(messages if isinstance(messages, list) else [])

    last_message = ""
    last_percent = 0
    last_timestamp = None
    for msg in reversed(messages if isinstance(messages, list) else []):
        if not isinstance(msg, dict):
            continue
        if not last_message:
            last_message = str(msg.get("content", "")).strip()
        if msg.get("percent") is not None and last_percent == 0:
            try:
                last_percent = int(float(msg["percent"]))
            except (TypeError, ValueError):
                pass
        if not last_timestamp and msg.get("timestamp"):
            last_timestamp = msg["timestamp"]
        if last_message and last_percent and last_timestamp:
            break

    if "wait_adoption" in next_nodes:
        status = "completed"
        last_percent = 100
        if not last_message:
            last_message = "方案生成完成"
        for s in steps:
            if s["status"] != "pending":
                s["status"] = "completed"
    elif next_nodes:
        status = "running"
    else:
        report = values.get("diagnosis_report")
        if report is not None:
            status = "completed"
            if last_percent < 100:
                last_percent = 100
            if not last_message:
                last_message = "诊断流程已完成"
            for s in steps:
                if s["status"] != "pending":
                    s["status"] = "completed"
        elif await running_tasks.is_running(thread_id):
            status = "running"
        else:
            status = "idle"

    task = running_tasks.get(thread_id)
    is_running = (task is not None and not task.done()) or await running_tasks.is_running(thread_id)

    current_step = None
    for s in steps:
        if s["status"] == "running":
            current_step = s["node"]
            break

    return {
        "thread_id": thread_id,
        "status": status,
        "is_running": is_running,
        "percent": max(0, min(100, last_percent)),
        "message": last_message,
        "last_timestamp": last_timestamp,
        "current_step": current_step,
        "steps": steps,
    }
