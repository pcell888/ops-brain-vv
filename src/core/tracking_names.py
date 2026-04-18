"""效果追踪名称相关工具函数。"""

from __future__ import annotations


def legacy_auto_solution_label(plan_id: str | None) -> str:
    """历史库内占位方案名：「方案」+ plan_id 前 8 位（与旧版 start_effect / 快照引导写入一致）。"""
    pid = str(plan_id or "").strip()
    return f"方案 {pid[:8]}" if pid else ""


def resolve_solution_name(
    tracking_data: dict | None,
    fallback_plan_name: str | None = None,
) -> str:
    """统一方案名称回退：solution_name -> plan_name -> fallback_plan_name -> plan_id 简称 -> 默认值。"""
    td = tracking_data or {}
    plan_id = str(td.get("plan_id") or "").strip()
    legacy_placeholder = legacy_auto_solution_label(plan_id)

    name = str(td.get("solution_name") or td.get("plan_name") or "").strip()
    fallback = str(fallback_plan_name or "").strip()
    # 旧占位名与 legacy 规则一致时，不应挡住执行侧解析到的真实方案名
    if name and plan_id and legacy_placeholder and name == legacy_placeholder and fallback:
        return fallback

    if name:
        return name

    if fallback:
        return fallback

    if plan_id:
        tail = plan_id[:16] if len(plan_id) > 16 else plan_id
        return tail or "效果追踪"
    return "效果追踪"
