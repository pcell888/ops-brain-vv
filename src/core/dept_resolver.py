"""部门关键词匹配与人员分配（全局唯一实现）。"""

from __future__ import annotations

DEPT_KEYWORDS: tuple[str, ...] = ("销售", "运营", "客服", "仓储", "管理", "市场", "售后")


def build_dept_map(dept_info: dict) -> dict[str, dict]:
    """从 dept_info 构建 keyword→dept 映射。"""
    departments = dept_info.get("departments", [])
    dept_map: dict[str, dict] = {}
    for dept in departments:
        dept_name = (dept.get("dept_name") or "").lower()
        dept_map[dept_name] = dept
        for kw in DEPT_KEYWORDS:
            if kw in dept_name:
                dept_map[kw] = dept
    return dept_map


def _first_user_id(dept: dict) -> str | None:
    users = dept.get("users", [])
    if not users:
        return None
    return users[0].get("userId", users[0].get("id"))


def resolve_default_assignee(dept_info: dict) -> tuple[str | None, str | None]:
    """返回 (default_user_id, default_dept_id)，优先管理部门。"""
    dept_map = build_dept_map(dept_info)
    departments = dept_info.get("departments", [])
    default_dept = dept_map.get("管理") or next(
        (d for d in departments if d.get("users")), None
    )
    if not default_dept:
        return None, None
    return _first_user_id(default_dept), default_dept.get("dept_id")


def resolve_dept_assignee(
    owner_dept: str,
    dept_info: dict,
) -> tuple[str | None, str | None]:
    """根据 owner_dept 关键词返回 (user_id, dept_id)，无匹配返回 (None, None)。"""
    dept_map = build_dept_map(dept_info)
    matched = dept_map.get(owner_dept) or dept_map.get((owner_dept or "").lower())
    if not matched:
        for kw in DEPT_KEYWORDS:
            if owner_dept and kw in owner_dept:
                matched = dept_map.get(kw)
                break
    if not matched:
        return None, None
    return _first_user_id(matched), matched.get("dept_id")


def resolve_dept_assignee_with_fallback(
    owner_dept: str,
    dept_info: dict,
) -> tuple[str | None, str | None]:
    """先精确匹配，失败则回退到默认部门。"""
    uid, did = resolve_dept_assignee(owner_dept, dept_info)
    if uid is not None:
        return uid, did
    return resolve_default_assignee(dept_info)


def dept_keyword_match(rule_dept: str, step_dept: str) -> bool:
    """判断两个部门名是否按关键词匹配（用于规则保底任务覆盖检测）。"""
    a, b = (rule_dept or "").strip(), (step_dept or "").strip()
    if not a or not b:
        return False
    for kw in DEPT_KEYWORDS:
        if kw in a and kw in b:
            return True
    return a == b
