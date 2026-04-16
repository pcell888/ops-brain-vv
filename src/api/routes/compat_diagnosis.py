"""前端兼容层 — /diagnosis/list、/diagnosis/report/{id}、/diagnosis/benchmarks/dimension-scores。

薄适配器：仅负责参数映射和响应格式转换，业务逻辑委托给 Service 层。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from src.api.routes import drill_down as drill_routes
from src.services import diagnosis_service
from src.core.calculator import INDICATOR_META, DRILL_ITEM_FIELDS, DRILL_FIELD_LABELS
from src.core.config import CN_TZ
from src.runtime.progress_store import progress_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnosis", tags=["诊断(兼容层)"])


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

@router.get("/list", summary="诊断历史列表(兼容)")
async def compat_diagnosis_list(
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

@router.get("/report/{diagnosis_id}", summary="诊断报告(兼容)")
async def compat_diagnosis_report(diagnosis_id: str):
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

    # 计算健康趋势
    total_score = diagnosis_service.extract_total_score(report)
    trend = await diagnosis_service.compute_health_trend(
        diagnosis_id,
        report.get("tenant_id"),
        total_score,
    )
    return diagnosis_service.transform_report_to_frontend_format(diagnosis_id, report, trend)


@router.get("/benchmarks/dimension-scores", summary="行业基准维度得分(兼容)")
async def compat_benchmark_dimension_scores(
    industry: str = Query(default="general"),
):
    return diagnosis_service.calculate_benchmark_dimension_scores(industry)


@router.get("/status/{diagnosis_id}", summary="诊断状态(兼容)")
async def compat_diagnosis_status(diagnosis_id: str):
    status_data = await diagnosis_service.get_diagnosis_status(diagnosis_id)

    # 如果状态是 not_found，抛出 404
    if status_data.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="诊断记录不存在")

    recent_progress_messages = await _recent_progress_messages(diagnosis_id)
    if recent_progress_messages:
        status_data = dict(status_data)
        status_data["recent_progress_messages"] = recent_progress_messages

    return status_data


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
    enterprise_id: Annotated[str, Query(min_length=1, description="企业ID（必填）")],
    dimension: str = Query(default="crm"),
    days: int = Query(default=90, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    meta = INDICATOR_META.get(metric_name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"未知指标: {metric_name}")

    if not meta.get("drillable"):
        raise HTTPException(status_code=400, detail=f"指标 {metric_name} 不支持钻取")

    metric_code = drill_routes._resolve_metric_code(metric_name) or metric_name
    if metric_code not in drill_routes._DRILL_ENDPOINT_MAP:
        return _empty_drill_response(metric_name, dimension, days, page, page_size)

    drill_fields = DRILL_ITEM_FIELDS.get(metric_name, [])
    field_labels = {k: DRILL_FIELD_LABELS.get(k, k) for k in drill_fields}

    now_cn = datetime.now(CN_TZ)
    start_cn = now_cn - timedelta(days=days)
    eid = enterprise_id

    try:
        rows, total = await drill_routes.query_drill_data_from_biz(
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


@router.get("/anomaly/{diagnosis_id}/{anomaly_id}", summary="异常指标详情(兼容)")
async def compat_anomaly_detail(diagnosis_id: str, anomaly_id: str):
    report = await diagnosis_service.get_diagnosis_report_data(diagnosis_id)
    if report is None:
        raise HTTPException(status_code=404, detail="诊断报告不存在")

    # 计算趋势并转换格式
    total_score = diagnosis_service.extract_total_score(report)
    trend = await diagnosis_service.compute_health_trend(
        diagnosis_id,
        report.get("tenant_id"),
        total_score,
    )
    transformed = diagnosis_service.transform_report_to_frontend_format(diagnosis_id, report, trend)
    
    # 查找异常指标
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
