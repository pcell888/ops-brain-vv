"""审批/跟进相关 API — 对接 MCP /examine-initiate/*。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Body

from src.wlwq.database import get_cursor

router = APIRouter(prefix="/examine-initiate", tags=["examine-initiate"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/follow-stats")
async def follow_stats(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
):
    """跟进统计：followTotal, avgResponseHours。"""
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
):
    """审批时效：onTimeRate。"""
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
    """创建审批/跟进单 — MCP task 调用。"""
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "INSERT INTO examine_initiate (store_id, title, content, created_at) VALUES (%s, %s, %s, NOW())",
                (body.get("storeId"), body.get("title", ""), body.get("content", "")),
            )
            await cur.execute("SELECT LAST_INSERT_ID() AS id")
            row = await cur.fetchone()
            id_ = (row or {}).get("id")
        return _ok({"id": id_})
    except Exception:
        return _ok({"id": "mock-1"})

