"""运营指标 — 与 biz/metrics.py 同名、同签名、同 register；进程内模拟（wlwq_local 由 BizAPIClient 分流）。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from mcp.server import FastMCP

from src.mcp_servers.biz_mock import client_sales_examine, stats
from src.mcp_servers.biz_scope import effective_store_id_for_biz
from src.core.calculator import DRILL_FIELD_LABELS, DRILL_ITEM_FIELDS, filter_drill_row_by_allowed_fields

logger = logging.getLogger(__name__)


def _store_aware_params(tenant_id: str, store_id: str, start_date: str, end_date: str) -> dict:
    sid = effective_store_id_for_biz(tenant_id, store_id)
    return {"storeId": sid, "startDate": start_date, "endDate": end_date}


def _num(v, default: float | int = 0):
    return default if v is None else v


_DRILL_FETCHERS: dict[str, Callable[[dict], dict]] = {
    "/client-record/list": client_sales_examine.client_record_list,
    "/examine-initiate/follow-stats": client_sales_examine.examine_follow_stats,
    "/account-coupon/statistics": stats.coupon_statistics,
    "/manage-data/exposure-stats": stats.exposure_stats,
    "/store-order/conversion-stats": stats.conversion_stats,
    "/seckill-apply/conversion-stats": stats.seckill_conversion_stats,
    "/store-refund-order/statistics": stats.refund_statistics,
    "/store-order-evaluate/statistics": stats.evaluate_statistics,
    "/store-order/repurchase-stats": stats.repurchase_stats,
    "/service-order/completion-stats": stats.service_completion_stats,
    "/store-order/shipping-stats": stats.shipping_stats,
}


def _drill_fetch_data(endpoint: str, params: dict) -> dict:
    fn = _DRILL_FETCHERS.get(endpoint)
    return fn(params) if fn else {}


async def get_crm_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
    auth_token: str | None = None,
) -> dict:
    _ = auth_token
    logger.info(
        "Tool called: get_crm_indicators tenant=%s store=%s period=%s~%s",
        tenant_id,
        store_id,
        start_date,
        end_date,
    )
    params = _store_aware_params(tenant_id, store_id, start_date, end_date)
    clients_data, contracts_data, follows_data = await asyncio.gather(
        asyncio.to_thread(client_sales_examine.client_record_statistics, params),
        asyncio.to_thread(client_sales_examine.sales_contract_statistics, params),
        asyncio.to_thread(client_sales_examine.examine_follow_stats, params),
    )
    total_clients = _num(clients_data.get("total"), 0)
    signed_clients = _num(contracts_data.get("signedCount"), 0)
    lead_conversion_rate = (signed_clients / total_clients * 100) if total_clients > 0 else 0
    follow_total = _num(follows_data.get("followTotal"), 0)
    response_time_avg = _num(follows_data.get("avgResponseHours"), 0)
    return {
        "tenant_id": tenant_id,
        "dimension": "crm",
        "period": f"{start_date} ~ {end_date}",
        "indicators": {
            "lead_conversion_rate": {
                "value": round(lead_conversion_rate, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"total_clients": total_clients, "signed_clients": signed_clients},
            },
            "response_time_avg": {
                "value": round(response_time_avg, 2),
                "unit": "小时",
                "direction": "lower_is_better",
                "raw_data": {"avg_response_hours": response_time_avg},
            },
            "follow_up_count": {
                "value": round(follow_total, 2),
                "unit": "次",
                "direction": "higher_is_better",
                "raw_data": {"follow_total": follow_total},
            },
        },
    }


async def get_marketing_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
    auth_token: str | None = None,
) -> dict:
    _ = auth_token
    logger.info(
        "Tool called: get_marketing_indicators tenant=%s store=%s period=%s~%s",
        tenant_id,
        store_id,
        start_date,
        end_date,
    )
    params = _store_aware_params(tenant_id, store_id, start_date, end_date)
    coupon_data, order_data, exposure_data, seckill_data = await asyncio.gather(
        asyncio.to_thread(stats.coupon_statistics, params),
        asyncio.to_thread(stats.conversion_stats, params),
        asyncio.to_thread(stats.exposure_stats, params),
        asyncio.to_thread(stats.seckill_conversion_stats, params),
    )
    total_coupons = _num(coupon_data.get("totalIssued"), 0)
    used_coupons = _num(coupon_data.get("totalUsed"), 0)
    coupon_rate = (used_coupons / total_coupons * 100) if total_coupons > 0 else 0
    browse_users = _num(exposure_data.get("browseUsers"), 0)
    order_users = _num(order_data.get("orderUsers"), 0)
    browse_to_order = (order_users / browse_users * 100) if browse_users > 0 else 0
    total_orders = _num(order_data.get("totalOrders"), 0)
    completed_orders = _num(order_data.get("completedOrders"), 0)
    order_conversion = (completed_orders / total_orders * 100) if total_orders > 0 else 0
    seckill_total = _num(seckill_data.get("totalSeckillGoods"), 0)
    seckill_sold = _num(seckill_data.get("soldGoods"), 0)
    seckill_rate = (seckill_sold / seckill_total * 100) if seckill_total > 0 else 0
    return {
        "tenant_id": tenant_id,
        "dimension": "marketing",
        "period": f"{start_date} ~ {end_date}",
        "indicators": {
            "coupon_redemption_rate": {
                "value": round(coupon_rate, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"total_issued": total_coupons, "total_used": used_coupons},
            },
            "browse_to_order_rate": {
                "value": round(browse_to_order, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"browse_users": browse_users, "order_users": order_users},
            },
            "order_conversion_rate": {
                "value": round(order_conversion, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"total_orders": total_orders, "completed_orders": completed_orders},
            },
            "seckill_conversion_rate": {
                "value": round(seckill_rate, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"total_seckill_goods": seckill_total, "sold_goods": seckill_sold},
            },
        },
    }


async def get_retention_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
    auth_token: str | None = None,
) -> dict:
    _ = auth_token
    logger.info(
        "Tool called: get_retention_indicators tenant=%s store=%s period=%s~%s",
        tenant_id,
        store_id,
        start_date,
        end_date,
    )
    params = _store_aware_params(tenant_id, store_id, start_date, end_date)
    repurchase_data, refund_data, evaluate_data = await asyncio.gather(
        asyncio.to_thread(stats.repurchase_stats, params),
        asyncio.to_thread(stats.refund_statistics, params),
        asyncio.to_thread(stats.evaluate_statistics, params),
    )
    total_buyers = _num(repurchase_data.get("totalBuyers"), 0)
    repeat_buyers = _num(repurchase_data.get("repeatBuyers"), 0)
    repurchase_rate = (repeat_buyers / total_buyers * 100) if total_buyers > 0 else 0
    total_completed = _num(refund_data.get("totalCompletedOrders"), 0)
    refund_orders = _num(refund_data.get("refundOrders"), 0)
    refund_rate = (refund_orders / total_completed * 100) if total_completed > 0 else 0
    active_customers = _num(repurchase_data.get("activeCustomers"), 0)
    churned = _num(repurchase_data.get("churnedCustomers"), 0)
    churn_rate = (churned / active_customers * 100) if active_customers > 0 else 0
    total_reviews = _num(evaluate_data.get("totalReviews"), 0)
    positive_reviews = _num(evaluate_data.get("positiveReviews"), 0)
    positive_rate = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0
    avg_ltv = _num(repurchase_data.get("avgLifetimeValue"), 0)
    return {
        "tenant_id": tenant_id,
        "dimension": "retention",
        "period": f"{start_date} ~ {end_date}",
        "indicators": {
            "repurchase_rate": {
                "value": round(repurchase_rate, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"total_buyers": total_buyers, "repeat_buyers": repeat_buyers},
            },
            "refund_rate": {
                "value": round(refund_rate, 2),
                "unit": "%",
                "direction": "lower_is_better",
                "raw_data": {"refund_orders": refund_orders, "total_completed": total_completed},
            },
            "churn_rate": {
                "value": round(churn_rate, 2),
                "unit": "%",
                "direction": "lower_is_better",
                "raw_data": {"churned": churned, "active_customers": active_customers},
            },
            "positive_review_rate": {
                "value": round(positive_rate, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"positive_reviews": positive_reviews, "total_reviews": total_reviews},
            },
            "avg_customer_lifetime_value": {
                "value": round(avg_ltv, 2),
                "unit": "元",
                "direction": "higher_is_better",
                "raw_data": {"avg_ltv": avg_ltv},
            },
        },
    }


async def get_efficiency_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
    auth_token: str | None = None,
) -> dict:
    _ = auth_token
    logger.info(
        "Tool called: get_efficiency_indicators tenant=%s store=%s period=%s~%s",
        tenant_id,
        store_id,
        start_date,
        end_date,
    )
    params = _store_aware_params(tenant_id, store_id, start_date, end_date)
    service_data, shipping_data = await asyncio.gather(
        asyncio.to_thread(stats.service_completion_stats, params),
        asyncio.to_thread(stats.shipping_stats, params),
    )
    total_service = _num(service_data.get("totalServiceOrders"), 0)
    completed_service = _num(service_data.get("completedOrders"), 0)
    service_rate = (completed_service / total_service * 100) if total_service > 0 else 0
    avg_shipping = _num(shipping_data.get("avgShippingHours"), 0)
    return {
        "tenant_id": tenant_id,
        "dimension": "efficiency",
        "period": f"{start_date} ~ {end_date}",
        "indicators": {
            "service_completion_rate": {
                "value": round(service_rate, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"total_service": total_service, "completed": completed_service},
            },
            "avg_shipping_hours": {
                "value": round(avg_shipping, 2),
                "unit": "小时",
                "direction": "lower_is_better",
                "raw_data": {"avg_shipping_hours": avg_shipping},
            },
        },
    }


async def drill_down_indicator(
    tenant_id: str,
    store_id: str,
    indicator_code: str,
    start_date: str,
    end_date: str,
    page: int = 1,
    page_size: int = 20,
    auth_token: str | None = None,
) -> dict:
    _ = auth_token
    logger.info(
        "Tool called: drill_down_indicator tenant=%s store=%s indicator=%s page=%s",
        tenant_id,
        store_id,
        indicator_code,
        page,
    )
    params: dict = {
        "storeId": effective_store_id_for_biz(tenant_id, store_id),
        "startDate": start_date,
        "endDate": end_date,
        "pageNo": page,
        "pageSize": page_size,
    }
    drill_map = {
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
    if indicator_code not in drill_map:
        return {"indicator_code": indicator_code, "total": 0, "items": [], "summary": "该指标暂不支持钻取"}
    endpoint, extra_params = drill_map[indicator_code]
    params.update(extra_params)
    data = await asyncio.to_thread(_drill_fetch_data, endpoint, params)
    raw_items = data.get("list", data.get("items", []))
    allowed = DRILL_ITEM_FIELDS.get(indicator_code)
    items = [filter_drill_row_by_allowed_fields(it, allowed) for it in raw_items] if allowed else raw_items
    field_labels = {k: DRILL_FIELD_LABELS.get(k, k) for k in (allowed or [])}
    return {
        "indicator_code": indicator_code,
        "total": data.get("total", 0),
        "items": items,
        "field_labels": field_labels,
        "summary": data.get("summary", f"{indicator_code} 钻取数据"),
    }


_METRIC_GET_HANDLERS: tuple[tuple[str, Callable[[dict], dict]], ...] = (
    ("client-record/statistics", client_sales_examine.client_record_statistics),
    ("sales-contract/statistics", client_sales_examine.sales_contract_statistics),
    ("examine-initiate/follow-stats", client_sales_examine.examine_follow_stats),
    ("examine-initiate/turnaround-stats", client_sales_examine.examine_turnaround_stats),
    ("service-order/completion-stats", stats.service_completion_stats),
    ("store-order/shipping-stats", stats.shipping_stats),
    ("account-coupon/statistics", stats.coupon_statistics),
    ("manage-data/exposure-stats", stats.exposure_stats),
    ("store-order/conversion-stats", stats.conversion_stats),
    ("seckill-apply/conversion-stats", stats.seckill_conversion_stats),
    ("store-refund-order/statistics", stats.refund_statistics),
    ("store-order-evaluate/statistics", stats.evaluate_statistics),
    ("store-order/repurchase-stats", stats.repurchase_stats),
)


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    """供 dispatch：与 biz.get 统计类 path 对齐。"""
    if method.upper() != "GET":
        return None
    for p, fn in _METRIC_GET_HANDLERS:
        if path == p:
            return fn(q)
    _ = body
    return None


def register(server: FastMCP) -> None:
    """与 biz/metrics.register 相同。"""
    for fn in (
        get_crm_indicators,
        get_marketing_indicators,
        get_retention_indicators,
        get_efficiency_indicators,
        drill_down_indicator,
    ):
        server.add_tool(fn)
