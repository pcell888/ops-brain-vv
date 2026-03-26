"""AI 诊断执行任务 — 对接 task-server create_execution_tasks，5.2.3 推送落地。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Body

from src.wlwq.database import get_pool

router = APIRouter(prefix="/ai-diagnosis/exec-task", tags=["ai-diagnosis"])


def _ok(data=None):
    return {"code": 0, "data": data or {}, "msg": "success"}


def _gen_task_id():
    return f"task_{uuid.uuid4().hex[:12]}"


def _parse_deadline_at(task: dict) -> datetime | None:
    raw = task.get("deadline_at") or task.get("deadlineAt")
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


@router.post("/batch-create")
async def batch_create(body: dict = Body(...)):
    """
    批量创建执行任务。body: storeId, planId, tasks[].
    tasks: [{task_name, description?, assignee_user_id?, assignee_account_id?, assignee_dept_id?, deadline?, priority?, related_resources?(object)}]
    """
    tasks = body.get("tasks", [])
    store_id = str(body.get("storeId", ""))[:32]
    plan_id = str(body.get("planId", ""))[:32]
    tenant_id = str(body.get("tenantId", ""))[:32]
    created = []
    pool = await get_pool()
    async with pool.acquire() as conn:
        for t in tasks:
            task_id = _gen_task_id()
            deadline = t.get("deadline")
            if isinstance(deadline, str) and "T" in deadline:
                try:
                    from datetime import datetime
                    deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                    deadline_str = deadline_dt.isoformat()[:200]
                except Exception:
                    deadline_str = deadline[:200] if deadline else None
            else:
                deadline_str = (deadline[:200] if isinstance(deadline, str) else None) if deadline else None
            deadline_at_dt = _parse_deadline_at(t)
            await conn.execute(
                """
                INSERT INTO ai_diagnosis_task
                (task_id, tenant_id, store_id, plan_id, task_name, description,
                 assignee_user_id, assignee_account_id, assignee_dept_id, deadline, deadline_at, priority, related_resources)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                task_id,
                tenant_id,
                store_id,
                plan_id,
                (t.get("task_name") or "")[:500],
                (t.get("description") or "")[:10000] if t.get("description") else None,
                t.get("assignee_user_id"),
                str(t.get("assignee_account_id", ""))[:32],
                str(t.get("assignee_dept_id", ""))[:32],
                deadline_str,
                deadline_at_dt,
                str(t.get("priority", ""))[:20],
                json.dumps(t.get("related_resources") if isinstance(t.get("related_resources"), dict) else {}),
            )
            created.append({"task_id": task_id, **t})
    return _ok({"tasks": created, "count": len(created)})


@router.put("/{task_id}/status")
async def update_status(task_id: str, body: dict = Body(...)):
    """更新任务状态。body: status, progress?, remark?"""
    status = (body.get("status") or "")[:20]
    progress = body.get("progress")
    remark = (body.get("remark") or "")[:2000] if body.get("remark") else None
    pool = await get_pool()
    async with pool.acquire() as conn:
        if progress is not None:
            await conn.execute(
                "UPDATE ai_diagnosis_task SET status = $1, progress = $2, remark = $3, updated_at = CURRENT_TIMESTAMP WHERE task_id = $4",
                status, progress, remark, task_id,
            )
        else:
            await conn.execute(
                "UPDATE ai_diagnosis_task SET status = $1, remark = $2, updated_at = CURRENT_TIMESTAMP WHERE task_id = $3",
                status, remark, task_id,
            )
    return _ok({"task_id": task_id, "updated": True})
