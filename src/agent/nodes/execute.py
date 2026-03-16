"""执行推送节点 — 将采纳的方案转为执行任务，推送至业务系统；并按 5.2.3 规则补全异常指标对应动作。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.agent.state import DiagnosisState
from src.core.config import get_settings
from src.core.push_log_repo import save_push_log
from src.core.exec_task_repo import save_exec_tasks
from src.core.pending_review_repo import save_pending_review
from src.agent.tools import mcp_call, emit_progress
from src.core.indicator_push_rules import INDICATOR_PUSH_RULES

logger = logging.getLogger(__name__)

RULE_PLAN_ID = "rule_5.2.3"


def _dept_resolve(owner_dept: str, dept_info: dict) -> tuple[str | None, str | None]:
    """根据 owner_dept 关键词从 dept_info 解析 assignee_user_id, assignee_dept_id。"""
    departments = dept_info.get("departments", [])
    dept_map: dict[str, dict] = {}
    for dept in departments:
        dept_name = (dept.get("dept_name") or "").lower()
        dept_map[dept_name] = dept
        for keyword in ["销售", "运营", "客服", "仓储", "管理", "市场", "售后"]:
            if keyword in dept_name:
                dept_map[keyword] = dept
    matched = dept_map.get(owner_dept) or dept_map.get((owner_dept or "").lower())
    if not matched:
        for keyword in ["销售", "运营", "客服", "仓储", "管理", "市场", "售后"]:
            if owner_dept and keyword in owner_dept:
                matched = dept_map.get(keyword)
                break
    if not matched:
        return None, None
    users = matched.get("users", [])
    uid = users[0].get("userId", users[0].get("id")) if users else None
    return uid, matched.get("dept_id")


def _build_tasks_from_rule_specs(specs: list[dict], dept_info: dict) -> list[dict]:
    """从 5.2.3 规则任务规格列表构建 create_execution_tasks 所需的 tasks。"""
    tasks: list[dict] = []
    for s in specs:
        uid, dept_id = _dept_resolve(s.get("owner_dept", ""), dept_info)
        tasks.append({
            "task_name": s.get("task_name", "优化任务"),
            "description": s.get("task_name", ""),
            "assignee_user_id": uid,
            "assignee_dept_id": dept_id,
            "deadline": s.get("timeline"),
            "priority": "medium",
            "related_resources": [],
        })
    return tasks


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

    # 兜底：无部门数据时用第一个有人的部门作为未分配任务的默认负责人
    default_dept = dept_map.get("管理") or next(
        (d for d in departments if d.get("users")), None
    )
    default_uid = None
    default_dept_id = None
    if default_dept:
        default_dept_id = default_dept.get("dept_id")
        users = default_dept.get("users", [])
        if users:
            default_uid = users[0].get("userId", users[0].get("id"))

    for step in plan.get("steps", []):
        owner_dept = (step.get("owner_dept") or "").strip()
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
        if assignee_user_id is None and default_uid is not None:
            assignee_user_id = default_uid
            assignee_dept_id = default_dept_id

        action = step.get("action", plan.get("plan_name", ""))
        data_ctx = step.get("data_context", "")
        desc_parts = [f"[{plan.get('plan_name', '')}]"]
        if data_ctx:
            desc_parts.append(f"【数据依据】{data_ctx}")
        desc_parts.append(action)
        tasks.append({
            "task_name": action,
            "description": " ".join(desc_parts),
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


def _needs_approval(plan: dict) -> bool:
    """判断方案是否需要走审批流程：priority_level=high 且含自动动作（涉及资金操作）。"""
    if plan.get("priority_level") != "high":
        return False
    return bool(plan.get("auto_actions"))


async def _send_task_notifications(
    tenant_id: str, store_id: str, tasks: list[dict],
):
    """批量发送任务分配通知。"""
    notifiable = [t for t in tasks if t.get("assignee_user_id")]
    if not notifiable:
        return
    try:
        await mcp_call("notify-server", "send_task_assignment_notification", {
            "tenant_id": tenant_id,
            "store_id": store_id,
            "tasks": notifiable,
        })
    except Exception as e:
        logger.warning("任务分配通知推送失败: %s", e)


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

    # ── 5.2.3 按异常指标补全规定动作 ──
    anomalies = state.get("anomalies") or []
    rule_tasks: list[dict] = []
    seen_task_name: set[str] = set()
    for a in anomalies:
        ind = a.get("indicator_code")
        rule = INDICATOR_PUSH_RULES.get(ind) if ind else None
        if not rule or not rule.get("tasks"):
            continue
        for t in _build_tasks_from_rule_specs(rule["tasks"], dept_info):
            name = t.get("task_name", "")
            if name and name not in seen_task_name:
                seen_task_name.add(name)
                rule_tasks.append(t)
    if rule_tasks and get_settings().exec_push_rule_tasks:
        try:
            result = await mcp_call("task-server", "create_execution_tasks", {
                "tenant_id": tenant_id,
                "store_id": store_id,
                "plan_id": RULE_PLAN_ID,
                "tasks": rule_tasks,
            })
            created = result.get("created_tasks", rule_tasks) if isinstance(result, dict) else rule_tasks
            all_tasks.extend(created)
            emit_progress(state, f"已按规范推送 {len(rule_tasks)} 项指标动作任务")
            await _send_task_notifications(tenant_id, store_id, created)
            await save_exec_tasks(state.get("thread_id", ""), tenant_id, store_id, RULE_PLAN_ID, created)
            await save_push_log(
                state.get("thread_id", ""), tenant_id, store_id,
                "task", "exec_task",
                "5.2.3 指标动作任务",
                f"已推送 {len(rule_tasks)} 项指标动作任务",
                {"plan_id": RULE_PLAN_ID, "count": len(rule_tasks), "task_names": [t.get("task_name") for t in rule_tasks]},
            )
        except Exception as e:
            logger.warning("5.2.3 规则任务推送失败: %s", e)

    seen_coupon_ind: set[str] = set()
    seen_message_key: set[tuple[str, str]] = set()
    for a in anomalies:
        ind = a.get("indicator_code")
        rule = INDICATOR_PUSH_RULES.get(ind) if ind else None
        if not rule:
            continue
        if rule.get("coupon_campaign") and ind not in seen_coupon_ind:
            seen_coupon_ind.add(ind)
            cfg = dict(rule["coupon_campaign"])
            if not cfg.get("start_time"):
                now = datetime.utcnow()
                cfg["start_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                cfg["end_time"] = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            try:
                await mcp_call("task-server", "create_coupon_campaign", {
                    "tenant_id": tenant_id,
                    "store_id": store_id,
                    "campaign_config": cfg,
                })
                emit_progress(state, f"已创建规则优惠券: {cfg.get('coupon_name', '')}")
            except Exception as e:
                logger.warning("5.2.3 规则优惠券创建失败: %s", e)
        msg_cfg = rule.get("message")
        if msg_cfg:
            key = (ind or "", msg_cfg.get("type", ""))
            if key not in seen_message_key:
                seen_message_key.add(key)
                seg = msg_cfg.get("target_segment", "")
                title = msg_cfg.get("title", "系统通知")
                content = msg_cfg.get("content_tpl", "")
                try:
                    await mcp_call("notify-server", "send_customer_targeted_message", {
                        "tenant_id": tenant_id,
                        "store_id": store_id,
                        "target_segment": seg,
                        "title": title,
                        "content": content,
                        "message_type": msg_cfg.get("type", "ai_targeted"),
                    })
                    emit_progress(state, f"已向目标人群推送: {title}")
                except Exception as e:
                    logger.warning("5.2.3 规则定向消息推送失败: %s", e)

    # ── 逐方案执行：审批 / 任务创建 / 自动动作 ──
    admin_accounts = (state.get("store_profile") or {}).get("admin_account_ids", [])
    for plan in adopted_plans:
        plan_name = plan.get("plan_name", "")

        if _needs_approval(plan):
            emit_progress(state, f"方案「{plan_name}」需审批，正在发起审批流程...")
            approver_uid = None
            for dept in dept_info.get("departments", []):
                if "管理" in (dept.get("dept_name") or ""):
                    users = dept.get("users", [])
                    if users:
                        approver_uid = users[0].get("userId", users[0].get("id"))
                    break
            if approver_uid:
                try:
                    await mcp_call("task-server", "create_approval_flow", {
                        "tenant_id": tenant_id,
                        "store_id": store_id,
                        "plan_id": plan.get("plan_id", ""),
                        "title": f"AI诊断方案审批：{plan_name}",
                        "content": plan.get("description", ""),
                        "approver_user_id": approver_uid,
                    })
                    emit_progress(state, f"方案「{plan_name}」审批已发起")
                except Exception as e:
                    logger.warning("审批流程创建失败 [%s]: %s", plan_name, e)

        emit_progress(state, f"正在创建方案「{plan_name}」的执行任务...")
        tasks = _build_execution_tasks(plan, dept_info)

        try:
            result = await mcp_call("task-server", "create_execution_tasks", {
                "tenant_id": tenant_id,
                "store_id": store_id,
                "plan_id": plan.get("plan_id", ""),
                "tasks": tasks,
            })
            created = result.get("created_tasks", tasks) if isinstance(result, dict) else tasks
            all_tasks.extend(created)
            await _send_task_notifications(tenant_id, store_id, created)
            await save_exec_tasks(state.get("thread_id", ""), tenant_id, store_id, plan.get("plan_id", ""), created)
            await save_push_log(
                state.get("thread_id", ""), tenant_id, store_id,
                "task", "exec_task",
                f"方案执行任务：{plan_name}",
                f"已创建 {len(created)} 个执行任务",
                {"plan_id": plan.get("plan_id"), "plan_name": plan_name, "count": len(created), "task_names": [t.get("task_name") for t in created]},
            )
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

    settings = get_settings()
    delay_days = settings.effect_track_delay_days
    if delay_days > 0:
        thread_id = state.get("thread_id", "")
        due_date = (datetime.now() + timedelta(days=delay_days)).date()
        try:
            await save_pending_review(thread_id, tenant_id, store_id, due_date)
            emit_progress(state, f"效果追踪已调度，将于 {due_date} 自动执行复盘")
        except Exception as e:
            logger.warning("保存待复盘调度失败: %s", e)

    return {"exec_tasks": all_tasks}
