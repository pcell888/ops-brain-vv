"""5.2.3 规则任务构建 — 从规则规格列表生成 create_execution_tasks 所需任务。"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta

from src.core.config import CN_TZ

logger = logging.getLogger(__name__)

_DATE_PATTERNS = (
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
)
_RELATIVE_DAY_PATTERN = re.compile(r"^\s*(\d+)\s*(?:天|day|days)?(?:内)?\s*$", re.IGNORECASE)
_RELATIVE_HOUR_PATTERN = re.compile(r"^\s*(\d+)\s*(?:小时|小時|h|hr|hour|hours)(?:内)?\s*$", re.IGNORECASE)
_RELATIVE_HOUR_SEARCH = re.compile(r"(\d+)\s*(?:小时|小時|h|hr|hour|hours)(?:内)?", re.IGNORECASE)
_RELATIVE_DAY_SEARCH = re.compile(r"(\d+)\s*(?:天|day|days)(?:内)?", re.IGNORECASE)


def parse_deadline_date(value: object) -> datetime | None:
    """尽量从 deadline/timeline 文本中提取日期。"""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        iso = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if iso.tzinfo is not None:
            return iso.astimezone(CN_TZ).replace(tzinfo=None)
        return iso
    except ValueError:
        pass
    for p in _DATE_PATTERNS:
        m = p.search(s)
        if not m:
            continue
        y, mm, dd = m.groups()
        try:
            return datetime(int(y), int(mm), int(dd))
        except ValueError:
            continue
    return None


def resolve_deadline_fields(value: object) -> tuple[str | None, str | None]:
    """将 timeline/deadline 文案转换为保留文案 + 绝对截止时间。"""
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None

    hm = _RELATIVE_HOUR_PATTERN.match(text)
    if hm:
        hours = int(hm.group(1))
        normalized_text = f"{hours}小时内"
        deadline_at = (datetime.now(CN_TZ) + timedelta(hours=hours)).replace(microsecond=0).isoformat()
        return normalized_text, deadline_at

    m = _RELATIVE_DAY_PATTERN.match(text)
    if m:
        days = int(m.group(1))
        normalized_text = text if "天" in text else f"{days}天内"
        deadline_at = (datetime.now(CN_TZ) + timedelta(days=days)).replace(microsecond=0).isoformat()
        return normalized_text, deadline_at

    hm2 = _RELATIVE_HOUR_SEARCH.search(text)
    if hm2:
        hours = int(hm2.group(1))
        deadline_at = (datetime.now(CN_TZ) + timedelta(hours=hours)).replace(microsecond=0).isoformat()
        return f"{hours}小时内", deadline_at

    dm2 = _RELATIVE_DAY_SEARCH.search(text)
    if dm2:
        days = int(dm2.group(1))
        normalized_text = text.strip() if re.search(r"\d+\s*天", text) else f"{days}天内"
        deadline_at = (datetime.now(CN_TZ) + timedelta(days=days)).replace(microsecond=0).isoformat()
        return normalized_text, deadline_at

    parsed = parse_deadline_date(text)
    if parsed is None:
        return text, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CN_TZ)
    deadline_at = parsed.astimezone(CN_TZ).replace(microsecond=0).isoformat()
    return text, deadline_at


def resolve_review_due_at(all_tasks: list[dict], delay_days: float) -> datetime:
    """复盘到期时刻（上海时区）：优先取执行任务最晚 deadline 的当日 00:00；无则 now + delay_days。"""
    latest: datetime | None = None
    for t in all_tasks:
        d = parse_deadline_date(t.get("deadline_at") or t.get("deadline"))
        if d is None:
            continue
        if latest is None or d > latest:
            latest = d
    if latest is not None:
        return datetime.combine(latest.date(), datetime.min.time(), tzinfo=CN_TZ)
    return datetime.now(CN_TZ) + timedelta(days=float(delay_days))


def ensure_deadline_at(task: dict) -> None:
    """企服侧要求 deadline_at 非空：在解析失败时回退为「当前 + 7 天」。"""
    existing = task.get("deadline_at")
    if isinstance(existing, str) and existing.strip():
        return
    text, at = resolve_deadline_fields(task.get("deadline"))
    if at:
        task["deadline_at"] = at
        if text:
            task["deadline"] = text
        return
    fallback = (datetime.now(CN_TZ) + timedelta(days=7)).replace(microsecond=0).isoformat()
    task["deadline_at"] = fallback
    if not (isinstance(task.get("deadline"), str) and str(task.get("deadline")).strip()):
        task["deadline"] = "7天内"


def task_db_row_to_push_payload(row: dict) -> dict:
    """将 exec_tasks 行转为 create_execution_tasks 单条 payload，并保证 deadline_at。"""
    rr = row.get("related_resources")
    if isinstance(rr, str):
        try:
            rr = json.loads(rr)
        except json.JSONDecodeError:
            rr = {}
    elif not isinstance(rr, dict):
        rr = {}
    raw_at = row.get("deadline_at")
    deadline_at: str | None
    if hasattr(raw_at, "isoformat"):
        deadline_at = raw_at.isoformat()
    elif isinstance(raw_at, str) and raw_at.strip():
        deadline_at = raw_at.strip()
    else:
        deadline_at = None
    uid = row.get("assignee_user_id")
    if uid is not None:
        uid = str(uid)
    did = row.get("assignee_dept_id")
    if did is not None and did != "":
        did = str(did)
    else:
        did = None
    pr = row.get("priority") or "medium"
    payload = {
        "task_id": row.get("task_id"),
        "task_name": row.get("task_name") or "",
        "description": (row.get("description") or "")[:10000],
        "assignee_user_id": uid,
        "assignee_dept_id": did,
        "assignee_user_name": row.get("assignee_user_name"),
        "deadline": row.get("deadline"),
        "deadline_at": deadline_at,
        "priority": str(pr)[:20],
        "related_resources": rr,
    }
    ensure_deadline_at(payload)
    return payload


def build_tasks_from_rule_specs(
    specs: list[dict],
    dept_info: dict,
    indicator_code: str | None = None,
    override_assignee_user_id: str | None = None,
    override_assignee_user_name: str | None = None,
) -> list[dict]:
    """从 5.2.3 规则任务规格列表构建 create_execution_tasks 所需的 tasks。

    当 override_assignee_user_id 提供时，所有任务直接使用该 assignee，不再从 dept_info 解析。
    """
    tasks: list[dict] = []

    for s in specs:
        impl = s.get("implementation_steps") or []
        impl_list = [str(x).strip() for x in impl if str(x).strip()][:30] if isinstance(impl, list) else []
        deadline_text, deadline_at = resolve_deadline_fields(s.get("timeline"))

        task_name = s.get("task_name", "优化任务")

        uid = override_assignee_user_id
        dept_id = None

        description_parts = []
        if indicator_code:
            description_parts.append(f"[{indicator_code}异常]")
        description_parts.append(task_name)
        if impl_list:
            description_parts.append(f"关键步骤：{' → '.join(impl_list[:3])}")

        priority = "medium"
        if indicator_code:
            if indicator_code in ["refund_rate", "churn_rate"]:
                priority = "high"
            elif indicator_code in ["lead_conversion_rate", "positive_review_rate"]:
                priority = "medium"

        tdict = {
            "task_name": task_name,
            "description": " ".join(description_parts),
            "assignee_user_id": uid,
            "assignee_dept_id": dept_id,
            "assignee_user_name": override_assignee_user_name if override_assignee_user_id is not None else None,
            "deadline": deadline_text,
            "deadline_at": deadline_at,
            "priority": priority,
            "related_resources": {
                "implementation_steps": impl_list,
                "execution_type": "manual",
                "dispatch_status": "pending",
                "indicator_code": indicator_code,
            },
        }
        ensure_deadline_at(tdict)
        tasks.append(tdict)
    return tasks


def build_execution_tasks(
    plan: dict,
    dept_info: dict | None = None,
    override_assignee_user_id: str | None = None,
    override_assignee_user_name: str | None = None,
) -> list[dict]:
    """根据方案步骤构建执行任务列表。

    当 override_assignee_user_id 提供时，所有任务直接使用该 assignee，不再从 dept_info 解析。
    """
    tasks: list[dict] = []

    for step in plan.get("steps", []):
        action = step.get("action", plan.get("plan_name", ""))
        data_ctx = step.get("data_context", "")
        desc_parts = [f"[{plan.get('plan_name', '')}]"]
        if data_ctx:
            desc_parts.append(f"【数据依据】{data_ctx}")
        desc_parts.append(action)
        impl = step.get("implementation_steps") or []
        impl_list = [str(x).strip() for x in impl if str(x).strip()][:30] if isinstance(impl, list) else []
        deadline_text, deadline_at = resolve_deadline_fields(step.get("timeline"))
        tdict = {
            "task_name": action,
            "description": " ".join(desc_parts),
            "assignee_user_id": override_assignee_user_id,
            "assignee_dept_id": None,
            "assignee_user_name": override_assignee_user_name,
            "deadline": deadline_text,
            "deadline_at": deadline_at,
            "priority": plan.get("priority_level", "medium"),
            "related_resources": {
                "implementation_steps": impl_list,
                "execution_type": "manual",
                "dispatch_status": "pending",
            },
        }
        ensure_deadline_at(tdict)
        tasks.append(tdict)

    if not tasks:
        tdict = {
            "task_name": plan.get("plan_name", "优化任务"),
            "description": plan.get("description", ""),
            "assignee_user_id": override_assignee_user_id,
            "assignee_dept_id": None,
            "assignee_user_name": override_assignee_user_name,
            "deadline": None,
            "deadline_at": None,
            "priority": plan.get("priority_level", "medium"),
            "related_resources": {
                "implementation_steps": [],
                "execution_type": "manual",
                "dispatch_status": "pending",
            },
        }
        ensure_deadline_at(tdict)
        tasks.append(tdict)
    return tasks
