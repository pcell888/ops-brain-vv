"""客户记录相关 API — 对接 MCP metrics/crm 的 /client-record/*。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor

router = APIRouter(prefix="/client-record", tags=["client-record"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/statistics")
async def statistics(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
):
    """CRM 维度：总客户数等。"""
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total FROM client_record WHERE del_status=0 "
                + (" AND create_time>=%s" if startDate else "")
                + (" AND create_time<=%s" if endDate else ""),
                tuple(x for x in [startDate, endDate] if x is not None),
            )
            row = await cur.fetchone()
            total = (row or {}).get("total", 0)
    except Exception:
        total = 0
    return _ok({"total": total})


@router.get("/list")
async def list_records(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
    clientRecordId: str | None = Query(None, alias="clientRecordId"),
    filterType: str | None = Query(None, alias="filterType"),
    page: int = Query(1, alias="page"),
    pageSize: int = Query(20, alias="pageSize"),
):
    """客户记录列表，支持分页与筛选。"""
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT * FROM client_record WHERE 1=1 LIMIT %s OFFSET %s",
                (pageSize, (page - 1) * pageSize),
            )
            rows = await cur.fetchall()
    except Exception:
        rows = []
    return _ok({"list": rows, "total": len(rows)})


@router.get("/{client_record_id}")
async def get_record(client_record_id: str):
    """单条客户记录。"""
    try:
        async with get_cursor() as cur:
            await cur.execute("SELECT * FROM client_record WHERE client_record_id=%s", (client_record_id,))
            row = await cur.fetchone()
    except Exception:
        row = None
    return _ok(row or {})
