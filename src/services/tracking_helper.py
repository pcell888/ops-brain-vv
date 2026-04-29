"""效果追踪通用工具与待复盘行时间字段。"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime

from src.core.datetime_cn import serialize_instant_cn
from src.repositories.tracking import (
    get_diagnosis_health_score,
    get_earliest_exec_task_created_at,
    get_first_exec_task,
    get_latest_adopted_plan_name,
)
from src.core.tracking_names import resolve_solution_name

logger = logging.getLogger(__name__)


def _ser(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return serialize_instant_cn(v)
    if isinstance(v, date):
        return serialize_instant_cn(v)
    if isinstance(v, str):
        return serialize_instant_cn(v)
    if hasattr(v, "isoformat") and callable(v.isoformat):
        return serialize_instant_cn(v) or v.isoformat()
    return v


def _to_float(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_int(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _parse_dt(v) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    text = str(v).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_json_dict(text: str) -> dict | None:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_plan_name_from_desc(desc: object) -> str | None:
    text = str(desc or "").strip()
    if not text:
        return None
    m = re.match(r"^\[(.+?)\]", text)
    if m:
        name = m.group(1).strip()
        return name or None
    lines = text.split("\n")
    first_line = lines[0].strip() if lines else ""
    um = re.match(r"^【(?:紧急|重要|常规)】(.+)$", first_line)
    if um:
        return um.group(1).strip() or None
    return first_line[:80] or None


async def _get_diagnosis_health_score(thread_id: str) -> float | None:
    return await get_diagnosis_health_score(thread_id)


def _derive_tracking_status(tracking_data: dict) -> str:
    raw = str(tracking_data.get("status") or "").strip().lower()
    if raw in {"active", "completed", "cancelled", "scheduled"}:
        return raw
    return "active"


def _is_tracking_completed(tracking_data: dict) -> bool:
    return _derive_tracking_status(tracking_data) == "completed"


async def _derive_adopted_plan_name(tracking_id: str, tracking_data: dict) -> str | None:
    plan_name = await get_latest_adopted_plan_name(tracking_id)
    if plan_name:
        return plan_name

    plan_id = str((tracking_data or {}).get("plan_id") or "").strip()
    task_row = await get_first_exec_task(tracking_id, plan_id=plan_id or None)
    if task_row:
        from_desc = _extract_plan_name_from_desc(task_row.get("description"))
        if from_desc:
            return from_desc
        from_task = str(task_row.get("task_name") or "").strip()
        if from_task and not from_task.startswith("执行计划 -"):
            return from_task
    return None


async def _scheduled_row_enrichment(thread_id: str) -> tuple[str, float | None]:
    adopted_label: str | None = None
    health: float | None = None
    try:
        adopted_label = await _derive_adopted_plan_name(thread_id, {})
        health = await _get_diagnosis_health_score(thread_id)
    except Exception:
        logger.exception("待复盘行展示字段查询失败 thread=%s", thread_id)
    solution_name = resolve_solution_name({}, adopted_label)
    return solution_name, health


async def _earliest_exec_task_created_at(thread_id: str) -> datetime | None:
    try:
        t = await get_earliest_exec_task_created_at(thread_id)
        if t is None:
            return None
        return t if isinstance(t, datetime) else _parse_dt(str(t))
    except Exception:
        return None


async def _scheduled_tracking_started_at(pr: dict, thread_id: str) -> datetime | None:
    ca = pr.get("created_at")
    if ca is not None:
        if isinstance(ca, datetime):
            return ca
        parsed = _parse_dt(str(ca))
        if parsed:
            return parsed
    return await _earliest_exec_task_created_at(thread_id)
