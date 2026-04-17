"""指标钻取逻辑 — 从 diagnosis.py 提取。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from src.core.calculator import (
    DRILL_ITEM_FIELDS,
    DRILL_FIELD_LABELS,
    INDICATOR_META,
    filter_drill_row_by_allowed_fields,
    list_available_indicators,
)
from src.core.config import CN_TZ
from src.core.tenant_config import get_tenant_config
from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient, BizAPIError

logger = logging.getLogger(__name__)
router = APIRouter()

_METRIC_NAME_TO_CODE = {code.lower(): code for code in INDICATOR_META.keys()}
_METRIC_NAME_TO_CODE.update(
    {(meta.get("name") or "").strip().lower(): code for code, meta in INDICATOR_META.items() if meta.get("name")}
)

_biz_router = TenantRouter()
_biz = BizAPIClient(_biz_router)


def _resolve_metric_code(metric_name: str) -> str | None:
    return _METRIC_NAME_TO_CODE.get((metric_name or "").strip().lower())


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


async def query_drill_data_from_biz(
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
        logger.exception("指标钻取调用业务接口失败: metric=%s enterprise_id=%s", metric_code, enterprise_id)
        raise HTTPException(status_code=502, detail="调用业务侧接口失败，请稍后重试") from e
    except Exception as e:
        logger.exception("指标钻取调用业务接口异常: metric=%s enterprise_id=%s", metric_code, enterprise_id)
        raise HTTPException(status_code=502, detail="调用业务侧接口异常，请稍后重试") from e

    raw_items = data.get("list") if isinstance(data, dict) else None
    if raw_items is None and isinstance(data, dict):
        raw_items = data.get("items")
    if raw_items is None:
        raw_items = [data] if isinstance(data, dict) and data else []

    allowed = DRILL_ITEM_FIELDS.get(metric_code)
    items = [filter_drill_row_by_allowed_fields(it, allowed) for it in raw_items] if allowed else raw_items
    total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
    return items, int(total or 0)


@router.get("/indicators", summary="获取可选指标清单")
async def get_available_indicators(
    dimensions: list[str] | None = Query(default=None),
):
    grouped = list_available_indicators(dimensions)
    flat = [ind for inds in grouped.values() for ind in inds]
    return {"total": len(flat), "dimensions": list(grouped.keys()), "by_dimension": grouped}


@router.get("/drill-down/{metric_name}", summary="指标钻取")
async def get_diagnosis_drill_down(
    metric_name: str,
    enterprise_id: str | None = Query(default=None),
    dimension: str = Query(default="crm"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
):
    logger.info(
        "指标钻取(新API) 收到请求 metric_name=%s enterprise_id=%s dimension=%s page=%s page_size=%s",
        metric_name,
        enterprise_id,
        dimension,
        page,
        page_size,
    )
    if not enterprise_id:
        raise HTTPException(status_code=400, detail="enterprise_id 不能为空")
    metric_code = _resolve_metric_code(metric_name)
    if not metric_code:
        raise HTTPException(status_code=404, detail=f"不支持的指标: {metric_name}")

    tenant_config = await get_tenant_config(enterprise_id)
    days = int(tenant_config.get("analysis_period_days") or 30)
    logger.info(
        "指标钻取请求 metric_name=%s metric_code=%s enterprise_id=%s dimension=%s days=%s page=%s page_size=%s",
        metric_name,
        metric_code,
        enterprise_id,
        dimension,
        days,
        page,
        page_size,
    )
    rows, total = await query_drill_data_from_biz(metric_code, enterprise_id, days, page, page_size)
    now = datetime.now(CN_TZ)
    start = now - timedelta(days=days)
    fields = DRILL_ITEM_FIELDS.get(metric_code, [])
    field_labels = {f: DRILL_FIELD_LABELS.get(f, f) for f in fields}

    return {
        "metric_name": metric_name,
        "metric_code": metric_code,
        "dimension": dimension,
        "time_range": {"start": start.isoformat(), "end": now.isoformat()},
        "data": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "field_labels": field_labels,
    }
