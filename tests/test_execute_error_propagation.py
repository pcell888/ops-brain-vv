from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.agent.nodes import execute


def _base_state() -> dict:
    return {
        "thread_id": "th-1",
        "tenant_id": "tenant-1",
        "store_id": "store-1",
        "adopted_plan_ids": ["p-1"],
        "solution_plans": [
            {
                "plan_id": "p-1",
                "plan_name": "执行方案",
                "priority_level": "medium",
                "steps": [
                    {
                        "action": "电话回访",
                        "owner_dept": "销售部",
                        "timeline": "3天内",
                        "data_context": "最近成交下降",
                        "implementation_steps": ["联系高意向客户"],
                    }
                ],
                "auto_actions": [],
            }
        ],
        "store_profile": {"admin_account_ids": []},
        "anomalies": [],
    }


@pytest.mark.asyncio
async def test_execute_plans_node_raise_when_dept_query_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _base_state()

    async def fake_mcp_call(server_name: str, tool_name: str, arguments: dict) -> dict:
        raise RuntimeError("部门查询失败")

    monkeypatch.setattr(execute, "mcp_call", fake_mcp_call)
    monkeypatch.setattr(
        execute,
        "get_settings",
        lambda: SimpleNamespace(exec_push_rule_tasks=False, effect_track_delay_days=0),
    )

    with pytest.raises(RuntimeError, match="部门查询失败"):
        await execute.execute_plans_node(state)


@pytest.mark.asyncio
async def test_execute_plans_node_raise_when_create_tasks_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _base_state()

    async def fake_mcp_call(server_name: str, tool_name: str, arguments: dict) -> dict:
        if server_name == "crm-server" and tool_name == "get_dept_structure":
            return {
                "departments": [
                    {"dept_id": "d-1", "dept_name": "销售部", "users": [{"userId": 1001}]}
                ]
            }
        if server_name == "task-server" and tool_name == "create_execution_tasks":
            raise RuntimeError("创建任务失败")
        return {}

    monkeypatch.setattr(execute, "mcp_call", fake_mcp_call)
    monkeypatch.setattr(
        execute,
        "get_settings",
        lambda: SimpleNamespace(exec_push_rule_tasks=False, effect_track_delay_days=0),
    )

    with pytest.raises(RuntimeError, match="创建任务失败"):
        await execute.execute_plans_node(state)
