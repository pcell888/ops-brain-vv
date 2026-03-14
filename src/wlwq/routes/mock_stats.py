"""其他 MCP 用到的统计接口 — 无表时返回模拟数据。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor

router = APIRouter(tags=["mock-stats"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


def _mock(**kwargs):
    return _ok(kwargs)


@router.get("/service-order/completion-stats")
async def service_completion(
    storeId: str | None = Query(None),
    startDate: str | None = Query(None),
    endDate: str | None = Query(None),
):
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total, SUM(CASE WHEN order_status=8 THEN 1 ELSE 0 END) AS completed "
                "FROM service_order WHERE 1=1"
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
):
    try:
        async with get_cursor() as cur:
            await cur.execute("SELECT AVG(shipping_hours) AS avg_hours FROM store_order WHERE shipping_hours IS NOT NULL")
            row = await cur.fetchone()
            avg_h = float((row or {}).get("avg_hours", 0) or 12.0)
        return _ok({"avgShippingHours": avg_h})
    except Exception:
        return _ok({"avgShippingHours": 12.0})


@router.get("/account-coupon/statistics")
@router.get("/manage-data/exposure-stats")
@router.get("/store-order/conversion-stats")
@router.get("/store-activities/roi")
@router.get("/store-refund-order/statistics")
@router.get("/store-order-evaluate/statistics")
@router.get("/store-order/repurchase-stats")
async def generic_mock():
    return _ok({"total": 0, "list": []})
