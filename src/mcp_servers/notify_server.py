"""
notify-server: 消息通知推送
传输: stdio
"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient

logger = logging.getLogger(__name__)

server = FastMCP("notify-server")
router = TenantRouter()
biz = BizAPIClient(router)


@server.tool()
async def send_diagnosis_report_notification(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
    report_summary: dict,
) -> dict:
    """
    推送诊断报告完成通知给企业管理员。

    report_summary:
    {"health_score", "anomaly_count", "top_anomaly", "report_url"}
    """
    health_score = report_summary.get("health_score", 0)
    anomaly_count = report_summary.get("anomaly_count", 0)
    top_anomaly = report_summary.get("top_anomaly", "")
    notify_type = report_summary.get("notification_type", "ai_diagnosis_report")

    is_weekly = notify_type == "ai_weekly_digest"
    title = f"{'【周度】' if is_weekly else ''}AI诊断报告已生成 — 健康度 {health_score:.1f}分"
    content = f"共发现 {anomaly_count} 项异常指标。"
    if top_anomaly:
        content += f" 最突出问题：{top_anomaly}"

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

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})

    return {"sent_count": len(messages), "status": "sent", **data}


@server.tool()
async def send_task_reminder(
    tenant_id: str,
    user_id: int,
    account_id: str,
    task_id: str,
    reminder_type: str,
    message: str,
) -> dict:
    """
    发送任务相关提醒。
    reminder_type: overdue | approaching_deadline | blocked
    """
    type_labels = {
        "overdue": "任务超期提醒",
        "approaching_deadline": "任务即将到期",
        "blocked": "任务受阻提醒",
    }
    title = type_labels.get(reminder_type, "任务提醒")

    data = await biz.post(
        tenant_id,
        "/message-remind/batch-create",
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
        },
    )

    return {"status": "sent", **data}


@server.tool()
async def send_plan_adoption_request(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
    thread_id: str,
    plans_summary: list[dict],
) -> dict:
    """推送方案待采纳通知。"""
    plan_names = "、".join(p.get("name", "") for p in plans_summary[:3])
    title = "AI优化方案待采纳"
    content = f"已生成 {len(plans_summary)} 个优化方案（{plan_names}），请查看并选择采纳。"

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

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


@server.tool()
async def send_review_report_notification(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
    thread_id: str,
    review_summary: dict,
) -> dict:
    """推送复盘报告完成通知。"""
    achievement = review_summary.get("overall_achievement", 0)
    improved = review_summary.get("improved_count", 0)

    title = f"AI复盘报告已生成 — 达成率 {achievement:.0f}%"
    content = f"共 {improved} 项指标得到改善。"

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

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


@server.tool()
async def send_task_assignment_notification(
    tenant_id: str,
    store_id: str,
    tasks: list[dict],
) -> dict:
    """
    批量发送任务分配通知给各任务负责人。
    tasks 中每项需包含: task_id, task_name, assignee_user_id, assignee_account_id, deadline
    """
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

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})

    return {"sent_count": len(messages), "status": "sent", **data}


@server.tool()
async def send_customer_targeted_message(
    tenant_id: str,
    store_id: str,
    target_segment: str,
    title: str,
    content: str,
    message_type: str = "ai_targeted",
) -> dict:
    """
    按人群定向推送消息（5.2.3 用）。
    target_segment: churn_risk | no_repurchase_90d | coupon_expiring_soon | low_conversion
    wlwq 需实现 POST /message-remind/targeted 或由本工具先拉取客户列表再 batch-create。
    """
    data = await biz.post(
        tenant_id,
        "/message-remind/targeted",
        {
            "storeId": store_id,
            "targetSegment": target_segment,
            "title": title,
            "content": content,
            "type": message_type,
        },
    )
    return {"sent_count": data.get("sent_count", 0), "status": "sent", **data}


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
