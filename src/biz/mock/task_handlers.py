"""Task dispatch — 供 dispatch 路由。"""

from __future__ import annotations

from src.biz.http_client import HTTPClientError
from src.biz.mock.handlers import client_sales_examine
from src.biz.mock.handlers import task_message_coupon


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    m = method.upper()
    if m == "GET" and path == "ai-diagnosis/hasCreateTaskPermission":
        return task_message_coupon.has_create_task_permission(q)
    if m == "POST" and path == "examine-initiate/create":
        return client_sales_examine.examine_create(body)
    if m == "POST" and path == "ai-diagnosis/exec-task/batch-create":
        return task_message_coupon.exec_task_batch_create(body)
    if m == "PUT" and path.startswith("ai-diagnosis/exec-task/") and path.endswith("/status"):
        inner = path[len("ai-diagnosis/exec-task/") : -len("/status")]
        if not inner:
            raise HTTPClientError(404, "缺少 task_id", path)
        return task_message_coupon.exec_task_update_status(inner, body)
    if m == "POST" and path == "coupon/create":
        return task_message_coupon.coupon_create(body)
    if m == "POST" and path == "coupon/distribute":
        return task_message_coupon.coupon_distribute(body)
    if m == "POST" and path == "seckill-apply/create":
        return task_message_coupon.seckill_create(body)
    _ = q
    return None