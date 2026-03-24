"""其他 MCP 用到的统计接口 — 无表时返回模拟数据。"""

from __future__ import annotations

import json
import uuid
from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor
from src.wlwq.routes._random_control import random_enabled, random_float, random_int

router = APIRouter(tags=["mock-stats"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


def _mock(**kwargs):
    return _ok(kwargs)


def _page_ok(rows: list, total: int = 0, page: int = 1, page_size: int = 20):
    """分页列表标准响应。"""
    return _ok({"total": total or len(rows), "list": rows})


def _gen_id(prefix: str = "d", length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


def _mock_detail_list(detail_type: str, count: int = 15) -> dict:
    """根据类型生成模拟明细列表。"""
    import random as _r
    from datetime import datetime, timedelta

    rows = []
    base_time = datetime.now() - timedelta(days=30)
    for i in range(count):
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
        elif detail_type == "follow":
            rows.append(
                {
                    "examine_initiate_id": _gen_id("ei"),
                    "content": _r.choice(["电话跟进", "客户拜访", "方案发送", "需求确认"]),
                    "create_time": t,
                    "finish_time": (base_time + timedelta(hours=_r.randint(1, 48))).strftime("%Y-%m-%d %H:%M:%S"),
                    "user_name": _r.choice(["张三", "李四", "王五", "赵六"]),
                }
            )
    return _page_ok(rows, total=count * 3)


def _store_filter(store_id: str | None, alias: str = "") -> tuple[str, list]:
    """返回 (SQL片段, 参数列表)。store_id 为空/None 时不过滤（全企业）。"""
    col = f"{alias}.store_id" if alias else "store_id"
    if store_id:
        return f" AND {col} = $1", [store_id]
    return "", []


@router.get("/service-order/completion-stats")
async def service_completion(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("service")
    if random_enabled(useRandom):
        total = random_int("WLWQ_SERVICE_TOTAL_RANDOM_MIN", "WLWQ_SERVICE_TOTAL_RANDOM_MAX", 80, 160)
        completed = random_int("WLWQ_SERVICE_COMPLETED_RANDOM_MIN", "WLWQ_SERVICE_COMPLETED_RANDOM_MAX", 45, 95)
        completed = min(completed, total)
        return _ok({"totalServiceOrders": total, "completedOrders": completed})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total, SUM(CASE WHEN order_status=8 THEN 1 ELSE 0 END) AS completed "
                f"FROM service_order WHERE 1=1{sf}",
                sp,
            )
            row = await cur.fetchone()
            total = (row or {}).get("total", 0) or 1
            completed = (row or {}).get("completed", 0)
        return _ok({"totalServiceOrders": total, "completedOrders": completed})
    except Exception:
        return _ok({"totalServiceOrders": 100, "completedOrders": 85})


@router.get("/store-order/shipping-stats")
async def shipping_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("shipping")
    if random_enabled(useRandom):
        return _ok(
            {
                "avgShippingHours": random_float(
                    "WLWQ_AVG_SHIPPING_RANDOM_MIN", "WLWQ_AVG_SHIPPING_RANDOM_MAX", 22.0, 32.0, 2
                )
            }
        )
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT AVG(shipping_hours) AS avg_hours FROM store_order WHERE shipping_hours IS NOT NULL{sf}",
                sp,
            )
            row = await cur.fetchone()
            avg_h = float((row or {}).get("avg_hours", 0) or 12.0)
        return _ok({"avgShippingHours": avg_h})
    except Exception:
        return _ok({"avgShippingHours": 12.0})


@router.get("/account-coupon/statistics")
async def coupon_statistics(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    filterType: str | None = Query(None),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if filterType == "unused":
        return _mock_detail_list("coupon")
    if random_enabled(useRandom):
        total_issued = random_int("WLWQ_COUPON_ISSUED_RANDOM_MIN", "WLWQ_COUPON_ISSUED_RANDOM_MAX", 4200, 6200)
        total_used = random_int("WLWQ_COUPON_USED_RANDOM_MIN", "WLWQ_COUPON_USED_RANDOM_MAX", 600, 1500)
        total_used = min(total_used, total_issued)
        return _ok({"totalIssued": total_issued, "totalUsed": total_used})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total_issued, "
                "SUM(CASE WHEN use_status=1 THEN 1 ELSE 0 END) AS total_used "
                f"FROM account_coupon WHERE 1=1{sf}",
                sp,
            )
            row = await cur.fetchone()
            return _ok(
                {"totalIssued": (row or {}).get("total_issued", 0), "totalUsed": (row or {}).get("total_used", 0)}
            )
    except Exception:
        return _ok({"totalIssued": 5000, "totalUsed": 1850})


@router.get("/manage-data/exposure-stats")
async def exposure_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("exposure")
    if random_enabled(useRandom):
        return _ok(
            {"browseUsers": random_int("WLWQ_BROWSE_USERS_RANDOM_MIN", "WLWQ_BROWSE_USERS_RANDOM_MAX", 12000, 18000)}
        )
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS bu FROM manage_data WHERE date_type=1{sf}", sp)
            row = await cur.fetchone()
            return _ok({"browseUsers": (row or {}).get("bu", 0)})
    except Exception:
        return _ok({"browseUsers": 12600})


@router.get("/store-order/analytics")
async def order_analytics(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    groupBy: str | None = Query(None, alias="groupBy"),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    """订单分析数据。"""
    if random_enabled(useRandom):
        return _ok(
            {
                "totalGmv": random_float(
                    "WLWQ_TOTAL_GMV_RANDOM_MIN",
                    "WLWQ_TOTAL_GMV_RANDOM_MAX",
                    280000.0,
                    650000.0,
                ),
                "avgOrderAmount": random_float(
                    "WLWQ_AVG_ORDER_RANDOM_MIN",
                    "WLWQ_AVG_ORDER_RANDOM_MAX",
                    120.0,
                    380.0,
                ),
                "orderCount": random_int(
                    "WLWQ_ORDER_COUNT_RANDOM_MIN",
                    "WLWQ_ORDER_COUNT_RANDOM_MAX",
                    1800,
                    3200,
                ),
            }
        )
    try:
        sf, sp = _store_filter(storeId)
        date_cond = ""
        dp = []
        if startDate:
            date_cond += " AND pay_time>=%s"
            dp.append(startDate)
        if endDate:
            date_cond += " AND pay_time<=%s"
            dp.append(endDate)
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS order_count, COALESCE(SUM(pay_price), 0) AS total_gmv "
                f"FROM store_order WHERE order_status>=3{sf}{date_cond}",
                sp + dp,
            )
            row = await cur.fetchone()
            count = (row or {}).get("order_count", 0) or 0
            gmv = float((row or {}).get("total_gmv", 0) or 0)
            avg = round(gmv / count, 2) if count else 0.0
        return _ok({"totalGmv": gmv, "avgOrderAmount": avg, "orderCount": count})
    except Exception:
        return _ok({"totalGmv": 425000.0, "avgOrderAmount": 265.0, "orderCount": 2400})


@router.get("/store-order/conversion-stats")
async def conversion_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("order")
    if random_enabled(useRandom):
        total_orders = random_int("WLWQ_TOTAL_ORDERS_RANDOM_MIN", "WLWQ_TOTAL_ORDERS_RANDOM_MAX", 1800, 2800)
        completed_orders = random_int("WLWQ_COMPLETED_ORDERS_RANDOM_MIN", "WLWQ_COMPLETED_ORDERS_RANDOM_MAX", 900, 1650)
        completed_orders = min(completed_orders, total_orders)
        order_users = random_int("WLWQ_ORDER_USERS_RANDOM_MIN", "WLWQ_ORDER_USERS_RANDOM_MAX", 300, 650)
        new_customers = random_int("WLWQ_NEW_CUSTOMERS_RANDOM_MIN", "WLWQ_NEW_CUSTOMERS_RANDOM_MAX", 80, 200)
        return _ok(
            {
                "orderUsers": order_users,
                "totalOrders": total_orders,
                "completedOrders": completed_orders,
                "newCustomers": min(new_customers, order_users),
            }
        )
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total_orders, "
                "SUM(CASE WHEN order_status>=3 THEN 1 ELSE 0 END) AS completed, "
                "COUNT(DISTINCT account_id) AS order_users "
                f"FROM store_order WHERE 1=1{sf}",
                sp,
            )
            row = await cur.fetchone()
            total = (row or {}).get("total_orders", 0)
            completed = (row or {}).get("completed", 0)
            order_users = (row or {}).get("order_users", 0)
            return _ok(
                {
                    "orderUsers": order_users,
                    "totalOrders": total,
                    "completedOrders": completed,
                    "newCustomers": max(1, int(order_users * 0.15)),
                }
            )
    except Exception:
        return _ok({"orderUsers": 820, "totalOrders": 2280, "completedOrders": 2050, "newCustomers": 320})


@router.get("/seckill-apply/conversion-stats")
async def seckill_conversion_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("seckill")
    if random_enabled(useRandom):
        total = random_int("WLWQ_SECKILL_TOTAL_RANDOM_MIN", "WLWQ_SECKILL_TOTAL_RANDOM_MAX", 450, 800)
        sold = random_int("WLWQ_SECKILL_SOLD_RANDOM_MIN", "WLWQ_SECKILL_SOLD_RANDOM_MAX", 80, 220)
        sold = min(sold, total)
        return _ok({"totalSeckillGoods": total, "soldGoods": sold})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COALESCE(SUM(goods_num), 0) AS total, "
                "COALESCE(SUM(goods_num - surplus_goods_num), 0) AS sold "
                f"FROM seckill_goods_time WHERE del_status = 0{sf}",
                sp,
            )
            row = await cur.fetchone()
            return _ok(
                {"totalSeckillGoods": int((row or {}).get("total", 0)), "soldGoods": int((row or {}).get("sold", 0))}
            )
    except Exception:
        return _ok({"totalSeckillGoods": 500, "soldGoods": 185})


