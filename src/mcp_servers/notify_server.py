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

    title = f"AI诊断报告已生成 — 健康度 {health_score:.1f}分"
    content = f"共发现 {anomaly_count} 项异常指标。"
    if top_anomaly:
        content += f" 最突出问题：{top_anomaly}"

    messages = [
        {
            "accountId": aid,
            "title": title,
            "content": content,
            "type": "ai_diagnosis_report",
            "jumpUrl": report_summary.get("report_url", ""),
        }
        for aid in admin_account_ids
    ]

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})
    await biz.post(tenant_id, "/message-record/create", {
        "storeId": store_id,
        "type": "ai_diagnosis_report",
        "title": title,
        "content": content,
    })

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

    data = await biz.post(tenant_id, "/message-remind/create", {
        "accountId": account_id,
        "title": title,
        "content": message,
        "type": f"ai_task_{reminder_type}",
        "bizId": task_id,
    })
    await biz.post(tenant_id, "/message-record/create", {
        "userId": user_id,
        "type": f"ai_task_{reminder_type}",
        "title": title,
        "content": message,
        "bizId": task_id,
    })

    return {"status": "sent", **data}


@server.tool()
async def send_plan_adoption_request(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
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
        }
        for aid in admin_account_ids
    ]

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


@server.tool()
async def send_review_report_notification(
    tenant_id: str,
    store_id: str,
    admin_account_ids: list[str],
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
        }
        for aid in admin_account_ids
    ]

    data = await biz.post(tenant_id, "/message-remind/batch-create", {"messages": messages})
    return {"sent_count": len(messages), "status": "sent", **data}


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
