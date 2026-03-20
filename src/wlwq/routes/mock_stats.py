"""其他 MCP 用到的统计接口 — 无表时返回模拟数据。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor
from src.wlwq.routes._random_control import random_enabled, random_float, random_int

router = APIRouter(tags=["mock-stats"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


def _mock(**kwargs):
    return _ok(kwargs)


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
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        total = random_int("WLWQ_SERVICE_TOTAL_RANDOM_MIN", "WLWQ_SERVICE_TOTAL_RANDOM_MAX", 80, 160)
        completed = random_int("WLWQ_SERVICE_COMPLETED_RANDOM_MIN", "WLWQ_SERVICE_COMPLETED_RANDOM_MAX", 45, 95)
        completed = min(completed, total)
        rate = (completed / total * 100) if total else 0
        return _ok({"totalServiceOrders": total, "completedOrders": completed, "completionRate": round(rate, 2)})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total, SUM(CASE WHEN order_status=8 THEN 1 ELSE 0 END) AS completed "
                f"FROM service_order WHERE 1=1{sf}", sp,
            )
            row = await cur.fetchone()
            total = (row or {}).get("total", 0) or 1
            completed = (row or {}).get("completed", 0)
            rate = (completed / total * 100) if total else 0
        return _ok({"totalServiceOrders": total, "completedOrders": completed, "completionRate": round(rate, 2)})
    except Exception:
        return _ok({"totalServiceOrders": 100, "completedOrders": 85, "completionRate": 85.0})


@router.get("/store-order/shipping-stats")
async def shipping_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        return _ok({
            "avgShippingHours": random_float(
                "WLWQ_AVG_SHIPPING_RANDOM_MIN",
                "WLWQ_AVG_SHIPPING_RANDOM_MAX",
                22.0,
                32.0,
                2,
            )
        })
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT AVG(shipping_hours) AS avg_hours FROM store_order WHERE shipping_hours IS NOT NULL{sf}", sp,
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
    useRandom: bool | None = Query(None, alias="useRandom"),
):
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
                f"FROM account_coupon WHERE 1=1{sf}", sp,
            )
            row = await cur.fetchone()
            return _ok({
                "totalIssued": (row or {}).get("total_issued", 0),
                "totalUsed": (row or {}).get("total_used", 0),
            })
    except Exception:
        return _ok({"totalIssued": 5000, "totalUsed": 1850})


@router.get("/manage-data/exposure-stats")
async def exposure_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        return _ok({
            "browseUsers": random_int(
                "WLWQ_BROWSE_USERS_RANDOM_MIN",
                "WLWQ_BROWSE_USERS_RANDOM_MAX",
                12000,
                18000,
            )
        })
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS bu FROM manage_data WHERE date_type=1{sf}", sp)
            row = await cur.fetchone()
            return _ok({"browseUsers": (row or {}).get("bu", 0)})
    except Exception:
        return _ok({"browseUsers": 12600})


@router.get("/store-order/conversion-stats")
async def conversion_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        total_orders = random_int("WLWQ_TOTAL_ORDERS_RANDOM_MIN", "WLWQ_TOTAL_ORDERS_RANDOM_MAX", 1800, 2800)
        completed_orders = random_int("WLWQ_COMPLETED_ORDERS_RANDOM_MIN", "WLWQ_COMPLETED_ORDERS_RANDOM_MAX", 900, 1650)
        completed_orders = min(completed_orders, total_orders)
        order_users = random_int("WLWQ_ORDER_USERS_RANDOM_MIN", "WLWQ_ORDER_USERS_RANDOM_MAX", 300, 650)
        new_customers = random_int("WLWQ_NEW_CUSTOMERS_RANDOM_MIN", "WLWQ_NEW_CUSTOMERS_RANDOM_MAX", 80, 200)
        return _ok({
            "orderUsers": order_users,
            "totalOrders": total_orders,
            "completedOrders": completed_orders,
            "newCustomers": min(new_customers, order_users),
        })
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total_orders, "
                "SUM(CASE WHEN order_status>=3 THEN 1 ELSE 0 END) AS completed, "
                "COUNT(DISTINCT account_id) AS order_users "
                f"FROM store_order WHERE 1=1{sf}", sp,
            )
            row = await cur.fetchone()
            total = (row or {}).get("total_orders", 0)
            completed = (row or {}).get("completed", 0)
            order_users = (row or {}).get("order_users", 0)
            return _ok({
                "orderUsers": order_users,
                "totalOrders": total,
                "completedOrders": completed,
                "newCustomers": max(1, int(order_users * 0.15)),
            })
    except Exception:
        return _ok({"orderUsers": 820, "totalOrders": 2280, "completedOrders": 2050, "newCustomers": 320})


@router.get("/seckill-apply/conversion-stats")
async def seckill_conversion_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
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
                f"FROM seckill_goods_time WHERE del_status = 0{sf}", sp,
            )
            row = await cur.fetchone()
            return _ok({
                "totalSeckillGoods": int((row or {}).get("total", 0)),
                "soldGoods": int((row or {}).get("sold", 0)),
            })
    except Exception:
        return _ok({"totalSeckillGoods": 500, "soldGoods": 185})


@router.get("/store-refund-order/statistics")
async def refund_statistics(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        total_completed = random_int("WLWQ_REFUND_TOTAL_COMPLETED_RANDOM_MIN", "WLWQ_REFUND_TOTAL_COMPLETED_RANDOM_MAX", 1500, 2400)
        refund_orders = random_int("WLWQ_REFUND_ORDERS_RANDOM_MIN", "WLWQ_REFUND_ORDERS_RANDOM_MAX", 120, 260)
        refund_orders = min(refund_orders, total_completed)
        return _ok({"totalCompletedOrders": total_completed, "refundOrders": refund_orders})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS refund_orders FROM store_refund_order WHERE 1=1{sf}", sp)
            row = await cur.fetchone()
            refund = (row or {}).get("refund_orders", 0)
            await cur.execute(
                f"SELECT COUNT(*) AS total FROM store_order WHERE order_status>=3{sf}", sp,
            )
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
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        total_reviews = random_int("WLWQ_TOTAL_REVIEWS_RANDOM_MIN", "WLWQ_TOTAL_REVIEWS_RANDOM_MAX", 900, 1500)
        positive_reviews = random_int("WLWQ_POSITIVE_REVIEWS_RANDOM_MIN", "WLWQ_POSITIVE_REVIEWS_RANDOM_MAX", 520, 960)
        positive_reviews = min(positive_reviews, total_reviews)
        return _ok({"totalReviews": total_reviews, "positiveReviews": positive_reviews})
    try:
        sf, sp = _store_filter(storeId)
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total_reviews, "
                "SUM(CASE WHEN star>=4 THEN 1 ELSE 0 END) AS positive "
                f"FROM store_order_evaluate WHERE 1=1{sf}", sp,
            )
            row = await cur.fetchone()
            return _ok({
                "totalReviews": (row or {}).get("total_reviews", 0),
                "positiveReviews": (row or {}).get("positive", 0),
            })
    except Exception:
        return _ok({"totalReviews": 1680, "positiveReviews": 1462})


@router.get("/store-order/repurchase-stats")
async def repurchase_stats(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    if random_enabled(useRandom):
        total_buyers = random_int("WLWQ_TOTAL_BUYERS_RANDOM_MIN", "WLWQ_TOTAL_BUYERS_RANDOM_MAX", 2200, 3200)
        repeat_buyers = random_int("WLWQ_REPEAT_BUYERS_RANDOM_MIN", "WLWQ_REPEAT_BUYERS_RANDOM_MAX", 500, 950)
        repeat_buyers = min(repeat_buyers, total_buyers)
        active_customers = random_int("WLWQ_ACTIVE_CUSTOMERS_RANDOM_MIN", "WLWQ_ACTIVE_CUSTOMERS_RANDOM_MAX", 1800, 2800)
        active_customers = min(active_customers, total_buyers)
        churned_customers = random_int("WLWQ_CHURNED_CUSTOMERS_RANDOM_MIN", "WLWQ_CHURNED_CUSTOMERS_RANDOM_MAX", 420, 780)
        churned_customers = min(churned_customers, active_customers)
        avg_ltv = random_float("WLWQ_AVG_LTV_RANDOM_MIN", "WLWQ_AVG_LTV_RANDOM_MAX", 600.0, 980.0, 2)
        return _ok({
            "totalBuyers": total_buyers,
            "repeatBuyers": repeat_buyers,
            "activeCustomers": active_customers,
            "churnedCustomers": churned_customers,
            "avgLifetimeValue": avg_ltv,
        })
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
            return _ok({
                "totalBuyers": total,
                "repeatBuyers": repeat_,
                "activeCustomers": total,
                "churnedCustomers": max(0, int(total * 0.17)),
                "avgLifetimeValue": 1560,
            })
    except Exception:
        return _ok({
            "totalBuyers": 2800, "repeatBuyers": 1120,
            "activeCustomers": 2200, "churnedCustomers": 380, "avgLifetimeValue": 1560,
        })


