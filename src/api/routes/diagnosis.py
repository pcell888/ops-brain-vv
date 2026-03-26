"""诊断相关 HTTP 接口。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Query, HTTPException, Request
from pydantic import BaseModel

from src.api.constants import API_PREFIX
from src.core.models import DiagnosisRequest, DiagnosisStartResponse
from src.core.config import CN_TZ
from src.core.calculator import list_available_indicators
from src.core.calculator import (
    DRILL_ITEM_FIELDS,
    DRILL_FIELD_LABELS,
    INDICATOR_META,
    filter_drill_row_by_allowed_fields,
)
from src.core.diagnosis_report_repo import list_reports, get_report as get_report_from_db
from src.core.tenant_config import get_tenant_config
from src.api.deps import (
    astream_events_with_retry,
    get_graph_app,
    manager,
    running_tasks,
    generate_thread_id,
    progress_cache,
)
from src.api.routes.compat_ws import (
    get_active_diagnosis_thread_for_tenant,
    register_thread_enterprise,
    unregister_thread,
)
from src.agent.tools import set_progress_sender, clear_progress_sender
from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient, BizAPIError
from src.api.token_sync import resolve_biz_auth_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnosis", tags=["诊断"])


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


_METRIC_NAME_TO_CODE = {code.lower(): code for code in INDICATOR_META.keys()}
_METRIC_NAME_TO_CODE.update(
    {(meta.get("name") or "").strip().lower(): code for code, meta in INDICATOR_META.items() if meta.get("name")}
)

_biz_router = TenantRouter()
_biz = BizAPIClient(_biz_router)


def _resolve_metric_code(metric_name: str) -> str | None:
    key = (metric_name or "").strip().lower()
    return _METRIC_NAME_TO_CODE.get(key)


_DRILL_ENDPOINT_MAP: dict[str, tuple[str, dict]] = {
    "lead_conversion_rate": ("/client-record/list", {"filterType": "low_conversion"}),
    "response_time_avg": ("/examine-initiate/follow-stats", {"filterType": "slow_response"}),
    "follow_up_count": ("/examine-initiate/follow-stats", {"detail": "true"}),
    "coupon_redemption_rate": ("/account-coupon/statistics", {"filterType": "unused"}),
    "browse_to_order_rate": ("/manage-data/exposure-stats", {"detail": "true"}),
    "order_conversion_rate": ("/store-order/conversion-stats", {"detail": "true"}),
    "seckill_conversion_rate": ("/seckill-apply/conversion-stats", {"detail": "true"}),
    "repurchase_rate": ("/client-record/list", {"filterType": "no_repurchase"}),
    "refund_rate": ("/store-refund-order/statistics", {"detail": "true"}),
    "churn_rate": ("/client-record/list", {"filterType": "churn_risk"}),
    "positive_review_rate": ("/store-order-evaluate/statistics", {"filterType": "negative"}),
    "avg_customer_lifetime_value": ("/store-order/repurchase-stats", {"detail": "true"}),
    "service_completion_rate": ("/service-order/completion-stats", {"detail": "true"}),
    "avg_shipping_hours": ("/store-order/shipping-stats", {"detail": "true"}),
}


async def _query_drill_data_from_wlwq(
    metric_code: str,
    enterprise_id: str,
    days: int,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    now = datetime.now(CN_TZ)
    start_at = now - timedelta(days=days)
    endpoint_conf = _DRILL_ENDPOINT_MAP.get(metric_code)
    if endpoint_conf is None:
        return [], 0
    endpoint, extra_params = endpoint_conf
    # enterprise_id 仅用于租户路由；全企业钻取传 storeId=""（与业务约定一致）
    params = {
        "storeId": "",
        "startDate": start_at.strftime("%Y-%m-%d %H:%M:%S"),
        "endDate": now.strftime("%Y-%m-%d %H:%M:%S"),
        "pageNo": page,
        "pageSize": page_size,
    }
    params.update(extra_params)
    try:
        data = await _biz.get(enterprise_id, endpoint, params)
    except BizAPIError as e:
        logger.error(
            "指标钻取调用业务接口失败: metric=%s enterprise_id=%s endpoint=%s status=%s url=%s error=%s",
            metric_code,
            enterprise_id,
            endpoint,
            e.status_code,
            e.url,
            e.message,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="调用业务侧接口失败，请稍后重试") from e
    except Exception as e:
        logger.error(
            "指标钻取调用业务接口异常: metric=%s enterprise_id=%s endpoint=%s error=%s",
            metric_code,
            enterprise_id,
            endpoint,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="调用业务侧接口异常，请稍后重试") from e

    raw_items = data.get("list") if isinstance(data, dict) else None
    if raw_items is None and isinstance(data, dict):
        raw_items = data.get("items")
    if raw_items is None:
        raw_items = [data] if isinstance(data, dict) and data else []

    allowed = DRILL_ITEM_FIELDS.get(metric_code)
    if allowed:
        items = [filter_drill_row_by_allowed_fields(it, allowed) for it in raw_items]
    else:
        items = raw_items
    total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
    return items, int(total or 0)


@router.get("/indicators", summary="获取可选指标清单")
async def get_available_indicators(
    dimensions: list[str] | None = Query(
        default=None, description="按维度筛选，如 ?dimensions=crm&dimensions=marketing"
    ),
):
    """返回所有可选指标清单（按维度分组），供前端构建选择 UI。"""
    grouped = list_available_indicators(dimensions)
    flat = [ind for inds in grouped.values() for ind in inds]
    return {
        "total": len(flat),
        "dimensions": list(grouped.keys()),
        "by_dimension": grouped,
    }


@router.get("/drill-down/{metric_name}", summary="指标钻取")
async def get_diagnosis_drill_down(
    metric_name: str,
    enterprise_id: str | None = Query(default=None, description="企业ID"),
    dimension: str = Query(default="crm", description="维度"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
):
    if not enterprise_id:
        raise HTTPException(status_code=400, detail="enterprise_id 不能为空")
    metric_code = _resolve_metric_code(metric_name)
    if not metric_code:
        raise HTTPException(status_code=404, detail=f"不支持的指标: {metric_name}")

    tenant_config = await get_tenant_config(enterprise_id)
    days = int(tenant_config.get("analysis_period_days") or 30)
    rows, total = await _query_drill_data_from_wlwq(metric_code, enterprise_id, days, page, page_size)
    now = datetime.now(CN_TZ)
    start = now - timedelta(days=days)
    fields = DRILL_ITEM_FIELDS.get(metric_code, [])
    field_labels = {f: DRILL_FIELD_LABELS.get(f, f) for f in fields}

    return {
        "metric_name": metric_name,
        "metric_code": metric_code,
        "dimension": dimension,
        "time_range": {
            "start": start.isoformat(),
            "end": now.isoformat(),
        },
        "data": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "field_labels": field_labels,
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
        set_progress_sender(thread_id, manager)
        async for event in astream_events_with_retry(initial_state, config):
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
        logger.error("诊断流程异常: %s", e, exc_info=True)
        progress_cache[thread_id] = {
            "message": f"诊断流程出错: {str(e)}",
            "percent": 0,
            "timestamp": datetime.now(CN_TZ).isoformat(),
        }
        await manager.send_progress(
            thread_id,
            {
                "type": "error",
                "message": f"诊断流程出错: {str(e)}",
                "timestamp": datetime.now(CN_TZ).isoformat(),
            },
        )
        return
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
    items, total = await list_reports(tenant_id, store_id, page, page_size)
    for row in items:
        if "created_at" in row and hasattr(row["created_at"], "isoformat"):
            row["created_at"] = row["created_at"].isoformat()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def _create_diagnosis_task(
    request: DiagnosisRequest,
) -> tuple[str, bool, asyncio.Task | None]:
    lock = await _get_tenant_diagnosis_start_lock(request.tenant_id)
    async with lock:
        existing = get_active_diagnosis_thread_for_tenant(request.tenant_id)
        if existing:
            return existing, True, running_tasks.get(existing)

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
                request.auth_token,
            )
        )
        running_tasks[thread_id] = task

        def _on_done(_):
            running_tasks.pop(thread_id, None)
            unregister_thread(thread_id)

        task.add_done_callback(_on_done)
        register_thread_enterprise(thread_id, request.tenant_id)
        return thread_id, False, task


async def _get_report_snapshot(thread_id: str) -> dict | None:
    report = await get_report_from_db(thread_id)
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
        thread_id, already_running, task = await _create_diagnosis_task(compat_request)

        if request.async_mode:
            return CompatDiagnosisStatusResponse(
                diagnosis_id=thread_id,
                status="running" if already_running else "pending",
                progress=0,
                message="已有诊断正在执行" if already_running else "诊断任务已提交",
            )

        if task is None:
            return CompatDiagnosisStatusResponse(
                diagnosis_id=thread_id,
                status="running" if already_running else "failed",
                progress=0,
                message="已有诊断正在执行" if already_running else "诊断任务启动失败",
            )

        await task
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
    thread_id, already_running, _ = await _create_diagnosis_task(request)
    return DiagnosisStartResponse(
        thread_id=thread_id,
        ws_url=f"{API_PREFIX}/ws/diagnosis/{thread_id}",
        already_running=already_running,
    )


@router.post("/{thread_id}/cancel", summary="取消诊断流程")
async def cancel_diagnosis(thread_id: str):
    """取消正在运行的诊断流程。"""
    task = running_tasks.get(thread_id)
    if task is None or task.done():
        raise HTTPException(status_code=400, detail="该诊断未在运行中")

    task.cancel()
    # 不在此处 pop running_tasks，由 task 完成时的 _on_done 统一清理，避免取消过程中又启动同一 tenant 的第二个诊断

    await manager.send_progress(
        thread_id,
        {
            "type": "cancelled",
            "message": "诊断流程已取消",
            "timestamp": datetime.now(CN_TZ).isoformat(),
        },
    )

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
        "values": {k: v for k, v in state.values.items() if k != "progress_messages"},
    }


_DIAGNOSIS_STEPS = [
    ("collect_data", "数据采集"),
    ("diagnose", "诊断分析"),
    ("generate_solutions", "方案生成"),
]

_STEP_PERCENT_RANGE = {
    "collect_data": (0, 35),
    "diagnose": (35, 70),
    "generate_solutions": (70, 100),
}


def _build_steps(messages: list[dict]) -> list[dict]:
    """将 progress_messages 按节点聚合成 steps 列表。"""
    steps: dict[str, dict] = {}
    for node, label in _DIAGNOSIS_STEPS:
        steps[node] = {
            "node": node,
            "label": label,
            "status": "pending",
            "percent_range": list(_STEP_PERCENT_RANGE[node]),
            "messages": [],
            "started_at": None,
            "completed_at": None,
        }

    current_node: str | None = None
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content", "")).strip()
        ts = msg.get("timestamp")
        pct = msg.get("percent")

        matched_node = None
        if pct is not None:
            try:
                pct_val = float(pct)
            except (TypeError, ValueError):
                pct_val = None
            if pct_val is not None:
                for node, (lo, hi) in _STEP_PERCENT_RANGE.items():
                    if lo <= pct_val <= hi:
                        matched_node = node
                        break
        if matched_node is None:
            matched_node = current_node

        if matched_node and matched_node in steps:
            current_node = matched_node
            step = steps[matched_node]
            if step["status"] == "pending":
                step["status"] = "running"
                step["started_at"] = ts
            if content:
                step["messages"].append(
                    {
                        "text": content,
                        "percent": pct,
                        "timestamp": ts,
                    }
                )

    for node, _ in _DIAGNOSIS_STEPS:
        step = steps[node]
        if step["messages"]:
            last_pct = step["messages"][-1].get("percent")
            if last_pct is not None:
                try:
                    _, hi = _STEP_PERCENT_RANGE[node]
                    if float(last_pct) >= hi:
                        step["status"] = "completed"
                        step["completed_at"] = step["messages"][-1].get("timestamp")
                except (TypeError, ValueError):
                    pass

    return [steps[node] for node, _ in _DIAGNOSIS_STEPS]


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
    is_running = task is not None and not task.done()
    if is_running and not messages:
        cached = progress_cache.get(thread_id)
        if cached:
            messages = [
                {
                    "type": "human",
                    "content": cached.get("message", ""),
                    "percent": cached.get("percent"),
                    "timestamp": cached.get("timestamp"),
                }
            ]

    steps = _build_steps(messages if isinstance(messages, list) else [])

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
        status = "pending_adoption"
        last_percent = 100
        if not last_message:
            last_message = "方案已生成，等待采纳"
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
        elif thread_id in running_tasks:
            status = "running"
        else:
            status = "idle"

    task = running_tasks.get(thread_id)
    is_running = task is not None and not task.done()

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
