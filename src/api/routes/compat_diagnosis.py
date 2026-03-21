"""前端兼容层 — /diagnosis/list、/diagnosis/report/{id}、/diagnosis/benchmarks/dimension-scores。

将后端内部数据结构转换为前端 DiagnosisReport / DiagnosisListItem 期望的格式。
"""

from __future__ import annotations

import logging
import hashlib
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row

from src.core.diagnosis_report_repo import list_reports, get_report as get_report_from_db
from src.core.calculator import (
    INDICATOR_META,
    DEFAULT_BENCHMARKS,
    DEFAULT_DIMENSION_WEIGHTS,
    ALL_DIMENSIONS,
    calculate_dimension_benchmarks_scores,
)
from src.api.deps import get_graph_app, running_tasks
from src.core.config import CN_TZ
from src.api.routes.compat_ws import get_running_threads_for_enterprise

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnosis", tags=["诊断(兼容层)"])

# ── 维度中文名 ──────────────────────────────────────────────────
_DIMENSION_DISPLAY_NAMES: dict[str, str] = {
    "crm": "CRM共享",
    "marketing": "营销效果",
    "retention": "客户留存",
    "efficiency": "运营效率",
}

_STATUS_LABELS: dict[str, str] = {
    "excellent": "excellent",
    "good": "good",
    "warning": "warning",
    "danger": "danger",
}


def _score_to_status(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "warning"
    return "danger"


def _normalize_recommendations(val: object) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, list):
        return [x.strip() for x in val if isinstance(x, str) and x.strip()]
    return []


async def _build_running_item(thread_id: str) -> dict | None:
    """为尚未入库但正在运行的任务构建列表项。"""
    status = "running"
    progress = 0
    message = "诊断执行中..."

    try:
        app = await get_graph_app()
        config = {"configurable": {"thread_id": thread_id}}
        state = await app.aget_state(config)
        values = state.values if state and state.values else {}
        msgs = values.get("progress_messages") or []
        if msgs:
            last = msgs[-1] if isinstance(msgs[-1], dict) else {}
            message = str(last.get("content", "")) or message
            try:
                progress = int(float(last.get("percent", 0)))
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    return {
        "diagnosis_id": thread_id,
        "status": status,
        "progress": progress,
        "message": message,
        "error_message": None,
        "health_score": None,
        "anomaly_count": None,
        "trigger_type": "manual",
        "created_at": datetime.now(CN_TZ).isoformat(),
    }


# ── /diagnosis/list ─────────────────────────────────────────────

