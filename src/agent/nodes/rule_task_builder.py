"""5.2.3 规则任务构建 — 从规则规格列表生成 create_execution_tasks 所需任务。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from src.core.config import CN_TZ
from src.core.dept_resolver import resolve_dept_assignee, resolve_default_assignee

_DATE_PATTERNS = (
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
)
_RELATIVE_DAY_PATTERN = re.compile(r"^\s*(\d+)\s*(?:天|day|days)?(?:内)?\s*$", re.IGNORECASE)
_RELATIVE_HOUR_PATTERN = re.compile(r"^\s*(\d+)\s*(?:小时|小時|h|hr|hour|hours)(?:内)?\s*$", re.IGNORECASE)


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

    parsed = parse_deadline_date(text)
    if parsed is None:
        return text, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CN_TZ)
    deadline_at = parsed.astimezone(CN_TZ).replace(microsecond=0).isoformat()
    return text, deadline_at


def resolve_review_due_date(all_tasks: list[dict], delay_days: int) -> datetime.date:
    """复盘到期日：优先使用执行任务最晚 deadline；无则回退为 now + delay_days。"""
    latest: datetime | None = None
    for t in all_tasks:
        d = parse_deadline_date(t.get("deadline_at") or t.get("deadline"))
        if d is None:
            continue
        if latest is None or d > latest:
            latest = d
    if latest is not None:
        return latest.date()
    return (datetime.now(CN_TZ) + timedelta(days=delay_days)).date()


def build_tasks_from_rule_specs(specs: list[dict], dept_info: dict, indicator_code: str | None = None) -> list[dict]:
    """从 5.2.3 规则任务规格列表构建 create_execution_tasks 所需的 tasks。"""
    tasks: list[dict] = []
    default_uid, default_dept_id = resolve_default_assignee(dept_info)

    for s in specs:
        uid, dept_id = resolve_dept_assignee(s.get("owner_dept", ""), dept_info)
        if uid is None and default_uid is not None:
            uid = default_uid
            dept_id = default_dept_id
        impl = s.get("implementation_steps") or []
        impl_list = [str(x).strip() for x in impl if str(x).strip()][:30] if isinstance(impl, list) else []
        deadline_text, deadline_at = resolve_deadline_fields(s.get("timeline"))

        task_name = s.get("task_name", "优化任务")
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

        tasks.append({
            "task_name": task_name,
            "description": " ".join(description_parts),
            "assignee_user_id": uid,
            "assignee_dept_id": dept_id,
            "deadline": deadline_text,
            "deadline_at": deadline_at,
            "priority": priority,
            "related_resources": {
                "implementation_steps": impl_list,
                "execution_type": "manual",
                "dispatch_status": "dispatched",
                "indicator_code": indicator_code,
            },
        })
    return tasks


def build_execution_tasks(plan: dict, dept_info: dict) -> list[dict]:
    """根据方案步骤和部门信息构建执行任务列表。"""
    tasks: list[dict] = []
    default_uid, default_dept_id = resolve_default_assignee(dept_info)

    for step in plan.get("steps", []):
        owner_dept = (step.get("owner_dept") or "").strip()
        assignee_user_id, assignee_dept_id = resolve_dept_assignee(owner_dept, dept_info)
        if assignee_user_id is None and default_uid is not None:
            assignee_user_id = default_uid
            assignee_dept_id = default_dept_id

        action = step.get("action", plan.get("plan_name", ""))
        data_ctx = step.get("data_context", "")
        desc_parts = [f"[{plan.get('plan_name', '')}]"]
        if data_ctx:
            desc_parts.append(f"【数据依据】{data_ctx}")
        desc_parts.append(action)
        impl = step.get("implementation_steps") or []
        impl_list = [str(x).strip() for x in impl if str(x).strip()][:30] if isinstance(impl, list) else []
        deadline_text, deadline_at = resolve_deadline_fields(step.get("timeline"))
        tasks.append({
            "task_name": action,
            "description": " ".join(desc_parts),
            "assignee_user_id": assignee_user_id,
            "assignee_dept_id": assignee_dept_id,
            "deadline": deadline_text,
            "deadline_at": deadline_at,
            "priority": plan.get("priority_level", "medium"),
            "related_resources": {
                "implementation_steps": impl_list,
                "execution_type": "manual",
                "dispatch_status": "dispatched",
            },
        })

    if not tasks:
        tasks.append({
            "task_name": plan.get("plan_name", "优化任务"),
            "description": plan.get("description", ""),
            "assignee_user_id": None,
            "assignee_dept_id": None,
            "deadline": None,
            "deadline_at": None,
            "priority": plan.get("priority_level", "medium"),
            "related_resources": {
                "implementation_steps": [],
                "execution_type": "manual",
                "dispatch_status": "dispatched",
            },
        })
    return tasks
