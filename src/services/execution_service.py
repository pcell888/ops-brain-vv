"""执行业务逻辑服务层。

封装执行计划和任务相关的核心业务逻辑，供 API 路由层调用。
"""

from __future__ import annotations

import logging
from datetime import timedelta

from src.core.datetime_cn import serialize_instant_cn, to_utc_aware
from src.repositories.exec_task import (
    count_distinct_plans,
    get_plan_group_by_id,
    get_task_by_id,
    query_filtered_tasks,
    query_plan_groups,
    query_plan_tasks,
    update_single_task_status,
)

logger = logging.getLogger(__name__)


def _implementation_steps_from_related(related) -> list[str]:
    if isinstance(related, dict):
        steps = related.get("implementation_steps")
        if isinstance(steps, list):
            return [str(s).strip() for s in steps if str(s).strip()]
    return []


def _execution_type_from_related(related) -> str:
    if isinstance(related, dict):
        et = related.get("execution_type")
        if isinstance(et, str) and et.strip():
            return et.strip().lower()[:32]
    return "manual"


def _task_progress_percent(status: str | None, related) -> int:
    if isinstance(related, dict):
        p = related.get("progress")
        if isinstance(p, (int, float)) and 0 <= float(p) <= 100:
            return int(round(float(p)))
    st = (status or "pending").lower()
    return 100 if st == "completed" else 0


def _dispatch_status_from_related(related) -> str:
    if isinstance(related, dict):
        ds = related.get("dispatch_status")
        if isinstance(ds, str) and ds.strip():
            return ds.strip().lower()[:32]
    return "pending"


def _recipient_from_row(row: dict) -> str:
    uid = row.get("assignee_user_id")
    did = row.get("assignee_dept_id")
    if uid is not None:
        return str(uid)
    if did:
        return str(did)
    return ""


def _calculate_plan_status(completed: int, running: int, failed: int, pending: int, total: int) -> str:
    if completed == total:
        return "completed"
    elif running > 0:
        return "running"
    elif failed > 0 and pending == 0 and running == 0:
        return "failed"
    else:
        return "pending"


def _calculate_plan_progress(completed: int, total: int) -> int:
    return round(completed / total * 100) if total > 0 else 0


def task_row_to_dict(row: dict, *, include_plan_meta: bool = False) -> dict:
    related = row.get("related_resources")
    task_status = row["status"] or "pending"
    recipient = _recipient_from_row(row)

    item: dict = {
        "id": row["task_id"],
        "task_key": row["task_id"],
        "name": row["task_name"] or "",
        "description": row["description"] or "",
        "implementation_steps": _implementation_steps_from_related(related),
        "status": task_status,
        "execution_type": _execution_type_from_related(related),
        "dependencies": [],
        "scheduled_start": serialize_instant_cn(row["created_at"]) if row.get("created_at") else None,
        "scheduled_end": serialize_instant_cn(row["deadline"]) if row.get("deadline") not in (None, "") else None,
        "progress": _task_progress_percent(task_status, related),
        "assigned_to": recipient,
        "recipient": recipient,
        "dispatch_status": _dispatch_status_from_related(related),
        "dispatch_time": serialize_instant_cn(row["created_at"]) if row.get("created_at") else None,
    }

    if include_plan_meta:
        item["plan_id"] = row["plan_id"]
        item["thread_id"] = row["thread_id"]

    return item


async def get_execution_plans(
    tenant_id: str | None = None,
    thread_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    try:
        rows = await query_plan_groups(tenant_id=tenant_id, thread_id=thread_id, skip=skip, limit=limit)
        total = await count_distinct_plans(tenant_id=tenant_id, thread_id=thread_id)

        items = []
        for row in rows:
            total_t = row["total_tasks"]
            completed_t = row["completed_tasks"]
            running_t = row["running_tasks"]
            failed_t = row["failed_tasks"]
            pending_t = row["pending_tasks"]

            plan_status = _calculate_plan_status(completed_t, running_t, failed_t, pending_t, total_t)
            progress = _calculate_plan_progress(completed_t, total_t)

            if status and plan_status != status:
                continue

            created = row["created_at"]
            planned_end = None
            if created:
                planned_end = serialize_instant_cn(to_utc_aware(created) + timedelta(days=30))
            items.append({
                "plan_id": row["plan_id"],
                "solution_id": row["plan_id"],
                "diagnosis_id": row["thread_id"],
                "name": f"执行计划 - {row['plan_id'][:8]}",
                "status": plan_status,
                "progress": progress,
                "task_stats": {
                    "pending": pending_t,
                    "ready": 0,
                    "running": running_t,
                    "paused": 0,
                    "completed": completed_t,
                    "failed": failed_t,
                    "cancelled": 0,
                },
                "planned_start": serialize_instant_cn(created) if created else None,
                "planned_end": planned_end,
            })

        return items, total
    except Exception:
        logger.exception("查询执行计划列表失败")
        return [], 0


async def get_execution_tasks(
    tenant_id: str | None = None,
    thread_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[dict], int, dict[str, int]]:
    try:
        rows, total, stats = await query_filtered_tasks(
            tenant_id=tenant_id, thread_id=thread_id, status=status, skip=skip, limit=limit,
        )
        items = [task_row_to_dict(row, include_plan_meta=True) for row in rows]
        return items, total, stats
    except Exception:
        logger.exception("查询执行任务列表失败")
        return [], 0, {
            "pending": 0, "ready": 0, "running": 0, "paused": 0,
            "completed": 0, "failed": 0, "cancelled": 0,
        }


async def get_task_detail(task_id: str) -> dict | None:
    row = await get_task_by_id(task_id)
    if not row:
        return None

    base = task_row_to_dict(row, include_plan_meta=True)
    related = row.get("related_resources")
    rr = related if isinstance(related, dict) else {}

    return {
        **base,
        "tenant_id": row.get("tenant_id"),
        "store_id": row.get("store_id"),
        "priority": row.get("priority"),
        "related_resources": rr,
    }


async def get_plan_summary(plan_id: str) -> dict | None:
    row = await get_plan_group_by_id(plan_id)
    if not row:
        return None

    total_t = row["total_tasks"]
    completed_t = row["completed_tasks"]
    running_t = row["running_tasks"]
    failed_t = row["failed_tasks"]
    pending_t = row["pending_tasks"]

    plan_status = _calculate_plan_status(completed_t, running_t, failed_t, pending_t, total_t)
    progress = _calculate_plan_progress(completed_t, total_t)
    created = row["created_at"]
    planned_end = None
    if created:
        planned_end = serialize_instant_cn(to_utc_aware(created) + timedelta(days=30))

    return {
        "plan_id": plan_id,
        "solution_id": plan_id,
        "name": f"执行计划 - {plan_id[:8]}",
        "status": plan_status,
        "progress": progress,
        "task_stats": {
            "pending": pending_t,
            "ready": 0,
            "running": running_t,
            "paused": 0,
            "completed": completed_t,
            "failed": failed_t,
            "cancelled": 0,
        },
        "planned_start": serialize_instant_cn(created) if created else None,
        "planned_end": planned_end,
    }


async def get_plan_tasks(plan_id: str, status: str | None = None) -> tuple[list[dict], int]:
    try:
        rows = await query_plan_tasks(plan_id, status=status)
        items = [task_row_to_dict(row, include_plan_meta=True) for row in rows]
        return items, len(items)
    except Exception:
        logger.exception("查询任务列表失败")
        return [], 0


async def update_task_status(task_id: str, new_status: str) -> bool:
    return await update_single_task_status(task_id, new_status)
