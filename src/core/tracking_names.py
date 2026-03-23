"""效果追踪名称相关工具函数。"""

from __future__ import annotations


def resolve_solution_name(
    tracking_data: dict | None,
    fallback_plan_name: str | None = None,
) -> str:
    """统一方案名称回退：solution_name -> plan_name -> fallback_plan_name -> plan_id 简称 -> 默认值。"""
    td = tracking_data or {}
    name = str(td.get("solution_name") or td.get("plan_name") or "").strip()
    if name:
        return name

    fallback = str(fallback_plan_name or "").strip()
    if fallback:
        return fallback

    plan_id = str(td.get("plan_id") or "").strip()
    if plan_id:
        return f"方案 {plan_id[:8]}"
    return "效果追踪"
