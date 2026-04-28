"""执行任务、消息、优惠券、秒杀模拟。"""

from __future__ import annotations

import random as _r
import uuid
from datetime import datetime


def parse_deadline_at(task: dict) -> datetime | None:
    raw = task.get("deadline_at") or task.get("deadlineAt")
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _gen_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


def exec_task_batch_create(body: dict) -> dict:
    tasks = body.get("tasks", [])
    created = []
    for t in tasks:
        task_id = _gen_task_id()
        created.append({"task_id": task_id, **t})
    return {"tasks": created, "count": len(created)}


def has_create_task_permission(q: dict) -> dict:
    user_id = str(q.get("userId") or "").strip()
    return {"hasPermission": "true" if user_id else "false"}


def exec_task_update_status(task_id: str, body: dict) -> dict:
    status = (body.get("status") or "")[:20]
    return {"task_id": task_id, "status": status, "updated": True}


def message_batch_create(body: dict) -> dict:
    messages = body.get("messages", [])
    if not messages:
        return {"count": 0}
    return {"count": len(messages)}


def message_targeted(body: dict) -> dict:
    segment = body.get("targetSegment", "")
    if segment not in (
        "churn_risk",
        "no_repurchase_90d",
        "coupon_expiring_soon",
        "low_conversion",
    ):
        return {"sent_count": 0, "error": f"unknown segment: {segment}"}
    n = _r.randint(8, 120)
    return {"sent_count": n, "segment": segment}


def _gen_coupon_id() -> str:
    return f"cp_{uuid.uuid4().hex[:14]}"[:20]


def coupon_create(_body: dict) -> dict:
    return {"couponId": _gen_coupon_id()}


def coupon_distribute(body: dict) -> dict:
    target = body.get("targetCustomers", "all")
    count = _r.randint(15, 280)
    return {"count": count, "targetCustomers": target}


def seckill_create(_body: dict) -> dict:
    sk_id = f"sk_{uuid.uuid4().hex[:14]}"[:20]
    return {"id": sk_id}
