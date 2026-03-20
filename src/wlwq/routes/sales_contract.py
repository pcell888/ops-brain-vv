"""销售合同相关 API — 对接 MCP /sales-contract/*。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor
from src.wlwq.routes._random_control import random_enabled, random_int

router = APIRouter(prefix="/sales-contract", tags=["sales-contract"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/statistics")
async def statistics(
    storeId: str | None = Query(None, alias="storeId"),
    startDate: str | None = Query(None, alias="startDate"),
    endDate: str | None = Query(None, alias="endDate"),
    useRandom: bool | None = Query(None, alias="useRandom"),
):
    """签约数等。"""
    if random_enabled(useRandom):
        return _ok({
            "signedCount": random_int(
                "WLWQ_SALES_CONTRACT_RANDOM_MIN",
                "WLWQ_SALES_CONTRACT_RANDOM_MAX",
                70,
                120,
            )
        })
    try:
        async with get_cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS signed_count FROM sales_contract WHERE del_status=0 "
                + (" AND sign_time>=%s" if startDate else "")
                + (" AND sign_time<=%s" if endDate else ""),
                tuple(x for x in [startDate, endDate] if x is not None),
            )
            row = await cur.fetchone()
            signed = (row or {}).get("signed_count", 0)
    except Exception:
        signed = 0
    return _ok({"signedCount": signed})


@router.get("/list")
async def list_contracts(
    clientRecordId: str | None = Query(None, alias="clientRecordId"),
    page: int = Query(1, alias="page"),
    pageSize: int = Query(20, alias="pageSize"),
):
    """合同列表。"""
    try:
        async with get_cursor() as cur:
            sql = "SELECT * FROM sales_contract WHERE 1=1"
            params = []
            if clientRecordId:
                sql += " AND client_record_id=%s"
                params.append(clientRecordId)
            sql += " LIMIT %s OFFSET %s"
            params.extend([pageSize, (page - 1) * pageSize])
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    except Exception:
        rows = []
    return _ok({"list": rows, "total": len(rows)})
