"""执行推送节点 — 将采纳方案转为执行任务并推送。5.2.3 规范任务默认由方案生成阶段融入，仅当 exec_push_rule_tasks=True 时保留旧版双轨补推。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.agent.state import DiagnosisState
from src.core.config import CN_TZ, get_settings
from src.core.dept_resolver import resolve_default_assignee
from src.core.push_log_repo import save_push_log
from src.core.exec_task_repo import save_exec_tasks, update_task_status
from src.core.pending_review_repo import save_pending_review
from src.agent.tools import mcp_call, emit_progress
from src.core.indicator_push_rules import INDICATOR_PUSH_RULES
from src.agent.nodes.rule_task_builder import (
    build_tasks_from_rule_specs,
    build_execution_tasks,
    resolve_review_due_at,
)

logger = logging.getLogger(__name__)

RULE_PLAN_ID = "rule_5.2.3"


def _merge_task_ids(local_tasks: list[dict], created: list[dict] | None) -> list[dict]:
    if not created or len(created) != len(local_tasks):
        return [dict(t) for t in local_tasks]
    out: list[dict] = []
    for loc, cr in zip(local_tasks, created):
        m = dict(loc)
        if isinstance(cr, dict) and cr.get("task_id"):
            m["task_id"] = cr["task_id"]
        out.append(m)
    return out


def _needs_approval(plan: dict) -> bool:
    if plan.get("priority_level") != "high":
        return False
    return bool(plan.get("auto_actions"))


async def _send_task_notifications(tenant_id: str, store_id: str, tasks: list[dict]):
    notifiable = [t for t in tasks if t.get("assignee_user_id")]
    if not notifiable:
        return
    await mcp_call("notify-server", "send_task_assignment_notification", {"tenant_id": tenant_id, "store_id": store_id, "tasks": notifiable})


async def execute_plans_node(state: DiagnosisState) -> dict:
    pending_id = state.get("pending_adopt_plan_id")
    if pending_id:
        adopted_ids = [pending_id]
    else:
        adopted_ids = (state.get("adopted_plan_ids") or [])[:1]
    all_plans = state.get("solution_plans", [])
    adopted_plans = [p for p in all_plans if p.get("plan_id") in adopted_ids]

    if not adopted_plans:
        emit_progress(state, "未选择任何方案，跳过执行")
        return {"exec_tasks": []}

    tenant_id = state["tenant_id"]
    store_id = state["store_id"]
    all_tasks: list[dict] = []

    dept_info = await mcp_call("crm-server", "get_dept_structure", {"tenant_id": tenant_id, "store_id": store_id})

    # ── 5.2.3 按异常指标补全规定动作 ──
    anomalies = state.get("anomalies") or []
    rule_message_specs = [
        (a.get("indicator_code"), (INDICATOR_PUSH_RULES.get(a.get("indicator_code")) or {}).get("message"))
        for a in anomalies if a.get("indicator_code")
    ]
    matched_message_rules = [ind for ind, msg in rule_message_specs if msg]
    exec_push_enabled = get_settings().exec_push_rule_tasks
    logger.info(
        "执行阶段规则推送开关: exec_push_rule_tasks=%s, anomalies=%d, matched_message_rules=%d, indicators=%s",
        exec_push_enabled, len(anomalies), len(matched_message_rules), matched_message_rules,
    )
    if matched_message_rules and not exec_push_enabled:
        logger.info("已跳过定向人群推送（exec_push_rule_tasks=false）: indicators=%s", matched_message_rules)

    rule_tasks: list[dict] = []
    seen_task_name: set[str] = set()
    for a in anomalies:
        ind = a.get("indicator_code")
        rule = INDICATOR_PUSH_RULES.get(ind) if ind else None
        if not rule or not rule.get("tasks"):
            continue
        for t in build_tasks_from_rule_specs(rule["tasks"], dept_info, ind):
            name = t.get("task_name", "")
            if name and name not in seen_task_name:
                seen_task_name.add(name)
                rule_tasks.append(t)

    if rule_tasks and exec_push_enabled:
        try:
            result = await mcp_call("task-server", "create_execution_tasks", {"tenant_id": tenant_id, "store_id": store_id, "plan_id": RULE_PLAN_ID, "tasks": rule_tasks})
            created = result.get("created_tasks", rule_tasks) if isinstance(result, dict) else rule_tasks
            all_tasks.extend(created)
            emit_progress(state, f"已按规范推送 {len(rule_tasks)} 项指标动作任务")
            await _send_task_notifications(tenant_id, store_id, created)
            to_save = _merge_task_ids(rule_tasks, result.get("created_tasks") if isinstance(result, dict) else None)
            await save_exec_tasks(state.get("thread_id", ""), tenant_id, store_id, RULE_PLAN_ID, to_save)
            await save_push_log(state.get("thread_id", ""), tenant_id, store_id, "task", "exec_task", "5.2.3 指标动作任务", f"已推送 {len(rule_tasks)} 项指标动作任务", {"plan_id": RULE_PLAN_ID, "count": len(rule_tasks), "task_names": [t.get("task_name") for t in rule_tasks]})
        except Exception as e:
            emit_progress(state, f"指标动作任务派发失败: {e}", level="warning")
            logger.warning("指标动作任务派发失败: %s", e)

    if exec_push_enabled:
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
                    now = datetime.now(CN_TZ)
                    cfg["start_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    cfg["end_time"] = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                emit_progress(state, f"已跳过规则优惠券创建: {cfg.get('coupon_name', '')}")
                logger.info("已屏蔽 create_coupon_campaign 调用（规则动作）: tenant=%s store=%s", tenant_id, store_id)
            msg_cfg = rule.get("message")
            if msg_cfg:
                key = (ind or "", msg_cfg.get("type", ""))
                if key not in seen_message_key:
                    seen_message_key.add(key)
                    await mcp_call("notify-server", "send_customer_targeted_message", {"tenant_id": tenant_id, "store_id": store_id, "target_segment": msg_cfg.get("target_segment", ""), "title": msg_cfg.get("title", "系统通知"), "content": msg_cfg.get("content_tpl", ""), "message_type": msg_cfg.get("type", "ai_targeted")})
                    emit_progress(state, f"已向目标人群推送: {msg_cfg.get('title', '系统通知')}")

    # ── 逐方案执行：审批 / 任务创建 / 自动动作 ──
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
                await mcp_call("task-server", "create_approval_flow", {"tenant_id": tenant_id, "store_id": store_id, "plan_id": plan.get("plan_id", ""), "title": f"AI诊断方案审批：{plan_name}", "content": plan.get("description", ""), "approver_user_id": approver_uid})
                emit_progress(state, f"方案「{plan_name}」审批已发起")

        emit_progress(state, f"正在创建方案「{plan_name}」的执行任务...")
        tasks = build_execution_tasks(plan, dept_info)

        saved_task_ids = await save_exec_tasks(state.get("thread_id", ""), tenant_id, store_id, plan.get("plan_id", ""), tasks)

        try:
            result = await mcp_call("task-server", "create_execution_tasks", {"tenant_id": tenant_id, "store_id": store_id, "plan_id": plan.get("plan_id", ""), "tasks": tasks})
            created = result.get("created_tasks", tasks) if isinstance(result, dict) else tasks
            all_tasks.extend(created)
            await update_task_status(saved_task_ids, "running")
            await _send_task_notifications(tenant_id, store_id, created)
            await save_push_log(state.get("thread_id", ""), tenant_id, store_id, "task", "exec_task", f"方案执行任务：{plan_name}", f"已创建 {len(created)} 个执行任务", {"plan_id": plan.get("plan_id"), "plan_name": plan_name, "count": len(created), "task_names": [t.get("task_name") for t in created]})
        except Exception as e:
            await update_task_status(saved_task_ids, "failed")
            emit_progress(state, f"方案「{plan_name}」任务派发失败: {str(e)}")
            logger.warning("任务派发失败: %s", e)
            continue

        for action in plan.get("auto_actions", []):
            action_type = action.get("type", "")
            config = action.get("config", {})
            if action_type == "coupon_campaign":
                emit_progress(state, f"已跳过自动优惠券创建: {config.get('coupon_name', '')}")
                logger.info("已屏蔽 create_coupon_campaign 调用（自动动作）: tenant=%s store=%s", tenant_id, store_id)
            elif action_type == "seckill_activity":
                await mcp_call("task-server", "create_seckill_activity", {"tenant_id": tenant_id, "store_id": store_id, "activity_config": config})
                emit_progress(state, "已自动创建秒杀活动")

    emit_progress(state, f"共创建 {len(all_tasks)} 个执行任务")

    settings = get_settings()
    delay_minutes = settings.effect_track_delay_minutes
    if delay_minutes > 0:
        thread_id = state.get("thread_id", "")
        due_at = resolve_review_due_at(all_tasks, delay_minutes)
        try:
            await save_pending_review(thread_id, tenant_id, store_id, due_at)
            emit_progress(
                state,
                f"效果追踪已调度，将于 {due_at.strftime('%Y-%m-%d %H:%M')} 自动执行复盘",
            )
        except Exception as e:
            logger.warning("保存待复盘调度失败: %s", e)

    result_state: dict = {"exec_tasks": all_tasks}
    if pending_id:
        result_state["adopted_plan_ids"] = [pending_id]
        result_state["pending_adopt_plan_id"] = None
    return result_state
