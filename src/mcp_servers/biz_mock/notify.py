"""消息通知 — 与 biz/notify.py 同名、同签名、同 register；进程内模拟。"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.biz_mock import task_message_coupon
from src.mcp_servers.biz_scope import effective_store_id_for_biz

logger = logging.getLogger(__name__)


async def send_diagnosis_report_notification(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
    report_summary: dict,
) -> dict:
    _ = store_id
    logger.info(
        "Tool called: send_diagnosis_report_notification tenant=%s store=%s admin_count=%d",
        tenant_id,
        store_id,
        len(admin_account_ids),
    )
    health_score = report_summary.get("health_score", 0)
    anomaly_count = report_summary.get("anomaly_count", 0)
    top_anomaly = report_summary.get("top_anomaly", "")
    notify_type = report_summary.get("notification_type", "ai_diagnosis_report")
    diagnosis_time = report_summary.get("diagnosis_time", "")
    analysis_period = report_summary.get("analysis_period_days", 30)
    is_weekly = notify_type == "ai_weekly_digest"
    title = f"{'【周度】' if is_weekly else ''}AI诊断报告已生成 — 健康度 {health_score:.1f}分"
    content = f"诊断时间: {diagnosis_time} | 近{analysis_period}天 | 共发现 {anomaly_count} 项异常指标。"
    if top_anomaly:
        content += f"最突出问题：{top_anomaly}。"
    content += "详情请到APP/后台查看"
    messages = [
        {
            "accountId": aid,
            "title": title,
            "content": content,
            "type": notify_type,
            "jumpUrl": report_summary.get("report_url", ""),
        }
        for aid in admin_account_ids
    ]
    if not messages:
        return {"sent_count": 0, "status": "no_admin"}
    data = task_message_coupon.message_batch_create({"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


async def send_task_reminder(
    tenant_id: str,
    user_id: int,
    account_id: str,
    task_id: str,
    reminder_type: str,
    message: str,
) -> dict:
    _ = user_id
    logger.info("Tool called: send_task_reminder tenant=%s task_id=%s type=%s", tenant_id, task_id, reminder_type)
    type_labels = {
        "overdue": "任务超期提醒",
        "approaching_deadline": "任务即将到期",
        "blocked": "任务受阻提醒",
    }
    title = type_labels.get(reminder_type, "任务提醒")
    data = task_message_coupon.message_batch_create(
        {
            "messages": [
                {
                    "accountId": account_id,
                    "title": title,
                    "content": message,
                    "type": f"ai_task_{reminder_type}",
                    "bizId": task_id,
                }
            ],
        }
    )
    return {"status": "sent", **data}


async def send_plan_adoption_request(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
    thread_id: str,
    plans_summary: list[dict],
) -> dict:
    _ = store_id
    logger.info(
        "Tool called: send_plan_adoption_request tenant=%s store=%s plan_count=%d",
        tenant_id,
        store_id,
        len(plans_summary),
    )
    plan_names = "、".join(p.get("name", "") for p in plans_summary[:3])
    title = f"您有 {len(plans_summary)} 个 AI 优化方案待审阅采纳"
    content = f"AI 已基于当前业务数据，为您生成了 {len(plans_summary)} 份针对性优化方案（{plan_names}）。方案详情已准备就绪，请前往 【企业APP → AI智能诊断 → 推荐方案】 尽快查看并选择采纳，以便及时落地执行。"
    messages = [
        {
            "accountId": aid,
            "title": title,
            "content": content,
            "type": "ai_plan_adoption",
            "jumpUrl": thread_id,
        }
        for aid in admin_account_ids
    ]
    if not messages:
        return {"sent_count": 0, "status": "no_admin"}
    data = task_message_coupon.message_batch_create({"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


async def send_review_report_notification(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
    thread_id: str,
    review_summary: dict,
) -> dict:
    _ = store_id
    logger.info(
        "Tool called: send_review_report_notification tenant=%s store=%s thread_id=%s",
        tenant_id,
        store_id,
        thread_id,
    )
    achievement = review_summary.get("overall_achievement", 0)
    improved = review_summary.get("improved_count", 0)
    total = review_summary.get("total_indicators", 0)
    solution_name = review_summary.get("solution_name", "")
    report_time = review_summary.get("report_time", "")
    tracking_period = review_summary.get("tracking_period", "")
    parts = []
    if solution_name:
        parts.append(f"方案: {solution_name}")
    if tracking_period:
        parts.append(f"追踪区间: {tracking_period}")
    parts.append(f"达成率 {achievement:.0f}%（{improved}/{total} 项指标改善）")
    if report_time:
        parts.append(f"报告时间: {report_time}")
    parts.append("报告详情请到【APP → AI智能诊断 → 效果追踪】中查看")
    title = f"方案复盘完成 — 达成率 {achievement:.0f}%"
    content = " | ".join(parts)
    messages = [
        {
            "accountId": aid,
            "title": title,
            "content": content,
            "type": "ai_review_report",
            "jumpUrl": thread_id,
        }
        for aid in admin_account_ids
    ]
    if not messages:
        return {"sent_count": 0, "status": "no_admin"}
    data = task_message_coupon.message_batch_create({"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


async def send_task_assignment_notification(
    tenant_id: str,
    store_id: str,
    tasks: list[dict],
) -> dict:
    _ = store_id
    logger.info(
        "Tool called: send_task_assignment_notification tenant=%s store=%s task_count=%d",
        tenant_id,
        store_id,
        len(tasks),
    )
    messages = []
    for t in tasks:
        account_id = t.get("assignee_account_id") or t.get("assignee_user_id")
        if not account_id:
            continue
        task_name = t.get("task_name", "")
        deadline = t.get("deadline", "")
        messages.append(
            {
                "accountId": str(account_id),
                "title": f"新任务分配：{task_name}",
                "content": f"您有一项新的AI诊断执行任务「{task_name}」，请在{deadline}前完成。",
                "type": "ai_task_assignment",
                "bizId": t.get("task_id", ""),
            }
        )
    if not messages:
        return {"sent_count": 0, "status": "no_assignee"}
    data = task_message_coupon.message_batch_create({"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


async def send_customer_targeted_message(
    tenant_id: str,
    store_id: str,
    target_segment: str,
    title: str,
    content: str,
    message_type: str = "ai_targeted",
) -> dict:
    logger.info(
        "Tool called: send_customer_targeted_message tenant=%s store=%s segment=%s",
        tenant_id,
        store_id,
        target_segment,
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    body = {
        "storeId": sid,
        "targetSegment": target_segment,
        "title": title,
        "content": content,
        "type": message_type,
    }
    data = task_message_coupon.message_targeted(body)
    return {"sent_count": data.get("sent_count", 0), "status": "sent", **data}


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    """供 dispatch：message-remind POST。"""
    m = method.upper()
    if m == "POST" and path == "message-remind/batch-create":
        return task_message_coupon.message_batch_create(body)
    if m == "POST" and path == "message-remind/targeted":
        return task_message_coupon.message_targeted(body)
    _ = q
    return None


def register(server: FastMCP) -> None:
    """与 biz/notify.register 相同。"""
    for fn in (
        send_diagnosis_report_notification,
        send_task_reminder,
        send_plan_adoption_request,
        send_review_report_notification,
        send_task_assignment_notification,
        send_customer_targeted_message,
    ):
        server.add_tool(fn)
