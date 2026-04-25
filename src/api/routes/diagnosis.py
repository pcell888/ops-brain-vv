"""诊断相关 HTTP 接口。"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.api.constants import API_PREFIX
from src.core.models import DiagnosisRequest, DiagnosisStartResponse
from src.core.config import CN_TZ
from src.core.calculator import INDICATOR_META, DRILL_ITEM_FIELDS, DRILL_FIELD_LABELS
from src.core.datetime_cn import serialize_instant_cn
from src.core.progress_utils import is_thread_running_full
from src.services import async_job_service, diagnosis_service
from src.api.deps import (
    manager,
    running_tasks,
    generate_thread_id,
    progress_cache,
)
from src.repositories.diagnosis_session import get_session
from src.core.diagnosis_engine import phase_to_next_nodes
from src.runtime.task_runner import get_graph_state_values
from src.runtime.thread_enterprise import (
    get_active_diagnosis_thread_for_tenant,
    register_thread_enterprise,
)
from src.api.token_sync import resolve_biz_auth_token
from src.api.routes.drill_down import router as drill_down_router
from src.api.routes.progress import build_steps
from src.worker.arq_queue import enqueue_diagnosis_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnosis", tags=["诊断"])
router.include_router(drill_down_router)


class CompatStartDiagnosisRequest(BaseModel):
    """兼容旧版 /diagnosis/start 请求体。"""

    enterprise_id: str
    store_id: str = Field(
        default="",
        description="门店ID，为空则诊断全企业（与 DiagnosisRequest.store_id 语义一致）",
    )
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
    values, _ = await get_graph_state_values(thread_id)
    report = values.get("diagnosis_report")
    if isinstance(report, dict):
        return report
    return None


async def _recent_progress_messages(diagnosis_id: str, limit: int = 20) -> list[dict]:
    events = await progress_cache.aget_history(diagnosis_id, limit=limit)
    out: list[dict] = []
    for item in events:
        if not isinstance(item, dict):
            continue
        message = str(item.get("message") or "").strip()
        if not message:
            continue
        percent = item.get("percent")
        event_type = str(item.get("type") or "").strip().lower()
        normalized_percent = None
        if percent is not None:
            try:
                normalized_percent = int(float(percent))
            except (TypeError, ValueError):
                normalized_percent = None
        event_status = "pending" if not normalized_percent or normalized_percent <= 0 else "running"
        if event_type == "error":
            event_status = "failed"
        out.append(
            {
                "status": event_status,
                "progress": normalized_percent,
                "message": message,
                "timestamp": item.get("timestamp"),
                "stage": item.get("stage"),
            }
        )
    return out


def _empty_drill_response(metric_name: str, dimension: str, days: int, page: int, page_size: int) -> dict:
    now = datetime.now(CN_TZ)
    disp = str((INDICATOR_META.get(metric_name) or {}).get("name") or "").strip()
    return {
        "metric_name": metric_name,
        "metric_display_name": disp,
        "dimension": dimension,
        "drill_desc": "",
        "time_range": {
            "start": (now - timedelta(days=days)).isoformat(),
            "end": now.isoformat(),
        },
        "data": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "field_labels": {},
    }


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
            store_id=request.store_id,
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


@router.get("/{thread_id}/state", summary="获取诊断流程状态")
async def get_diagnosis_state(thread_id: str):
    """获取当前诊断流程状态。"""
    values, next_nodes = await get_graph_state_values(thread_id)
    return {
        "thread_id": thread_id,
        "next_nodes": next_nodes,
        "values": {k: v for k, v in values.items() if k != "progress_messages"},
    }


@router.get("/{thread_id}/progress", summary="查询诊断进度")
async def get_diagnosis_progress(thread_id: str):
    """返回按流程节点组织的诊断进度，供前端轮询渲染步骤条。"""
    values, next_nodes = await get_graph_state_values(thread_id)
    messages = values.get("progress_messages") or []

    is_running = await is_thread_running_full(thread_id)
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

    is_running = await is_thread_running_full(thread_id)

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


@router.get("/list", summary="诊断历史列表")
async def get_diagnosis_list(
    enterprise_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    tenant_id = enterprise_id
    items, total = await diagnosis_service.get_diagnosis_list_items(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        store_id=None,
        include_running=True,
    )
    return {"items": items, "total": total}


@router.get("/report/{diagnosis_id}", summary="诊断报告")
async def get_diagnosis_report(diagnosis_id: str):
    report = await diagnosis_service.get_diagnosis_report_data(diagnosis_id)
    if report is None:
        status_data = await diagnosis_service.get_diagnosis_status(diagnosis_id)
        status = str(status_data.get("status") or "").strip().lower()
        message = str(status_data.get("message") or "").strip()
        if status == "failed":
            raise HTTPException(status_code=409, detail=message or "诊断执行失败")
        if status in {"pending", "running"}:
            raise HTTPException(status_code=409, detail=message or "诊断尚未完成")
        if status == "not_found":
            raise HTTPException(status_code=404, detail="诊断记录不存在")
        raise HTTPException(status_code=404, detail="诊断报告不存在或尚未生成")

    total_score = diagnosis_service.extract_total_score(report)
    trend = await diagnosis_service.compute_health_trend(
        diagnosis_id,
        report.get("tenant_id"),
        total_score,
    )
    return diagnosis_service.transform_report_to_frontend_format(diagnosis_id, report, trend)


@router.get("/benchmarks/dimension-scores", summary="行业基准维度得分")
async def get_benchmark_dimension_scores(
    industry: str = Query(default="general"),
):
    return diagnosis_service.calculate_benchmark_dimension_scores(industry)


@router.get("/status/{diagnosis_id}", summary="诊断状态")
async def get_diagnosis_status(diagnosis_id: str):
    status_data = await diagnosis_service.get_diagnosis_status(diagnosis_id)

    if status_data.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="诊断记录不存在")

    recent_progress_messages = await _recent_progress_messages(diagnosis_id)
    if recent_progress_messages:
        status_data = dict(status_data)
        status_data["recent_progress_messages"] = recent_progress_messages

    return status_data


@router.get("/drill-down/{metric_name}", summary="指标钻取")
async def get_drill_down(
    metric_name: str,
    enterprise_id: Annotated[str, Query(min_length=1, description="企业ID（必填）")],
    dimension: str = Query(default="crm"),
    days: int = Query(default=90, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    from src.api.routes.drill_down import _resolve_metric_code, _DRILL_ENDPOINT_MAP, query_drill_data_from_biz

    logger.info(
        "指标钻取 收到请求 metric_name=%s enterprise_id=%s dimension=%s days=%s page=%s page_size=%s",
        metric_name,
        enterprise_id,
        dimension,
        days,
        page,
        page_size,
    )
    meta = INDICATOR_META.get(metric_name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"未知指标: {metric_name}")

    if not meta.get("drillable"):
        raise HTTPException(status_code=400, detail=f"指标 {metric_name} 不支持钻取")

    metric_code = _resolve_metric_code(metric_name) or metric_name
    if metric_code not in _DRILL_ENDPOINT_MAP:
        return _empty_drill_response(metric_name, dimension, days, page, page_size)

    drill_fields = DRILL_ITEM_FIELDS.get(metric_name, [])
    field_labels = {k: DRILL_FIELD_LABELS.get(k, k) for k in drill_fields}

    now_cn = datetime.now(CN_TZ)
    start_cn = now_cn - timedelta(days=days)
    eid = enterprise_id

    try:
        rows, total = await query_drill_data_from_biz(
            metric_code, eid, days, page, page_size
        )
    except HTTPException as e:
        logger.warning("指标钻取业务接口失败 %s: %s", metric_name, e.detail)
        return _empty_drill_response(metric_name, dimension, days, page, page_size)
    except Exception as e:
        logger.warning("指标钻取查询失败 %s: %s", metric_name, e)
        return _empty_drill_response(metric_name, dimension, days, page, page_size)

    serialized = []
    for row in rows:
        item = {}
        for k, v in row.items():
            if isinstance(v, (datetime, date)):
                item[k] = serialize_instant_cn(v)
            elif hasattr(v, "isoformat") and callable(v.isoformat):
                s = serialize_instant_cn(v)
                item[k] = s if s is not None else v.isoformat()
            elif isinstance(v, (int, float, str, bool, type(None))):
                item[k] = v
            else:
                item[k] = str(v)
        serialized.append(item)

    return {
        "metric_name": metric_name,
        "metric_display_name": str(meta.get("name") or "").strip(),
        "dimension": dimension,
        "drill_desc": meta.get("drill_desc", ""),
        "time_range": {
            "start": start_cn.isoformat(),
            "end": now_cn.isoformat(),
        },
        "data": serialized,
        "total": total,
        "page": page,
        "page_size": page_size,
        "field_labels": field_labels,
    }


@router.get("/anomaly/{diagnosis_id}/{anomaly_id}", summary="异常指标详情")
async def get_anomaly_detail(diagnosis_id: str, anomaly_id: str):
    report = await diagnosis_service.get_diagnosis_report_data(diagnosis_id)
    if report is None:
        raise HTTPException(status_code=404, detail="诊断报告不存在")

    total_score = diagnosis_service.extract_total_score(report)
    trend = await diagnosis_service.compute_health_trend(
        diagnosis_id,
        report.get("tenant_id"),
        total_score,
    )
    transformed = diagnosis_service.transform_report_to_frontend_format(diagnosis_id, report, trend)

    for a in transformed.get("anomalies", []):
        if a["id"] == anomaly_id or a["metric_name"] == anomaly_id:
            rc = None
            for rca in transformed.get("root_cause_analyses", []):
                if rca.get("metric_name") == a.get("metric_name"):
                    rc = rca
                    break
            return {
                "anomaly": a,
                "root_cause_analysis": rc,
                "solution_id": None,
            }
    raise HTTPException(status_code=404, detail=f"未找到异常指标: {anomaly_id}")
