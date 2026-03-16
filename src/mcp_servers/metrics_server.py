"""
metrics-server: 运营指标采集与计算
传输: stdio
"""

from __future__ import annotations

import asyncio
import logging

from mcp.server import FastMCP

from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient
from src.core.calculator import DRILL_ITEM_FIELDS, DRILL_FIELD_LABELS

logger = logging.getLogger(__name__)

server = FastMCP("metrics-server")
router = TenantRouter()
biz = BizAPIClient(router)


@server.tool()
async def get_crm_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    采集CRM共享维度指标。
    返回: lead_conversion_rate, response_time_avg, follow_up_count
    """
    params = {"storeId": store_id, "startDate": start_date, "endDate": end_date}

    clients_data, contracts_data, follows_data = await asyncio.gather(
        biz.get(tenant_id, "/client-record/statistics", params),
        biz.get(tenant_id, "/sales-contract/statistics", params),
        biz.get(tenant_id, "/examine-initiate/follow-stats", params),
    )

    total_clients = clients_data.get("total", 0)
    signed_clients = contracts_data.get("signedCount", 0)
    lead_conversion_rate = (signed_clients / total_clients * 100) if total_clients > 0 else 0

    follow_total = follows_data.get("followTotal", 0)
    response_time_avg = follows_data.get("avgResponseHours", 0)

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


@server.tool()
async def get_marketing_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    采集营销效果维度指标。
    返回: coupon_redemption_rate, browse_to_order_rate, order_conversion_rate,
          customer_acquisition_cost
    """
    params = {"storeId": store_id, "startDate": start_date, "endDate": end_date}

    coupon_data, order_data, activity_data, exposure_data = await asyncio.gather(
        biz.get(tenant_id, "/account-coupon/statistics", params),
        biz.get(tenant_id, "/store-order/conversion-stats", params),
        biz.get(tenant_id, "/store-activities/roi", params),
        biz.get(tenant_id, "/manage-data/exposure-stats", params),
    )

    total_coupons = coupon_data.get("totalIssued", 0)
    used_coupons = coupon_data.get("totalUsed", 0)
    coupon_rate = (used_coupons / total_coupons * 100) if total_coupons > 0 else 0

    browse_users = exposure_data.get("browseUsers", 0)
    order_users = order_data.get("orderUsers", 0)
    browse_to_order = (order_users / browse_users * 100) if browse_users > 0 else 0

    total_orders = order_data.get("totalOrders", 0)
    completed_orders = order_data.get("completedOrders", 0)
    order_conversion = (completed_orders / total_orders * 100) if total_orders > 0 else 0

    marketing_spend = activity_data.get("totalSpend", 0)
    new_customers = order_data.get("newCustomers", 1)
    cac = marketing_spend / new_customers if new_customers > 0 else 0

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
            "customer_acquisition_cost": {
                "value": round(cac, 2),
                "unit": "元",
                "direction": "lower_is_better",
                "raw_data": {"marketing_spend": marketing_spend, "new_customers": new_customers},
            },
        },
    }


@server.tool()
async def get_retention_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    采集客户留存维度指标。
    返回: repurchase_rate, refund_rate, churn_rate, positive_review_rate,
          avg_customer_lifetime_value
    """
    params = {"storeId": store_id, "startDate": start_date, "endDate": end_date}

    repurchase_data, refund_data, evaluate_data = await asyncio.gather(
        biz.get(tenant_id, "/store-order/repurchase-stats", params),
        biz.get(tenant_id, "/store-refund-order/statistics", params),
        biz.get(tenant_id, "/store-order-evaluate/statistics", params),
    )

    total_buyers = repurchase_data.get("totalBuyers", 0)
    repeat_buyers = repurchase_data.get("repeatBuyers", 0)
    repurchase_rate = (repeat_buyers / total_buyers * 100) if total_buyers > 0 else 0

    total_completed = refund_data.get("totalCompletedOrders", 0)
    refund_orders = refund_data.get("refundOrders", 0)
    refund_rate = (refund_orders / total_completed * 100) if total_completed > 0 else 0

    active_customers = repurchase_data.get("activeCustomers", 0)
    churned = repurchase_data.get("churnedCustomers", 0)
    churn_rate = (churned / active_customers * 100) if active_customers > 0 else 0

    total_reviews = evaluate_data.get("totalReviews", 0)
    positive_reviews = evaluate_data.get("positiveReviews", 0)
    positive_rate = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0

    avg_ltv = repurchase_data.get("avgLifetimeValue", 0)

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


@server.tool()
async def get_efficiency_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    采集运营效率维度指标。
    返回: service_completion_rate, avg_shipping_hours, task_on_time_rate
    """
    params = {"storeId": store_id, "startDate": start_date, "endDate": end_date}

    approval_data, service_data, shipping_data = await asyncio.gather(
        biz.get(tenant_id, "/examine-initiate/turnaround-stats", params),
        biz.get(tenant_id, "/service-order/completion-stats", params),
        biz.get(tenant_id, "/store-order/shipping-stats", params),
    )

    task_on_time = approval_data.get("onTimeRate", 0)

    total_service = service_data.get("totalServiceOrders", 0)
    completed_service = service_data.get("completedOrders", 0)
    service_rate = (completed_service / total_service * 100) if total_service > 0 else 0

    avg_shipping = shipping_data.get("avgShippingHours", 0)

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
            "task_on_time_rate": {
                "value": round(task_on_time, 2),
                "unit": "%",
                "direction": "higher_is_better",
                "raw_data": {"on_time_rate": task_on_time},
            },
        },
    }


