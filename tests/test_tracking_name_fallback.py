"""效果追踪方案名称回退规则测试。"""

from __future__ import annotations

from src.core.tracking_names import resolve_solution_name


def test_resolve_solution_name_prefers_solution_name() -> None:
    data = {"solution_name": "门店转化率提升方案", "plan_name": "旧名称", "plan_id": "plan_12345678"}
    assert resolve_solution_name(data) == "门店转化率提升方案"


def test_resolve_solution_name_falls_back_to_plan_name() -> None:
    data = {"solution_name": "", "plan_name": "直播投放优化", "plan_id": "plan_abcdef12"}
    assert resolve_solution_name(data) == "直播投放优化"


def test_resolve_solution_name_falls_back_to_plan_id() -> None:
    data = {"solution_name": "", "plan_name": "", "plan_id": "plan_1234567890abcdef"}
    assert resolve_solution_name(data) == "方案 plan_123"


def test_resolve_solution_name_falls_back_to_knowledge_plan_name() -> None:
    data = {"solution_name": "", "plan_name": "", "plan_id": ""}
    assert resolve_solution_name(data, fallback_plan_name="高客单提升专项方案") == "高客单提升专项方案"


def test_resolve_solution_name_falls_back_to_default() -> None:
    assert resolve_solution_name({}) == "效果追踪"
