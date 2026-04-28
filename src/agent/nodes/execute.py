"""执行推送节点 — 将采纳方案转为执行任务并推送。5.2.3 规范任务默认由方案生成阶段融入，仅当 exec_push_rule_tasks=True 时保留旧版双轨补推。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.agent.state import DiagnosisState
from src.core.config import CN_TZ, get_settings
from src.repositories.push_log import save_push_log
from src.repositories.exec_task import patch_related_resources, save_exec_tasks, update_task_status
from src.repositories.pending_review import save_pending_review
from src.repositories.tenant_registry import get_tenant_row
from src.agent.progress import emit_progress
from src.biz.client import tenant_client
from src.core.indicator_push_rules import INDICATOR_PUSH_RULES
from src.agent.nodes.rule_task_builder import (
    build_execution_tasks,
    build_tasks_from_rule_specs,
    resolve_review_due_at,
)

logger = logging.getLogger(__name__)

RULE_PLAN_ID = "rule_5.2.3"


async def _send_task_notifications(tenant_id: str, store_id: str, tasks: list[dict], thread_id: str = ""):
    notifiable = [t for t in tasks if t.get("assignee_user_id")]
    if not notifiable:
        return
    tc = tenant_client(tenant_id)
    result = await tc.send_task_assignment_notification(tenant_id=tenant_id, store_id=store_id, tasks=notifiable)
    task_names = [t.get("task_name", "") for t in notifiable]
    await save_push_log(
        thread_id,
        tenant_id,
        store_id,
        "message",
        "ai_task_assignment",
        f"新任务分配通知（{len(notifiable)} 条）",
        f"已向执行人推送任务分配通知：{'、'.join(task_names[:5])}",
        {"task_count": len(notifiable), "task_names": task_names, "sent_count": result.get("sent_count", 0)},
    )


async def _batch_push_tasks(
    tenant_id: str,
    store_id: str,
    plan_id: str,
    tasks: list[dict],
    saved_task_ids: list[str],
) -> tuple[list[dict], list[tuple[str, str]]]:
    """逐条调用企服 batch-create（每次 1 条）。成功写 dispatched，失败写 failed + dispatch_error。"""
    created_merged: list[dict] = []
    failures: list[tuple[str, str]] = []
    for idx, t in enumerate(tasks):
        tid = saved_task_ids[idx]
        loc = dict(t)
        loc["task_id"] = tid
        name = str(loc.get("task_name") or tid)
        try:
            tc = tenant_client(tenant_id)
            result = await tc.create_execution_tasks(
                tenant_id=tenant_id, store_id=store_id, plan_id=plan_id, tasks=[loc]
            )
            cr_list = result.get("created_tasks", []) if isinstance(result, dict) else []
            cr0 = cr_list[0] if cr_list and isinstance(cr_list[0], dict) else None
            merged = dict(loc)
            if isinstance(cr0, dict) and cr0.get("task_id"):
                merged["task_id"] = cr0["task_id"]
            created_merged.append(merged)
            await patch_related_resources(tid, {"dispatch_status": "dispatched"})
            await update_task_status([tid], "running")
        except Exception as e:
            err_msg = str(e)
            failures.append((name, err_msg))
            await patch_related_resources(
                tid,
                {"dispatch_status": "failed", "dispatch_error": err_msg[:500]},
            )
            await update_task_status([tid], "failed")
            logger.warning("任务派发失败 task_id=%s name=%s: %s", tid, name, err_msg)
    return created_merged, failures


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

    tenant_row = await get_tenant_row(tenant_id)
    registry_user_id = (tenant_row or {}).get("user_id")
    registry_user_name = (tenant_row or {}).get("user_name")

    tc = tenant_client(tenant_id)

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
        for t in build_tasks_from_rule_specs(
            rule["tasks"],
            {},
            ind,
            override_assignee_user_id=str(registry_user_id) if registry_user_id else None,
            override_assignee_user_name=registry_user_name if registry_user_id else None,
        ):
            name = t.get("task_name", "")
            if name and name not in seen_task_name:
                seen_task_name.add(name)
                rule_tasks.append(t)

    if rule_tasks and exec_push_enabled:
        thread_id = state.get("thread_id", "")
        rule_created: list[dict] = []
        rule_failed_names: list[str] = []
        for rt in rule_tasks:
            saved_ids = await save_exec_tasks(thread_id, tenant_id, store_id, RULE_PLAN_ID, [rt])
            merged, fails = await _batch_push_tasks(
                tenant_id, store_id, RULE_PLAN_ID, [rt], saved_ids
            )
            rule_created.extend(merged)
            rule_failed_names.extend([n for n, _ in fails])
        if rule_created:
            emit_progress(state, f"已按规范推送 {len(rule_created)} 项指标动作任务")
            await _send_task_notifications(tenant_id, store_id, rule_created, thread_id)
            await save_push_log(
                thread_id,
                tenant_id,
                store_id,
                "task",
                "exec_task",
                "5.2.3 指标动作任务",
                f"已推送 {len(rule_created)} 项指标动作任务",
                {
                    "plan_id": RULE_PLAN_ID,
                    "count": len(rule_created),
                    "task_names": [t.get("task_name") for t in rule_created],
                },
            )
        if rule_failed_names:
            preview = "、".join(rule_failed_names[:5])
            emit_progress(
                state,
                f"指标动作任务 {len(rule_failed_names)} 条派发失败：{preview}",
                level="warning",
            )
            logger.warning("指标动作任务部分派发失败: %s", rule_failed_names)
        all_tasks.extend(rule_created)

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
                    await tc.send_customer_targeted_message(tenant_id=tenant_id, store_id=store_id, target_segment=msg_cfg.get("target_segment", ""), title=msg_cfg.get("title", "系统通知"), content=msg_cfg.get("content_tpl", ""), message_type=msg_cfg.get("type", "ai_targeted"))
                    emit_progress(state, f"已向目标人群推送: {msg_cfg.get('title', '系统通知')}")
                    await save_push_log(
                        state.get("thread_id", ""),
                        tenant_id,
                        store_id,
                        "message",
                        msg_cfg.get("type", "ai_targeted"),
                        msg_cfg.get("title", "系统通知"),
                        msg_cfg.get("content_tpl", ""),
                        {"indicator": ind, "target_segment": msg_cfg.get("target_segment", "")},
                    )

    # ── 逐方案执行：审批 / 任务创建 / 自动动作 ──
    for plan in adopted_plans:
        plan_name = plan.get("plan_name", "")

        emit_progress(state, f"正在创建方案「{plan_name}」的执行任务...")
        tasks = build_execution_tasks(
            plan,
            override_assignee_user_id=str(registry_user_id) if registry_user_id else None,
            override_assignee_user_name=registry_user_name if registry_user_id else None,
        )

        saved_task_ids = await save_exec_tasks(state.get("thread_id", ""), tenant_id, store_id, plan.get("plan_id", ""), tasks)

        created, push_failures = await _batch_push_tasks(
            tenant_id,
            store_id,
            plan.get("plan_id", ""),
            tasks,
            saved_task_ids,
        )
        all_tasks.extend(created)
        if created:
            await _send_task_notifications(tenant_id, store_id, created, state.get("thread_id", ""))
            await save_push_log(
                state.get("thread_id", ""),
                tenant_id,
                store_id,
                "task",
                "exec_task",
                f"方案执行任务：{plan_name}",
                f"已创建 {len(created)} 个执行任务",
                {
                    "plan_id": plan.get("plan_id"),
                    "plan_name": plan_name,
                    "count": len(created),
                    "task_names": [t.get("task_name") for t in created],
                },
            )
        if push_failures:
            preview = "、".join(n for n, _ in push_failures[:5])
            emit_progress(
                state,
                f"方案「{plan_name}」{len(push_failures)} 个任务派发失败：{preview}",
                level="warning",
            )
            for n, msg in push_failures:
                logger.warning("任务派发失败 name=%s: %s", n, msg)
        if not created:
            continue

        for action in plan.get("auto_actions", []):
            action_type = action.get("type", "")
            config = action.get("config", {})
            if action_type == "coupon_campaign":
                emit_progress(state, f"已跳过自动优惠券创建: {config.get('coupon_name', '')}")
                logger.info("已屏蔽 create_coupon_campaign 调用（自动动作）: tenant=%s store=%s", tenant_id, store_id)
            elif action_type == "seckill_activity":
                await tc.create_seckill_activity(tenant_id=tenant_id, store_id=store_id, activity_config=config)
                emit_progress(state, "已自动创建秒杀活动")

    emit_progress(state, f"共创建 {len(all_tasks)} 个执行任务")

    settings = get_settings()
    delay_days = float(settings.effect_track_delay_days)
    if delay_days > 0:
        thread_id = state.get("thread_id", "")
        due_at = resolve_review_due_at(all_tasks, delay_days)
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
