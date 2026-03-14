"""消息提醒与记录 — 供 MCP notify-server 调用。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["message"])


def _ok(data=None):
    return {"code": 0, "data": data or {}, "msg": "success"}


@router.post("/message-remind/batch-create")
async def message_remind_batch_create(body: dict):
    """批量创建消息提醒。"""
    return _ok()


@router.post("/message-remind/create")
async def message_remind_create(body: dict):
    """单条创建消息提醒。"""
    return _ok()


@router.post("/message-record/create")
async def message_record_create(body: dict):
    """创建消息记录。"""
    return _ok()
