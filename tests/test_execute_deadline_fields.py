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
