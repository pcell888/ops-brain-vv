from __future__ import annotations

from datetime import datetime

from src.agent.nodes import execute


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 26, 10, 0, 0, tzinfo=tz)


def test_resolve_deadline_fields_relative_days(monkeypatch):
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    deadline, deadline_at = execute._resolve_deadline_fields("5天内")
    assert deadline == "5天内"
    assert deadline_at == "2026-03-31T10:00:00+08:00"


def test_resolve_deadline_fields_relative_hours(monkeypatch):
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    deadline, deadline_at = execute._resolve_deadline_fields("24 小时内")
    assert deadline == "24小时内"
    assert deadline_at == "2026-03-27T10:00:00+08:00"


def test_build_execution_tasks_sets_deadline_at(monkeypatch):
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    plan = {
        "plan_name": "提升转化",
        "priority_level": "medium",
        "steps": [
            {
                "action": "回访客户",
                "owner_dept": "销售部",
                "timeline": "5天内",
                "data_context": "线索转化偏低",
                "implementation_steps": ["联系高意向客户"],
            }
        ],
    }
    dept_info = {
        "departments": [
            {"dept_id": "2", "dept_name": "销售部", "users": [{"userId": 101}]},
        ]
    }
    tasks = execute._build_execution_tasks(plan, dept_info)
    assert len(tasks) == 1
    assert tasks[0]["deadline"] == "5天内"
    assert tasks[0]["deadline_at"] == "2026-03-31T10:00:00+08:00"


def test_build_tasks_from_rule_specs_fallback_to_default_assignee(monkeypatch):
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    specs = [
        {
            "task_name": "售后服务优化",
            "owner_dept": "售后",
            "timeline": "3天内",
            "implementation_steps": [],
        }
    ]
    dept_info = {
        "departments": [
            {"dept_id": "2", "dept_name": "销售部", "users": [{"userId": 101}]},
            {"dept_id": "3", "dept_name": "运营部", "users": [{"userId": 102}]},
        ]
    }

    tasks = execute._build_tasks_from_rule_specs(specs, dept_info, None)

    assert len(tasks) == 1
    assert tasks[0]["assignee_user_id"] == 101
    assert tasks[0]["assignee_dept_id"] == "2"


def test_build_tasks_from_rule_specs_prioritize_management_dept(monkeypatch):
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    specs = [
        {
            "task_name": "仓储发货流程优化",
            "owner_dept": "仓储",
            "timeline": "5天内",
            "implementation_steps": [],
        }
    ]
    dept_info = {
        "departments": [
            {"dept_id": "2", "dept_name": "销售部", "users": [{"userId": 101}]},
            {"dept_id": "9", "dept_name": "管理部", "users": [{"userId": 900}]},
            {"dept_id": "3", "dept_name": "运营部", "users": [{"userId": 102}]},
        ]
    }

    tasks = execute._build_tasks_from_rule_specs(specs, dept_info, None)

    assert len(tasks) == 1
    assert tasks[0]["assignee_user_id"] == 900
    assert tasks[0]["assignee_dept_id"] == "9"


def test_build_tasks_from_rule_specs_enriched_description(monkeypatch):
    """测试任务描述丰富功能：包含异常指标和关键步骤。"""
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    specs = [
        {
            "task_name": "退款原因分析与商品质量改进",
            "owner_dept": "运营",
            "timeline": "5天内",
            "implementation_steps": [
                "导出近30天退款单及原因标签分布",
                "对 TOP SKU 做质量/描述一致性核查",
                "形成改进清单并对接采购/质检闭环",
            ],
        }
    ]
    dept_info = {
        "departments": [
            {"dept_id": "3", "dept_name": "运营部", "users": [{"userId": 102}]},
        ]
    }

    tasks = execute._build_tasks_from_rule_specs(specs, dept_info, "refund_rate")

    assert len(tasks) == 1
    task = tasks[0]
    assert task["task_name"] == "退款原因分析与商品质量改进"
    assert "[refund_rate异常]" in task["description"]
    assert "关键步骤：" in task["description"]
    assert "导出近30天退款单及原因标签分布" in task["description"]
    assert task["priority"] == "high"
    assert task["related_resources"]["indicator_code"] == "refund_rate"


def test_build_tasks_from_rule_specs_dynamic_priority(monkeypatch):
    """测试动态优先级功能。"""
    monkeypatch.setattr(execute, "datetime", _FixedDateTime)
    specs = [
        {
            "task_name": "线索跟进优化",
            "owner_dept": "销售",
            "timeline": "24小时内",
            "implementation_steps": ["导出近7日新线索及负责人清单"],
        }
    ]
    dept_info = {
        "departments": [
            {"dept_id": "2", "dept_name": "销售部", "users": [{"userId": 101}]},
        ]
    }

    tasks = execute._build_tasks_from_rule_specs(specs, dept_info, "lead_conversion_rate")

    assert len(tasks) == 1
    assert tasks[0]["priority"] == "medium"
    assert "[lead_conversion_rate异常]" in tasks[0]["description"]