@server.tool()
async def get_inventory_indicators(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    采集库存维度指标。
    返回: stock_turnover_days, stockout_rate, overstock_rate
    """
    params = {"storeId": store_id, "startDate": start_date, "endDate": end_date}

    stock_data, goods_data = await asyncio.gather(
        biz.get(tenant_id, "/stock/statistics", params),
        biz.get(tenant_id, "/store-goods/statistics", params),
    )

    total_sku = goods_data.get("totalSku", 0)
    stockout_sku = stock_data.get("stockoutSku", 0)
    overstock_sku = stock_data.get("overstockSku", 0)
    stockout_rate = (stockout_sku / total_sku * 100) if total_sku > 0 else 0
    overstock_rate = (overstock_sku / total_sku * 100) if total_sku > 0 else 0
    turnover_days = stock_data.get("avgTurnoverDays", 0)

    return {
        "tenant_id": tenant_id,
        "dimension": "inventory",
        "period": f"{start_date} ~ {end_date}",
        "indicators": {
            "stock_turnover_days": {
                "value": round(turnover_days, 2),
                "unit": "天",
                "direction": "lower_is_better",
                "raw_data": {"avg_turnover_days": turnover_days},
            },
            "stockout_rate": {
                "value": round(stockout_rate, 2),
                "unit": "%",
                "direction": "lower_is_better",
                "raw_data": {"stockout_sku": stockout_sku, "total_sku": total_sku},
            },
            "overstock_rate": {
                "value": round(overstock_rate, 2),
                "unit": "%",
                "direction": "lower_is_better",
                "raw_data": {"overstock_sku": overstock_sku, "total_sku": total_sku},
            },
        },
    }


@server.tool()
async def drill_down_indicator(
    tenant_id: str,
    store_id: str,
    indicator_code: str,
    start_date: str,
    end_date: str,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    指标数据钻取 — 返回指标对应的明细数据列表，支持分页。
    支持全部指标 (indicator_code 见 INDICATOR_META)。
    """
    params = {
        "storeId": store_id,
        "startDate": start_date,
        "endDate": end_date,
        "page": page,
        "pageSize": page_size,
    }

    drill_map = {
        # CRM维度
        "lead_conversion_rate": ("/client-record/list", {"filterType": "low_conversion"}),
        "response_time_avg": ("/examine-initiate/follow-stats", {"filterType": "slow_response"}),
        "follow_up_count": ("/examine-initiate/follow-stats", {"detail": "true"}),
        # 营销维度
        "coupon_redemption_rate": ("/account-coupon/statistics", {"filterType": "unused"}),
        "browse_to_order_rate": ("/manage-data/exposure-stats", {"detail": "true"}),
        "order_conversion_rate": ("/store-order/conversion-stats", {"detail": "true"}),
        "customer_acquisition_cost": ("/store-activities/roi", {"filterType": "high_cost"}),
        # 客户留存
        "repurchase_rate": ("/client-record/list", {"filterType": "no_repurchase"}),
        "refund_rate": ("/store-refund-order/statistics", {"detail": "true"}),
        "churn_rate": ("/client-record/list", {"filterType": "churn_risk"}),
        "positive_review_rate": ("/store-order-evaluate/statistics", {"filterType": "negative"}),
        "avg_customer_lifetime_value": ("/store-order/repurchase-stats", {"detail": "true"}),
        # 运营效率
        "service_completion_rate": ("/service-order/completion-stats", {"detail": "true"}),
        "avg_shipping_hours": ("/store-order/shipping-stats", {"detail": "true"}),
        "task_on_time_rate": ("/examine-initiate/turnaround-stats", {"filterType": "overdue"}),
        # 库存
        "stock_turnover_days": ("/stock/statistics", {"detail": "true", "filterType": "slow_turnover"}),
        "stockout_rate": ("/stock/statistics", {"detail": "true", "filterType": "stockout"}),
        "overstock_rate": ("/stock/statistics", {"detail": "true", "filterType": "overstock"}),
    }

    if indicator_code not in drill_map:
        return {"indicator_code": indicator_code, "total": 0, "items": [], "summary": "该指标暂不支持钻取"}

    endpoint, extra_params = drill_map[indicator_code]
    params.update(extra_params)

    data = await biz.get(tenant_id, endpoint, params)
    raw_items = data.get("list", data.get("items", []))
    allowed = DRILL_ITEM_FIELDS.get(indicator_code)
    items = (
        [{k: v for k, v in (it if isinstance(it, dict) else {}).items() if k in allowed} for it in raw_items]
        if allowed
        else raw_items
    )
    field_labels = {k: DRILL_FIELD_LABELS.get(k, k) for k in (allowed or [])}
    return {
        "indicator_code": indicator_code,
        "total": data.get("total", 0),
        "items": items,
        "field_labels": field_labels,
        "summary": data.get("summary", f"{indicator_code} 钻取数据"),
    }


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
