"""客户记录相关 API — 对接 MCP metrics/crm 的 /client-record/*。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor
from src.wlwq.routes._random_control import random_enabled, random_int

router = APIRouter(prefix="/client-record", tags=["client-record"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/statistics")
async def statistics(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    """CRM 维度：客户总数 & 新增客户数。"""
    if random_enabled(useRandom):
        total = random_int(
            "WLWQ_CLIENT_TOTAL_RANDOM_MIN",
            "WLWQ_CLIENT_TOTAL_RANDOM_MAX",
            2600,
            3400,
        )
        new_clients = random_int(
            "WLWQ_CLIENT_NEW_RANDOM_MIN",
            "WLWQ_CLIENT_NEW_RANDOM_MAX",
            80,
            200,
        )
        return _ok({"total": total, "newClients": new_clients})
    try:
        conditions = ["del_status=0"]
        params = []
        if storeId:
            conditions.append("store_id=%s")
            params.append(storeId)
        if startDate:
            conditions.append("create_time>=%s")
            params.append(startDate)
        if endDate:
            conditions.append("create_time<=%s")
            params.append(endDate)
        where = " AND ".join(conditions)
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS total FROM client_record WHERE {where}",
                params,
            )
            row = await cur.fetchone()
            total = (row or {}).get("total", 0)
            await cur.execute(
                f"SELECT COUNT(*) AS new_clients FROM client_record WHERE {where}"
                + (" AND create_time>=CURDATE()" if not startDate else ""),
                params,
            )
            row2 = await cur.fetchone()
            new_clients = (row2 or {}).get("new_clients", 0)
    except Exception:
        total = 0
        new_clients = 0
    return _ok({"total": total, "newClients": new_clients})


@router.get("/list")
async def list_records(
    storeId: str | None = Query(None, alias="storeId"),
    filterType: str | None = Query(None, alias="filterType"),
    page: int = Query(1, alias="page"),
    pageSize: int = Query(20, alias="pageSize"),
):
    """客户记录列表，支持分页与筛选。"""
    try:
        conditions = ["cr.del_status=0"]
        params = []
        if storeId:
            conditions.append("cr.store_id=%s")
            params.append(storeId)
        where = " AND ".join(conditions)
        order_clause = ""
        if filterType == "high_value":
            order_clause = " ORDER BY cr.total_amount DESC"
        elif filterType == "churn_risk":
            order_clause = " ORDER BY cr.last_order_days DESC"
        elif filterType == "new":
            order_clause = " ORDER BY cr.create_time DESC"
        elif filterType == "no_repurchase":
            order_clause = " ORDER BY cr.create_time ASC"
        elif filterType == "low_conversion":
            order_clause = " ORDER BY cr.create_time DESC"
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS cnt FROM client_record cr WHERE {where}",
                params,
            )
            total = ((await cur.fetchone()) or {}).get("cnt", 0)
            await cur.execute(
                f"SELECT cr.client_record_id AS id, cr.name, cr.phone, "
                f'cr.tags, cr.last_order_days AS "lastOrderDays" '
                f"FROM client_record cr WHERE {where}{order_clause} LIMIT %s OFFSET %s",
                params + [pageSize, (page - 1) * pageSize],
            )
            rows = await cur.fetchall()
            for r in rows:
                if isinstance(r.get("tags"), str):
                    import json as _json

                    try:
                        r["tags"] = _json.loads(r["tags"])
                    except Exception:
                        r["tags"] = [r["tags"]] if r["tags"] else []
    except Exception:
        rows = []
        total = 0
    return _ok({"list": rows, "total": total})


@router.get("/{client_record_id}")
async def get_record(client_record_id: str):
    """单条客户记录。"""
    try:
        async with get_cursor() as cur:
            await cur.execute(
                'SELECT client_record_id AS id, name, phone, total_orders AS "totalOrders", '
                'total_amount AS "totalAmount" FROM client_record WHERE client_record_id=%s',
                (client_record_id,),
            )
            row = await cur.fetchone()
    except Exception:
        row = None
    return _ok(row or {})
