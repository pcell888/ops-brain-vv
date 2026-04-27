"""统计类 GET — mock 数据生成。"""

from __future__ import annotations

import random as _r
import uuid
from datetime import datetime, timedelta

from src.biz.mock.handlers.random_util import (
    query_param_bool,
    random_enabled,
    random_float,
    random_int,
    use_random_from_params,
)


def _gen_id(prefix: str = "d", length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


def _mock_detail_list(detail_type: str, count: int = 15) -> dict:
    rows = []
    base_time = datetime.now() - timedelta(days=30)
    for _ in range(count):
        t = (base_time + timedelta(days=_r.randint(0, 30), hours=_r.randint(0, 23))).strftime("%Y-%m-%d %H:%M:%S")
        if detail_type == "order":
            rows.append(
                {
                    "account_id": f"acc_{_r.randint(1000, 9999)}",
                    "order_sn": f"SN{_r.randint(100000, 999999)}",
                    "pay_time": t,
                    "pay_price": round(_r.uniform(20, 500), 2),
                    "order_status": _r.choice([3, 4, 5, 6]),
                }
            )
        elif detail_type == "shipping":
            rows.append(
                {
                    "store_order_id": _gen_id("so"),
                    "order_sn": f"SN{_r.randint(100000, 999999)}",
                    "pay_time": t,
                    "delivery_time": (base_time + timedelta(days=_r.randint(1, 5))).strftime("%Y-%m-%d %H:%M:%S"),
                    "shipping_hours": round(_r.uniform(2, 72), 1),
                }
            )
        elif detail_type == "seckill":
            rows.append(
                {
                    "seckill_apply_id": _gen_id("sk"),
                    "goods_name": f"秒杀商品{_r.randint(1, 100)}",
                    "goods_num": _r.randint(50, 500),
                    "surplus_goods_num": _r.randint(0, 100),
                    "start_time": t,
                    "end_time": (base_time + timedelta(days=_r.randint(1, 7))).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        elif detail_type == "refund":
            rows.append(
                {
                    "store_refund_order_id": _gen_id("rf"),
                    "store_order_id": _gen_id("so"),
                    "order_sn": f"SN{_r.randint(100000, 999999)}",
                    "refund_price": round(_r.uniform(10, 300), 2),
                    "refund_cause": _r.choice(["质量问题", "不想要了", "与描述不符", "其他"]),
                    "refund_apply_time": t,
                    "refund_success_time": (base_time + timedelta(days=_r.randint(1, 3))).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        elif detail_type == "review":
            rows.append(
                {
                    "store_order_evaluate_id": _gen_id("ev"),
                    "store_order_id": _gen_id("so"),
                    "star": _r.randint(1, 5),
                    "level": _r.choice([1, 2, 3]),
                    "content": _r.choice(["好评", "一般", "不错", "差", "很好"]),
                    "create_time": t,
                }
            )
        elif detail_type == "service":
            rows.append(
                {
                    "service_order_id": _gen_id("sv"),
                    "order_sn": f"SV{_r.randint(100000, 999999)}",
                    "order_status": _r.choice([1, 2, 3, 8]),
                    "create_time": t,
                    "finish_time": (base_time + timedelta(days=_r.randint(1, 10))).strftime("%Y-%m-%d %H:%M:%S")
                    if _r.random() > 0.3
                    else None,
                }
            )
        elif detail_type == "coupon":
            rows.append(
                {
                    "account_coupon_id": _gen_id("cp"),
                    "coupon_name": f"满{_r.choice([50, 100, 200])}减{_r.choice([5, 10, 20, 30])}",
                    "phone": f"138****{_r.randint(1000, 9999)}",
                    "use_status": _r.choice([0, 1]),
                    "start_time": t,
                    "end_time": (base_time + timedelta(days=_r.randint(7, 30))).strftime("%Y-%m-%d %H:%M:%S"),
                    "create_time": t,
                }
            )
        elif detail_type == "exposure":
            rows.append(
                {
                    "account_id": f"acc_{_r.randint(1000, 9999)}",
                    "browse_time": t,
                    "order_count": _r.randint(0, 5),
                    "first_order_time": t if _r.random() > 0.5 else None,
                }
            )
        elif detail_type == "ltv":
            rows.append(
                {
                    "account_id": f"acc_{_r.randint(1000, 9999)}",
                    "order_count": _r.randint(1, 50),
                    "total_amount": round(_r.uniform(100, 10000), 2),
                    "last_order_time": t,
                }
            )
    return {"total": count * 3, "list": rows}


def service_completion_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("service")
    if random_enabled(use_random_from_params(params)):
        total = random_int("WLWQ_SERVICE_TOTAL_RANDOM_MIN", "WLWQ_SERVICE_TOTAL_RANDOM_MAX", 80, 160)
        completed = random_int("WLWQ_SERVICE_COMPLETED_RANDOM_MIN", "WLWQ_SERVICE_COMPLETED_RANDOM_MAX", 45, 95)
        completed = min(completed, total)
        return {"totalServiceOrders": total, "completedOrders": completed}
    return {"totalServiceOrders": 100, "completedOrders": 85}


def shipping_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("shipping")
    if random_enabled(use_random_from_params(params)):
        return {
            "avgShippingHours": random_float(
                "WLWQ_AVG_SHIPPING_RANDOM_MIN", "WLWQ_AVG_SHIPPING_RANDOM_MAX", 22.0, 32.0, 2
            )
        }
    return {"avgShippingHours": 12.0}


def coupon_statistics(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if params.get("filterType") == "unused":
        return _mock_detail_list("coupon")
    if random_enabled(use_random_from_params(params)):
        total_issued = random_int("WLWQ_COUPON_ISSUED_RANDOM_MIN", "WLWQ_COUPON_ISSUED_RANDOM_MAX", 4200, 6200)
        total_used = random_int("WLWQ_COUPON_USED_RANDOM_MIN", "WLWQ_COUPON_USED_RANDOM_MAX", 600, 1500)
        total_used = min(total_used, total_issued)
        return {"totalIssued": total_issued, "totalUsed": total_used}
    return {"totalIssued": 5000, "totalUsed": 1850}


def exposure_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("exposure")
    if random_enabled(use_random_from_params(params)):
        return {
            "browseUsers": random_int("WLWQ_BROWSE_USERS_RANDOM_MIN", "WLWQ_BROWSE_USERS_RANDOM_MAX", 12000, 18000)
        }
    return {"browseUsers": 12600}


def store_order_analytics(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("groupBy"))
    if random_enabled(use_random_from_params(params)):
        return {
            "totalGmv": random_float("WLWQ_TOTAL_GMV_RANDOM_MIN", "WLWQ_TOTAL_GMV_RANDOM_MAX", 280000.0, 650000.0),
            "avgOrderAmount": random_float(
                "WLWQ_AVG_ORDER_RANDOM_MIN", "WLWQ_AVG_ORDER_RANDOM_MAX", 120.0, 380.0
            ),
            "orderCount": random_int("WLWQ_ORDER_COUNT_RANDOM_MIN", "WLWQ_ORDER_COUNT_RANDOM_MAX", 1800, 3200),
        }
    return {"totalGmv": 425000.0, "avgOrderAmount": 265.0, "orderCount": 2400}


def conversion_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("order")
    if random_enabled(use_random_from_params(params)):
        total_orders = random_int("WLWQ_TOTAL_ORDERS_RANDOM_MIN", "WLWQ_TOTAL_ORDERS_RANDOM_MAX", 1800, 2800)
        completed_orders = random_int("WLWQ_COMPLETED_ORDERS_RANDOM_MIN", "WLWQ_COMPLETED_ORDERS_RANDOM_MAX", 900, 1650)
        completed_orders = min(completed_orders, total_orders)
        order_users = random_int("WLWQ_ORDER_USERS_RANDOM_MIN", "WLWQ_ORDER_USERS_RANDOM_MAX", 300, 650)
        new_customers = random_int("WLWQ_NEW_CUSTOMERS_RANDOM_MIN", "WLWQ_NEW_CUSTOMERS_RANDOM_MAX", 80, 200)
        return {
            "orderUsers": order_users,
            "totalOrders": total_orders,
            "completedOrders": completed_orders,
            "newCustomers": min(new_customers, order_users),
        }
    return {"orderUsers": 820, "totalOrders": 2280, "completedOrders": 2050, "newCustomers": 320}


def seckill_conversion_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("seckill")
    if random_enabled(use_random_from_params(params)):
        total = random_int("WLWQ_SECKILL_TOTAL_RANDOM_MIN", "WLWQ_SECKILL_TOTAL_RANDOM_MAX", 450, 800)
        sold = random_int("WLWQ_SECKILL_SOLD_RANDOM_MIN", "WLWQ_SECKILL_SOLD_RANDOM_MAX", 80, 220)
        sold = min(sold, total)
        return {"totalSeckillGoods": total, "soldGoods": sold}
    return {"totalSeckillGoods": 500, "soldGoods": 185}


def refund_statistics(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("refund")
    if random_enabled(use_random_from_params(params)):
        total_completed = random_int(
            "WLWQ_REFUND_TOTAL_COMPLETED_RANDOM_MIN", "WLWQ_REFUND_TOTAL_COMPLETED_RANDOM_MAX", 1500, 2400
        )
        refund_orders = random_int("WLWQ_REFUND_ORDERS_RANDOM_MIN", "WLWQ_REFUND_ORDERS_RANDOM_MAX", 120, 260)
        refund_orders = min(refund_orders, total_completed)
        return {"totalCompletedOrders": total_completed, "refundOrders": refund_orders}
    return {"totalCompletedOrders": 2050, "refundOrders": 82}


def evaluate_statistics(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if params.get("filterType") == "negative":
        return _mock_detail_list("review")
    if random_enabled(use_random_from_params(params)):
        total_reviews = random_int("WLWQ_TOTAL_REVIEWS_RANDOM_MIN", "WLWQ_TOTAL_REVIEWS_RANDOM_MAX", 900, 1500)
        positive_reviews = random_int("WLWQ_POSITIVE_REVIEWS_RANDOM_MIN", "WLWQ_POSITIVE_REVIEWS_RANDOM_MAX", 520, 960)
        positive_reviews = min(positive_reviews, total_reviews)
        return {"totalReviews": total_reviews, "positiveReviews": positive_reviews}
    return {"totalReviews": 1680, "positiveReviews": 1462}


def repurchase_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), params.get("page"), params.get("pageSize"))
    if query_param_bool(params, "detail"):
        return _mock_detail_list("ltv")
    if random_enabled(use_random_from_params(params)):
        total_buyers = random_int("WLWQ_TOTAL_BUYERS_RANDOM_MIN", "WLWQ_TOTAL_BUYERS_RANDOM_MAX", 2200, 3200)
        repeat_buyers = random_int("WLWQ_REPEAT_BUYERS_RANDOM_MIN", "WLWQ_REPEAT_BUYERS_RANDOM_MAX", 500, 950)
        repeat_buyers = min(repeat_buyers, total_buyers)
        active_customers = random_int(
            "WLWQ_ACTIVE_CUSTOMERS_RANDOM_MIN", "WLWQ_ACTIVE_CUSTOMERS_RANDOM_MAX", 1800, 2800
        )
        active_customers = min(active_customers, total_buyers)
        churned_customers = random_int(
            "WLWQ_CHURNED_CUSTOMERS_RANDOM_MIN", "WLWQ_CHURNED_CUSTOMERS_RANDOM_MAX", 420, 780
        )
        churned_customers = min(churned_customers, active_customers)
        avg_ltv = random_float("WLWQ_AVG_LTV_RANDOM_MIN", "WLWQ_AVG_LTV_RANDOM_MAX", 600.0, 980.0, 2)
        return {
            "totalBuyers": total_buyers,
            "repeatBuyers": repeat_buyers,
            "activeCustomers": active_customers,
            "churnedCustomers": churned_customers,
            "avgLifetimeValue": avg_ltv,
        }
    return {
        "totalBuyers": 2800,
        "repeatBuyers": 1120,
        "activeCustomers": 2200,
        "churnedCustomers": 380,
        "avgLifetimeValue": 1560,
    }