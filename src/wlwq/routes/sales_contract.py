"""销售合同相关 API — 对接 MCP /sales-contract/*。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor
from src.wlwq.routes._random_control import random_enabled, random_float, random_int

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
    """签约数 & 签约总额。"""
    if random_enabled(useRandom):
        return _ok(
            {
                "signedCount": random_int(
                    "WLWQ_SALES_CONTRACT_RANDOM_MIN",
                    "WLWQ_SALES_CONTRACT_RANDOM_MAX",
                    70,
                    120,
                ),
                "totalAmount": random_float(
                    "WLWQ_SALES_AMOUNT_RANDOM_MIN",
                    "WLWQ_SALES_AMOUNT_RANDOM_MAX",
                    280000.0,
                    520000.0,
                ),
            }
        )
    try:
        conditions = ["del_status=0"]
        params = []
        if storeId:
            conditions.append("store_id=%s")
            params.append(storeId)
        if startDate:
            conditions.append("sign_time>=%s")
            params.append(startDate)
        if endDate:
            conditions.append("sign_time<=%s")
            params.append(endDate)
        where = " AND ".join(conditions)
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS signed_count, COALESCE(SUM(amount), 0) AS total_amount "
                f"FROM sales_contract WHERE {where}",
                params,
            )
            row = await cur.fetchone()
            signed = (row or {}).get("signed_count", 0)
            total_amount = float((row or {}).get("total_amount", 0))
    except Exception:
        signed = 0
        total_amount = 0.0
    return _ok({"signedCount": signed, "totalAmount": total_amount})


@router.get("/list")
async def list_contracts(
    clientRecordId: str | None = Query(None, alias="clientRecordId"),
    page: int | None = Query(None, alias="page"),
    pageNo: int | None = Query(None, alias="pageNo"),
    pageSize: int = Query(20, alias="pageSize"),
):
    """合同列表。"""
    current_page = pageNo or page or 1
    try:
        conditions = ["del_status=0"]
        params = []
        if clientRecordId:
            conditions.append("client_record_id=%s")
            params.append(clientRecordId)
        where = " AND ".join(conditions)
        async with get_cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS cnt FROM sales_contract WHERE {where}",
                params,
            )
            total = ((await cur.fetchone()) or {}).get("cnt", 0)
            await cur.execute(
                f"SELECT sales_contract_id AS id, amount, status FROM sales_contract WHERE {where} LIMIT %s OFFSET %s",
                params + [pageSize, (current_page - 1) * pageSize],
            )
            rows = await cur.fetchall()
    except Exception:
        rows = []
        total = 0
    return _ok({"list": rows, "total": total})
