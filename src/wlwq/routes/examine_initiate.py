"""审批/跟进相关 API — 对接 MCP /examine-initiate/*。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Body

from src.wlwq.database import get_pool, get_cursor
from src.wlwq.routes._random_control import random_enabled, random_float, random_int

router = APIRouter(prefix="/examine-initiate", tags=["examine-initiate"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


def _gen_id(prefix: str = "ei", length: int = 16) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


@router.get("/follow-stats")
async def follow_stats(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    """跟进统计：followTotal, avgResponseHours。"""
    if random_enabled(useRandom):
        return _ok({
            "followTotal": random_int("WLWQ_FOLLOW_TOTAL_RANDOM_MIN", "WLWQ_FOLLOW_TOTAL_RANDOM_MAX", 380, 720),
            "avgResponseHours": random_float("WLWQ_AVG_RESPONSE_RANDOM_MIN", "WLWQ_AVG_RESPONSE_RANDOM_MAX", 8.0, 12.0, 2),
        })
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS follow_total, COALESCE(AVG(response_hours), 0) AS avg_response_hours "
                "FROM examine_initiate WHERE 1=1 "
                + (" AND store_id=%s" if storeId else "")
                + (" AND created_at>=%s" if startDate else "")
                + (" AND created_at<=%s" if endDate else ""),
                tuple(x for x in [storeId, startDate, endDate] if x is not None),
            )
            row = await cur.fetchone()
            follow_total = (row or {}).get("follow_total", 0)
            avg_response = float((row or {}).get("avg_response_hours", 0))
    except Exception:
        follow_total = 0
        avg_response = 0.0
    return _ok({"followTotal": follow_total, "avgResponseHours": avg_response})


@router.get("/turnaround-stats")
async def turnaround_stats(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    """审批时效：onTimeRate。"""
    if random_enabled(useRandom):
        return _ok({
            "onTimeRate": random_float("WLWQ_ON_TIME_RATE_RANDOM_MIN", "WLWQ_ON_TIME_RATE_RANDOM_MAX", 45.0, 68.0, 2)
        })
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total, SUM(CASE WHEN turnaround_hours <= 24 THEN 1 ELSE 0 END) AS on_time "
                "FROM examine_initiate WHERE 1=1 "
                + (" AND store_id=%s" if storeId else "")
                + (" AND created_at>=%s" if startDate else "")
                + (" AND created_at<=%s" if endDate else ""),
                tuple(x for x in [storeId, startDate, endDate] if x is not None),
            )
            row = await cur.fetchone()
            total = (row or {}).get("total", 0) or 1
            on_time = (row or {}).get("on_time", 0)
            rate = (on_time / total * 100) if total else 0
    except Exception:
        rate = 100.0
    return _ok({"onTimeRate": round(rate, 2)})


@router.post("/create")
async def create(body: dict = Body(...)):
    """
    创建审批单并生成审批流程记录。
    body: storeId, title, content, approverUserId, bizType(ai_diagnosis等), bizId(plan_id等)
    """
    store_id = body.get("storeId", "")
    title = body.get("title", "")
    content = body.get("content", "")
    approver_user_id = body.get("approverUserId")
    biz_type = body.get("bizType", "")
    biz_id = body.get("bizId", "")
    user_id = body.get("userId")

    ei_id = _gen_id("ei")[:20]
    examine_tag = _gen_id("tag", 8)[:20]

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO examine_initiate
            (examine_initiate_id, store_id, title, content,
             biz_type, biz_id, user_id, examine_status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 1, NOW())
            """,
            ei_id, store_id, title, content,
            biz_type, biz_id, user_id,
        )

        if approver_user_id:
            flow_id = _gen_id("oef")[:20]
            await conn.execute(
                """
                INSERT INTO oa_examine_flow
                (oa_examine_flow_id, examine_initiate_id, examine_tag,
                 user_id, examine_sequence, examine_status, created_at)
                VALUES ($1, $2, $3, $4, 1, 2, NOW())
                """,
                flow_id, ei_id, examine_tag, int(approver_user_id),
            )

    return _ok({
        "id": ei_id,
        "examine_status": 1,
        "approver_user_id": approver_user_id,
        "biz_type": biz_type,
        "biz_id": biz_id,
    })