@router.get("/store-refund-order/statistics")
async def refund_statistics(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("refund")
    if random_enabled(useRandom):
        total_completed = random_int(
            "WLWQ_REFUND_TOTAL_COMPLETED_RANDOM_MIN", "WLWQ_REFUND_TOTAL_COMPLETED_RANDOM_MAX", 1500, 2400
        )
        refund_orders = random_int("WLWQ_REFUND_ORDERS_RANDOM_MIN", "WLWQ_REFUND_ORDERS_RANDOM_MAX", 120, 260)
        refund_orders = min(refund_orders, total_completed)
        return _ok({"totalCompletedOrders": total_completed, "refundOrders": refund_orders})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS refund_orders FROM store_refund_order WHERE 1=1{sf}", sp)
            row = await cur.fetchone()
            refund = (row or {}).get("refund_orders", 0)
            await cur.execute(f"SELECT COUNT(*) AS total FROM store_order WHERE order_status>=3{sf}", sp)
            row2 = await cur.fetchone()
            total_completed = (row2 or {}).get("total", 0)
            return _ok({"totalCompletedOrders": total_completed, "refundOrders": refund})
    except Exception:
        return _ok({"totalCompletedOrders": 2050, "refundOrders": 82})


@router.get("/store-order-evaluate/statistics")
async def evaluate_statistics(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    filterType: str | None = Query(None),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if filterType == "negative":
        return _mock_detail_list("review")
    if random_enabled(useRandom):
        total_reviews = random_int("WLWQ_TOTAL_REVIEWS_RANDOM_MIN", "WLWQ_TOTAL_REVIEWS_RANDOM_MAX", 900, 1500)
        positive_reviews = random_int("WLWQ_POSITIVE_REVIEWS_RANDOM_MIN", "WLWQ_POSITIVE_REVIEWS_RANDOM_MAX", 520, 960)
        positive_reviews = min(positive_reviews, total_reviews)
        return _ok({"totalReviews": total_reviews, "positiveReviews": positive_reviews})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total_reviews, SUM(CASE WHEN star>=4 THEN 1 ELSE 0 END) AS positive "
                f"FROM store_order_evaluate WHERE 1=1{sf}",
                sp,
            )
            row = await cur.fetchone()
            return _ok(
                {"totalReviews": (row or {}).get("total_reviews", 0), "positiveReviews": (row or {}).get("positive", 0)}
            )
    except Exception:
        return _ok({"totalReviews": 1680, "positiveReviews": 1462})


@router.get("/store-order/repurchase-stats")
async def repurchase_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    detail: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(20),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if detail:
        return _mock_detail_list("ltv")
    if random_enabled(useRandom):
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
        return _ok(
            {
                "totalBuyers": total_buyers,
                "repeatBuyers": repeat_buyers,
                "activeCustomers": active_customers,
                "churnedCustomers": churned_customers,
                "avgLifetimeValue": avg_ltv,
            }
        )
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(DISTINCT account_id) AS total_buyers, "
                "SUM(CASE WHEN order_count>1 THEN 1 ELSE 0 END) AS repeat_buyers "
                f"FROM (SELECT account_id, COUNT(*) AS order_count FROM store_order WHERE 1=1{sf} GROUP BY account_id) t",
                sp,
            )
            row = await cur.fetchone()
            total = (row or {}).get("total_buyers", 0)
            repeat_ = (row or {}).get("repeat_buyers", 0)
            return _ok(
                {
                    "totalBuyers": total,
                    "repeatBuyers": repeat_,
                    "activeCustomers": total,
                    "churnedCustomers": max(0, int(total * 0.17)),
                    "avgLifetimeValue": 1560,
                }
            )
    except Exception:
        return _ok(
            {
                "totalBuyers": 2800,
                "repeatBuyers": 1120,
                "activeCustomers": 2200,
                "churnedCustomers": 380,
                "avgLifetimeValue": 1560,
            }
        )