@router.get("/list", summary="诊断历史列表(兼容)")
async def compat_diagnosis_list(
    enterprise_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """兼容前端 GET /diagnosis/list?enterprise_id&skip&limit。

    内部调用 list_reports(tenant_id, page, page_size) 并补充 status/health_score 等字段。
    同时将 running_tasks 中尚未入库的运行中任务注入到列表最前面。
    """
    page = skip // limit + 1 if limit else 1
    items, total = await list_reports(enterprise_id, None, page, limit)

    db_thread_ids = {row.get("thread_id", "") for row in items}

    # 找出正在运行但尚未入库的任务（thread_id 不在 DB 结果中）
    running_not_in_db: list[dict] = []
    if enterprise_id and skip == 0:
        running_thread_ids = get_running_threads_for_enterprise(enterprise_id)
        for tid in running_thread_ids:
            task = running_tasks.get(tid)
            if task and not task.done() and tid not in db_thread_ids:
                item = await _build_running_item(tid)
                if item:
                    running_not_in_db.append(item)

    result_items = []

    # 先放 running 但未入库的任务
    result_items.extend(running_not_in_db)

    for row in items:
        thread_id = row.get("thread_id", "")
        report = await get_report_from_db(thread_id)

        status = "completed"
        progress = 100
        message = None
        error_message = None
        health_score_val = None
        anomaly_count = None

        if report:
            health_score_val = report.get("health_score")
            anomalies = report.get("anomalies") or []
            anomaly_count = len(anomalies)
        else:
            task = running_tasks.get(thread_id)
            is_task_running = task and not task.done()

            app = await get_graph_app()
            config = {"configurable": {"thread_id": thread_id}}
            try:
                state = await app.aget_state(config)
                values = state.values if state and state.values else {}
                if values.get("diagnosis_report"):
                    report = values["diagnosis_report"]
                    health_score_val = report.get("health_score")
                    anomaly_count = len(report.get("anomalies") or [])
                elif is_task_running or state.next:
                    status = "running"
                    msgs = values.get("progress_messages") or []
                    if msgs:
                        last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                        message = str(last.get("content", ""))
                        try:
                            progress = int(float(last.get("percent", 0)))
                        except (TypeError, ValueError):
                            pass
                    else:
                        message = "诊断执行中..."
                        progress = 0
                else:
                    status = "failed"
                    msgs = values.get("progress_messages") or []
                    for m in reversed(msgs):
                        if isinstance(m, dict) and m.get("content"):
                            error_message = str(m["content"])
                            message = error_message
                            break
            except Exception:
                if is_task_running:
                    status = "running"
                    progress = 0
                    message = "诊断执行中..."
                else:
                    status = "failed"
                    error_message = "无法获取诊断状态"

        result_items.append({
            "diagnosis_id": thread_id,
            "status": status,
            "progress": progress,
            "message": message,
            "error_message": error_message,
            "health_score": health_score_val,
            "anomaly_count": anomaly_count,
            "trigger_type": row.get("trigger_type", "manual"),
            "created_at": row["created_at"].isoformat() if hasattr(row.get("created_at"), "isoformat") else row.get("created_at"),
        })

    adjusted_total = total + len(running_not_in_db)
    return {"items": result_items, "total": adjusted_total}


# ── /diagnosis/report/{id} ─────────────────────────────────────

def _extract_total_score(raw: dict) -> float:
    raw_health_score = raw.get("health_score", 0)
    if isinstance(raw_health_score, dict):
        return float(raw_health_score.get("total_score", 0))
    return float(raw_health_score)


def _empty_health_trend() -> dict:
    return {"previous_score": None, "change": None, "direction": None}


async def _compute_health_trend(
    diagnosis_id: str,
    tenant_id: str | None,
    current_total_score: float,
) -> dict:
    """对比同租户按时间倒序的上一份已落库报告，计算综合健康度变化。"""
    empty = _empty_health_trend()
    if not tenant_id:
        return empty
    try:
        items, _ = await list_reports(tenant_id, None, 1, 100)
    except Exception as e:
        logger.debug("趋势计算列表失败: %s", e)
        return empty
    idx = next((i for i, row in enumerate(items) if row.get("thread_id") == diagnosis_id), None)
    if idx is None or idx + 1 >= len(items):
        return empty
    prev_tid = items[idx + 1].get("thread_id")
    if not prev_tid:
        return empty
    prev_report = await get_report_from_db(prev_tid)
    if not prev_report:
        return empty
    prev_hs = prev_report.get("health_score", 0)
    if isinstance(prev_hs, dict):
        prev_score = float(prev_hs.get("total_score", 0))
    else:
        prev_score = float(prev_hs)
    change = round(current_total_score - prev_score, 1)
    if change > 0:
        direction = "up"
    elif change < 0:
        direction = "down"
    else:
        direction = "stable"
    return {
        "previous_score": round(prev_score, 1),
        "change": change,
        "direction": direction,
    }


def _transform_report(thread_id: str, raw: dict, trend: dict | None = None) -> dict:
    """将后端原始 report dict 转换为前端 DiagnosisReport 结构。"""

    raw_health_score = raw.get("health_score", 0)
    if isinstance(raw_health_score, dict):
        total_score = raw_health_score.get("total_score", 0)
    else:
        total_score = float(raw_health_score)

    raw_dim_scores = raw.get("dimension_scores") or {}
    dim_indicator_scores = raw.get("dimension_indicator_scores") or {}
    dim_benchmarks = raw.get("dimension_benchmarks") or {}

    dimension_scores_list = []
    for dim_name, dim_data in raw_dim_scores.items():
        score = dim_data.get("score", 60) if isinstance(dim_data, dict) else float(dim_data)
        weight = dim_data.get("weight", DEFAULT_DIMENSION_WEIGHTS.get(dim_name, 0.25)) if isinstance(dim_data, dict) else DEFAULT_DIMENSION_WEIGHTS.get(dim_name, 0.25)

        metrics_detail = []
        for ind in dim_indicator_scores.get(dim_name, []):
            code = ind.get("indicator_code", "")
            bench = DEFAULT_BENCHMARKS.get(code, {})
            metrics_detail.append({
                "name": code,
                "display_name": ind.get("indicator_name", code),
                "value": ind.get("current_value", 0),
                "unit": ind.get("unit", "%"),
                "score": ind.get("score", 60),
                "benchmark_avg": bench.get("avg_value", 0) if isinstance(bench, dict) else 0,
                "benchmark_excellent": bench.get("excellent_value", 0) if isinstance(bench, dict) else 0,
            })

        dimension_scores_list.append({
            "dimension": dim_name,
            "score": score,
            "weight": weight,
            "weighted_score": round(score * weight, 2),
            "status": _score_to_status(score),
            "metrics_detail": metrics_detail,
        })

    raw_anomalies = raw.get("anomalies") or []
    anomalies_list = []
    for a in raw_anomalies:
        root_cause = a.get("root_cause")
        root_cause_chain = []
        if root_cause and isinstance(root_cause, dict):
            cause_text = root_cause.get("cause", "")
            if cause_text:
                root_cause_chain = [s.strip() for s in cause_text.split("→") if s.strip()] or [cause_text]
        code = a.get("indicator_code", "")
        meta = INDICATOR_META.get(code, {})

        stable_id = a.get("id") or hashlib.md5(f"{thread_id}:{code}".encode()).hexdigest()[:8]
        anomalies_list.append({
            "id": stable_id,
            "rule_id": code,
            "rule_name": a.get("indicator_name") or meta.get("name", code),
            "metric_name": code,
            "dimension": a.get("dimension", ""),
            "current_value": a.get("current_value", 0),
            "benchmark_value": a.get("benchmark_avg"),
            "gap_percentage": abs(a.get("deviation_pct", 0)),
            "severity": _map_severity(a.get("severity", "low")),
            "root_cause_chain": root_cause_chain,
            "unit": meta.get("unit", "%"),
        })

    raw_root_causes = raw.get("root_causes") or []
    root_cause_analyses = []
    for rc in raw_root_causes:
        root_cause_analyses.append({
            "metric_name": rc.get("anomaly_indicator", ""),
            "cause_chain": [
                {"step": 1, "description": rc.get("cause", ""), "is_root": True},
            ],
            "explanation": rc.get("evidence", ""),
            "recommendations": _normalize_recommendations(rc.get("recommendations")),
        })

    benchmark_dimension_scores = []
    dim_bench_scores = raw.get("dimension_benchmarks_scores") or {}
    if dim_bench_scores:
        for dim_name, score in dim_bench_scores.items():
            benchmark_dimension_scores.append({
                "dimension": dim_name,
                "score": score,
            })

    health_score_obj = {
        "total_score": round(total_score, 1),
        "status": _score_to_status(total_score),
        "dimension_scores": dimension_scores_list,
        "trend": trend if trend is not None else _empty_health_trend(),
    }

    return {
        "diagnosis_id": thread_id,
        "enterprise_id": raw.get("tenant_id", ""),
        "store_id": raw.get("store_id", ""),
        "status": "completed",
        "health_score": health_score_obj,
        "anomalies": anomalies_list,
        "root_cause_analyses": root_cause_analyses,
        "benchmark_dimension_scores": benchmark_dimension_scores,
        "created_at": raw.get("generated_at"),
        "completed_at": raw.get("generated_at"),
        "summary": raw.get("summary", ""),
    }


def _map_severity(sev: str) -> str:
    return {"high": "critical", "medium": "high", "low": "medium"}.get(sev, sev)


@router.get("/report/{diagnosis_id}", summary="诊断报告(兼容)")
async def compat_diagnosis_report(diagnosis_id: str):
    """兼容前端 GET /diagnosis/report/{diagnosisId}。

    将后端原始报告转换为前端 DiagnosisReport 类型。
    """
    report = await get_report_from_db(diagnosis_id)
    if report is None:
        app = await get_graph_app()
        config = {"configurable": {"thread_id": diagnosis_id}}
        state = await app.aget_state(config)
        if state and state.values:
            report = state.values.get("diagnosis_report")
    if report is None:
        raise HTTPException(status_code=404, detail="诊断报告不存在或尚未生成")

    trend = await _compute_health_trend(
        diagnosis_id,
        report.get("tenant_id"),
        _extract_total_score(report),
    )
    return _transform_report(diagnosis_id, report, trend)


# ── /diagnosis/benchmarks/dimension-scores ──────────────────────

@router.get("/benchmarks/dimension-scores", summary="行业基准维度得分(兼容)")
async def compat_benchmark_dimension_scores(
    industry: str = Query(default="general"),
):
    """兼容前端 GET /diagnosis/benchmarks/dimension-scores?industry=。

    基于 DEFAULT_BENCHMARKS 按维度聚合计算行业基准得分。
    """
    dim_benchmarks: dict[str, list[dict]] = {}
    for code, meta in INDICATOR_META.items():
        dim = meta["dimension"]
        bench = DEFAULT_BENCHMARKS.get(code)
        if bench is None:
            continue
        dim_benchmarks.setdefault(dim, []).append({
            "indicator_code": code,
            "indicator_name": meta["name"],
            "unit": meta["unit"],
            "avg_value": bench.get("avg_value") if isinstance(bench, dict) else bench,
            "excellent_value": bench.get("excellent_value") if isinstance(bench, dict) else None,
        })

    scores = calculate_dimension_benchmarks_scores(dim_benchmarks)

    return {
        "industry": industry,
        "dimension_scores": [
            {"dimension": dim, "score": scores.get(dim, 60.0)}
            for dim in ALL_DIMENSIONS
        ],
    }


# ── /diagnosis/status/{id} ──────────────────────────────────────

@router.get("/status/{diagnosis_id}", summary="诊断状态(兼容)")
async def compat_diagnosis_status(diagnosis_id: str):
    """兼容前端 GET /diagnosis/status/{diagnosisId}。"""
    report = await get_report_from_db(diagnosis_id)
    if report:
        hs = report.get("health_score", 0)
        return {
            "diagnosis_id": diagnosis_id,
            "status": "completed",
            "progress": 100,
            "message": "诊断完成",
            "health_score": hs if not isinstance(hs, dict) else hs.get("total_score", 0),
        }

    task = running_tasks.get(diagnosis_id)
    if task and not task.done():
        return {
            "diagnosis_id": diagnosis_id,
            "status": "running",
            "progress": 0,
            "message": "诊断执行中...",
            "health_score": None,
        }

    app = await get_graph_app()
    config = {"configurable": {"thread_id": diagnosis_id}}
    try:
        state = await app.aget_state(config)
        values = state.values if state and state.values else {}
        if values.get("diagnosis_report"):
            hs = values["diagnosis_report"].get("health_score", 0)
            return {
                "diagnosis_id": diagnosis_id,
                "status": "completed",
                "progress": 100,
                "message": "诊断完成",
                "health_score": hs if not isinstance(hs, dict) else hs.get("total_score", 0),
            }
        if state.next:
            return {
                "diagnosis_id": diagnosis_id,
                "status": "running",
                "progress": 0,
                "message": "诊断执行中...",
                "health_score": None,
            }
    except Exception:
        pass

    return {
        "diagnosis_id": diagnosis_id,
        "status": "failed",
        "progress": 0,
        "message": "诊断不存在或已失败",
        "health_score": None,
    }


# ── /diagnosis/drill-down/{metricName} ──────────────────────────

def _empty_drill_response(metric_name: str, dimension: str, days: int, page: int, page_size: int) -> dict:
    now = datetime.now(CN_TZ)
    return {
        "metric_name": metric_name,
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


@router.get("/drill-down/{metric_name}", summary="指标钻取(兼容)")
async def compat_drill_down(
    metric_name: str,
    enterprise_id: str | None = Query(default=None),
    dimension: str = Query(default="crm"),
    days: int = Query(default=90, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """兼容前端 GET /diagnosis/drill-down/{metricName}。

    从 wlwq 模拟业务库中查询指标相关的明细数据。
    仅支持异常指标的钻取。
    """
    from src.core.calculator import DRILL_ITEM_FIELDS, DRILL_FIELD_LABELS

    meta = INDICATOR_META.get(metric_name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"未知指标: {metric_name}")

    if not meta.get("drillable"):
        raise HTTPException(status_code=400, detail=f"指标 {metric_name} 不支持钻取")

    _INDICATOR_TABLE_MAP: dict[str, tuple[str, str]] = {
        "lead_conversion_rate":       ("client_record", "create_time"),
        "response_time_avg":          ("examine_initiate", "create_time"),
        "follow_up_count":            ("examine_initiate", "create_time"),
        "coupon_redemption_rate":     ("account_coupon", "create_time"),
        "browse_to_order_rate":       ("store_order", "create_time"),
        "order_conversion_rate":      ("store_order", "pay_time"),
        "seckill_conversion_rate":    ("store_seckill_apply", "start_time"),
        "repurchase_rate":            ("client_record", "create_time"),
        "refund_rate":                ("store_refund_order", "refund_apply_time"),
        "churn_rate":                 ("client_record", "create_time"),
        "positive_review_rate":       ("store_order_evaluate", "create_time"),
        "avg_customer_lifetime_value":("store_order", "create_time"),
        "service_completion_rate":    ("store_order", "create_time"),
        "avg_shipping_hours":         ("store_order", "pay_time"),
        "task_on_time_rate":          ("examine_initiate", "create_time"),
    }

    table_info = _INDICATOR_TABLE_MAP.get(metric_name)
    if not table_info:
        return _empty_drill_response(metric_name, dimension, days, page, page_size)

    table_name, date_field = table_info
    drill_fields = DRILL_ITEM_FIELDS.get(metric_name, [])
    fields_sql = ", ".join(drill_fields) if drill_fields else "*"

    field_labels = {k: DRILL_FIELD_LABELS.get(k, k) for k in drill_fields}

    now_cn = datetime.now(CN_TZ)
    start_cn = now_cn - timedelta(days=days)
    # wlwq 表字段多为无时区本地时间，按中国墙钟传参
    start_date = start_cn.replace(tzinfo=None)

    try:
        from src.wlwq.database import get_pool

        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                count_sql = f"SELECT COUNT(*) FROM {table_name} WHERE {date_field} >= %s"
                await cur.execute(count_sql, (start_date,))
                total = (await cur.fetchone() or {}).get("count", 0)

                offset = (page - 1) * page_size
                data_sql = (
                    f"SELECT {fields_sql} FROM {table_name} "
                    f"WHERE {date_field} >= %s "
                    f"ORDER BY {date_field} DESC OFFSET %s LIMIT %s"
                )
                await cur.execute(data_sql, (start_date, offset, page_size))
                rows = await cur.fetchall()

        serialized = []
        for row in rows:
            item = {}
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    item[k] = v.isoformat()
                elif isinstance(v, (int, float, str, bool, type(None))):
                    item[k] = v
                else:
                    item[k] = str(v)
            serialized.append(item)

        return {
            "metric_name": metric_name,
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
    except Exception as e:
        logger.warning("指标钻取查询失败 %s: %s", metric_name, e)
        return _empty_drill_response(metric_name, dimension, days, page, page_size)


@router.get("/anomaly/{diagnosis_id}/{anomaly_id}", summary="异常指标详情(兼容)")
async def compat_anomaly_detail(diagnosis_id: str, anomaly_id: str):
    """兼容前端 GET /diagnosis/anomaly/{diagnosisId}/{anomalyId}。"""
    report = await get_report_from_db(diagnosis_id)
    if report is None:
        app = await get_graph_app()
        config = {"configurable": {"thread_id": diagnosis_id}}
        state = await app.aget_state(config)
        if state and state.values:
            report = state.values.get("diagnosis_report")
    if report is None:
        raise HTTPException(status_code=404, detail="诊断报告不存在")

    trend = await _compute_health_trend(
        diagnosis_id,
        report.get("tenant_id"),
        _extract_total_score(report),
    )
    transformed = _transform_report(diagnosis_id, report, trend)
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
