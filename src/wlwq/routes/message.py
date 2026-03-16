"""消息提醒与记录 — 供 MCP notify-server 调用。"""

from __future__ import annotations

import uuid
from fastapi import APIRouter

from src.wlwq.database import get_pool

router = APIRouter(tags=["message"])


def _ok(data=None):
    return {"code": 0, "data": data or {}, "msg": "success"}


def _gen_id(prefix="mr", length=16):
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


@router.post("/message-remind/batch-create")
async def message_remind_batch_create(body: dict):
    """批量创建消息提醒。body: messages: [{accountId, title, content, type?, jumpUrl?}]"""
    messages = body.get("messages", [])
    if not messages:
        return _ok({"count": 0})
    pool = await get_pool()
    async with pool.acquire() as conn:
        for m in messages:
            rid = _gen_id("mr")[:20]
            await conn.execute(
                """
                INSERT INTO message_remind
                (message_remind_id, account_id, message_title, message_content, message_type, model_id, model_status)
                VALUES ($1, $2, $3, $4, $5, $6, 1)
                """,
                rid,
                str(m.get("accountId", "")),
                m.get("title", "")[:1000],
                (m.get("content") or "")[:10000],
                m.get("type", ""),
                m.get("jumpUrl", "")[:64],
            )
    return _ok({"count": len(messages)})


@router.post("/message-remind/create")
async def message_remind_create(body: dict):
    """单条创建消息提醒。"""
    rid = _gen_id("mr")[:20]
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO message_remind
            (message_remind_id, account_id, message_title, message_content, message_type, model_id, model_status)
            VALUES ($1, $2, $3, $4, $5, $6, 1)
            """,
            rid,
            str(body.get("accountId", "")),
            (body.get("title") or "")[:1000],
            (body.get("content") or "")[:10000],
            body.get("type", ""),
            str(body.get("bizId", ""))[:64],
        )
    return _ok({"message_remind_id": rid})


@router.post("/message-record/create")
async def message_record_create(body: dict):
    """创建消息记录。body: storeId?, userId?, type, title, content, bizId?"""
    rid = _gen_id("rec")[:20]
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO message_record
            (message_record_id, user_id, store_id, title, brief, message_type, model_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            rid,
            body.get("userId") or body.get("user_id"),
            str(body.get("storeId", ""))[:32],
            (body.get("title") or "")[:1000],
            (body.get("content") or "")[:10000],
            body.get("type", ""),
            str(body.get("bizId", ""))[:64],
        )
    return _ok({"message_record_id": rid})


_SEGMENT_QUERIES: dict[str, str] = {
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
    "coupon_expiring_soon": """
        SELECT DISTINCT account_id FROM account_coupon
        WHERE use_status = 0 AND account_id != ''
        LIMIT 500
    """,
    "low_conversion": """
        SELECT DISTINCT md.account_id
        FROM manage_data md
        LEFT JOIN store_order so ON md.account_id = so.account_id AND so.order_status = 6
        WHERE md.date_type = 1 AND md.account_id != '' AND so.store_order_id IS NULL
        LIMIT 500
    """,
}


@router.post("/message-remind/targeted")
async def message_remind_targeted(body: dict):
    """
    按人群定向推送消息（5.2.3）。
    body: storeId, targetSegment, title, content, type.
    根据 targetSegment 查询目标客户列表后批量写 message_remind。
    """
    segment = body.get("targetSegment", "")
    title = (body.get("title") or "")[:1000]
    content = (body.get("content") or "")[:10000]
    msg_type = body.get("type", "ai_targeted")

    query = _SEGMENT_QUERIES.get(segment)
    if not query:
        return _ok({"sent_count": 0, "error": f"unknown segment: {segment}"})

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query)
        account_ids = [r["account_id"] for r in rows if r.get("account_id")]

        if not account_ids:
            return _ok({"sent_count": 0, "segment": segment})

        for aid in account_ids:
            rid = _gen_id("mr")[:20]
            await conn.execute(
                """
                INSERT INTO message_remind
                (message_remind_id, account_id, message_title, message_content, message_type, model_id, model_status)
                VALUES ($1, $2, $3, $4, $5, $6, 1)
                """,
                rid, str(aid), title, content, msg_type, segment,
            )

    return _ok({"sent_count": len(account_ids), "segment": segment})
