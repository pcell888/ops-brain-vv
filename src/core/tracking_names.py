"""效果追踪名称相关工具函数。"""

from __future__ import annotations


def legacy_auto_solution_label(plan_id: str | None) -> str:
    """历史库内占位方案名：「方案」+ plan_id 前 8 位（与旧版 start_effect / 快照引导写入一致）。"""
    pid = str(plan_id or "").strip()
    return f"方案 {pid[:8]}" if pid else ""


def _is_generic_solution_name(v: object, plan_id: str | None = None) -> bool:
    name = str(v or "").strip()
    if (not name) or name.startswith("效果追踪"):
        return True
    pid = str(plan_id or "").strip()
    legacy = legacy_auto_solution_label(pid)
    if legacy and name == legacy:
        return True
    return False


def resolve_solution_name(
    tracking_data: dict | None,
    fallback_plan_name: str | None = None,
) -> str:
    """统一方案名称回退：solution_name -> plan_name -> fallback_plan_name -> plan_id 简称 -> 默认值。"""
    td = tracking_data or {}
    plan_id = str(td.get("plan_id") or "").strip()
    legacy_placeholder = legacy_auto_solution_label(plan_id)
    fallback = str(fallback_plan_name or "").strip()

    name = ""
    for key in ("solution_name", "plan_name"):
        c = str(td.get(key) or "").strip()
        if not c:
            continue
        # 旧占位名与 legacy 规则一致时，不应挡住执行侧解析到的真实方案名
        if plan_id and legacy_placeholder and c == legacy_placeholder and fallback:
            return fallback
        if not _is_generic_solution_name(c, plan_id):
            name = c
            break

    if name:
        return name

    if fallback:
        return fallback

    if plan_id:
        tail = plan_id[:16] if len(plan_id) > 16 else plan_id
        return tail or "效果追踪"
    return "效果追踪"
