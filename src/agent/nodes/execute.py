"""执行推送节点 — 将采纳的方案转为执行任务，推送至业务系统。"""

from __future__ import annotations

import logging

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress

logger = logging.getLogger(__name__)


def _build_execution_tasks(plan: dict, dept_info: dict) -> list[dict]:
    """根据方案步骤和部门信息构建执行任务列表。"""
    tasks: list[dict] = []
    departments = dept_info.get("departments", [])

    dept_map: dict[str, dict] = {}
    for dept in departments:
        dept_name = dept.get("dept_name", "").lower()
        dept_map[dept_name] = dept
        for keyword in ["销售", "运营", "客服", "仓储", "管理", "市场", "售后"]:
            if keyword in dept_name:
                dept_map[keyword] = dept

    for step in plan.get("steps", []):
        owner_dept = step.get("owner_dept", "")
        matched_dept = None
        for keyword in ["销售", "运营", "客服", "仓储", "管理", "市场", "售后"]:
            if keyword in owner_dept:
                matched_dept = dept_map.get(keyword)
                break

        assignee_user_id = None
        assignee_dept_id = None
        if matched_dept:
            assignee_dept_id = matched_dept.get("dept_id")
            users = matched_dept.get("users", [])
            if users:
                assignee_user_id = users[0].get("userId", users[0].get("id"))

        tasks.append({
            "task_name": step.get("action", plan.get("plan_name", "")),
            "description": f"[{plan.get('plan_name', '')}] {step.get('action', '')}",
            "assignee_user_id": assignee_user_id,
            "assignee_dept_id": assignee_dept_id,
            "deadline": step.get("timeline"),
            "priority": plan.get("priority_level", "medium"),
            "related_resources": [],
        })

    if not tasks:
        tasks.append({
            "task_name": plan.get("plan_name", "优化任务"),
            "description": plan.get("description", ""),
            "assignee_user_id": None,
            "assignee_dept_id": None,
            "deadline": None,
            "priority": plan.get("priority_level", "medium"),
            "related_resources": [],
        })

    return tasks


async def execute_plans_node(state: DiagnosisState) -> dict:
    adopted_ids = state.get("adopted_plan_ids", [])
    all_plans = state.get("solution_plans", [])
    adopted_plans = [p for p in all_plans if p.get("plan_id") in adopted_ids]

    if not adopted_plans:
        emit_progress(state, "未选择任何方案，跳过执行")
        return {"exec_tasks": []}

    tenant_id = state["tenant_id"]
    store_id = state["store_id"]
    all_tasks: list[dict] = []

    dept_info = {}
    try:
        dept_info = await mcp_call("crm-server", "get_dept_structure", {
            "tenant_id": tenant_id,
            "store_id": store_id,
        })
    except Exception as e:
        logger.warning("获取部门架构失败: %s", e)

    for plan in adopted_plans:
        plan_name = plan.get("plan_name", "")
        emit_progress(state, f"正在创建方案「{plan_name}」的执行任务...")

        tasks = _build_execution_tasks(plan, dept_info)

        try:
            result = await mcp_call("task-server", "create_execution_tasks", {
                "tenant_id": tenant_id,
                "store_id": store_id,
                "plan_id": plan.get("plan_id", ""),
                "tasks": tasks,
            })
            all_tasks.extend(result.get("created_tasks", tasks))
        except Exception as e:
            logger.error("创建执行任务失败 [%s]: %s", plan_name, e)
            all_tasks.extend(tasks)

        for action in plan.get("auto_actions", []):
            action_type = action.get("type", "")
            config = action.get("config", {})
            try:
                if action_type == "coupon_campaign":
                    await mcp_call("task-server", "create_coupon_campaign", {
                        "tenant_id": tenant_id,
                        "store_id": store_id,
                        "campaign_config": config,
                    })
                    emit_progress(state, f"已自动创建优惠券活动: {config.get('coupon_name', '')}")
                elif action_type == "seckill_activity":
                    await mcp_call("task-server", "create_seckill_activity", {
                        "tenant_id": tenant_id,
                        "store_id": store_id,
                        "activity_config": config,
                    })
                    emit_progress(state, f"已自动创建秒杀活动")
            except Exception as e:
                logger.error("自动动作执行失败 [%s]: %s", action_type, e)

    emit_progress(state, f"共创建 {len(all_tasks)} 个执行任务")

    return {"exec_tasks": all_tasks}
