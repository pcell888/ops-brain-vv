"""优惠券与秒杀 — 供 MCP task-server create_coupon_campaign / create_seckill_activity 调用。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body

from src.wlwq.database import get_pool

router = APIRouter(tags=["coupon"])


def _ok(data=None):
    return {"code": 0, "data": data or {}, "msg": "success"}


def _gen_id(prefix: str = "ac", length: int = 14) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


@router.post("/coupon/create")
async def coupon_create(body: dict = Body(...)):
    """创建优惠券。"""
    coupon_id = _gen_id("cp")[:20]
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO coupon
            (coupon_id, store_id, coupon_name, coupon_type, full_price, reduce_price,
             start_time, end_time, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::timestamp, $8::timestamp, NOW())
            """,
            coupon_id,
            body.get("storeId", ""),
            body.get("couponName", ""),
            body.get("couponType", 1),
            body.get("fullPrice", 0),
            body.get("reducePrice", 0),
            body.get("startTime"),
            body.get("endTime"),
        )
    return _ok({"couponId": coupon_id})


_TARGET_QUERIES: dict[str, str] = {
    "churn_risk": """
        SELECT DISTINCT account_id FROM store_order
        WHERE order_status = 6 AND account_id != ''
        GROUP BY account_id
        HAVING MAX(pay_time) < NOW() - INTERVAL '60 days'
        LIMIT 500
    """,
    "no_repurchase_90d": """
        SELECT DISTINCT account_id FROM store_order
        WHERE order_status = 6 AND account_id != ''
        GROUP BY account_id
        HAVING MAX(pay_time) < NOW() - INTERVAL '90 days'
        LIMIT 500
    """,
    "all": """
        SELECT DISTINCT account_id FROM store_order
        WHERE account_id != ''
        LIMIT 1000
    """,
}


@router.post("/coupon/distribute")
async def coupon_distribute(body: dict = Body(...)):
    """按目标客群定向发放优惠券，写入 account_coupon 表。"""
    coupon_id = body.get("couponId", "")
    target = body.get("targetCustomers", "all")

    query = _TARGET_QUERIES.get(target, _TARGET_QUERIES["all"])

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query)
        account_ids = [r["account_id"] for r in rows if r.get("account_id")]

        if not account_ids:
            return _ok({"count": 0, "targetCustomers": target})

        for aid in account_ids:
            ac_id = _gen_id("ac")[:20]
            await conn.execute(
                """
                INSERT INTO account_coupon
                (account_coupon_id, account_id, coupon_id, use_status, create_time)
                VALUES ($1, $2, $3, 0, NOW())
                """,
                ac_id, str(aid), coupon_id,
            )

    return _ok({"count": len(account_ids), "targetCustomers": target})


@router.post("/seckill-apply/create")
async def seckill_create(body: dict = Body(...)):
    """创建秒杀活动。"""
    sk_id = _gen_id("sk")[:20]
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO seckill_apply
            (seckill_apply_id, store_id, title, start_time, end_time, created_at)
            VALUES ($1, $2, $3, $4::timestamp, $5::timestamp, NOW())
            """,
            sk_id,
            body.get("storeId", ""),
            body.get("title", "AI秒杀活动"),
            body.get("startTime"),
            body.get("endTime"),
        )
    return _ok({"id": sk_id})
