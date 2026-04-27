"""Notify dispatch — 供 dispatch 路由。"""

from __future__ import annotations

from src.biz.mock.handlers import task_message_coupon


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    m = method.upper()
    if m == "POST" and path == "message-remind/batch-create":
        return task_message_coupon.message_batch_create(body)
    if m == "POST" and path == "message-remind/targeted":
        return task_message_coupon.message_targeted(body)
    _ = q
    return None