"""
task-server: 任务创建与推送
传输: stdio
"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient

logger = logging.getLogger(__name__)

server = FastMCP("task-server")
router = TenantRouter()
biz = BizAPIClient(router)


@server.tool()
async def create_execution_tasks(
    tenant_id: str,
    store_id: str,
    plan_id: str,
    tasks: list[dict],
) -> dict:
    """
    批量创建执行任务并推送到目标企业的业务系统。

    tasks 结构:
    [{"task_name", "description", "assignee_user_id", "assignee_dept_id",
      "deadline", "priority", "related_resources"}]
    """
    payload = {
        "storeId": store_id,
        "planId": plan_id,
        "tasks": tasks,
    }
    data = await biz.post(tenant_id, "/ai-diagnosis/exec-task/batch-create", payload)

    return {
        "plan_id": plan_id,
        "created_tasks": data.get("tasks", data.get("list", [])),
        "created_count": data.get("count", len(tasks)),
    }


@server.tool()
async def create_approval_flow(
    tenant_id: str,
    store_id: str,
    plan_id: str,
    title: str,
    content: str,
    approver_user_id: int,
) -> dict:
    """发起方案审批流程（复用现有OA审批）。"""
    data = await biz.post(tenant_id, "/examine-initiate/create", {
        "storeId": store_id,
        "title": title,
        "content": content,
        "approverUserId": approver_user_id,
        "bizType": "ai_diagnosis",
        "bizId": plan_id,
    })
    return {"approval_id": data.get("id", ""), "status": "pending"}


@server.tool()
async def update_task_status(
    tenant_id: str,
    task_id: str,
    status: str,
    progress: float | None = None,
    remark: str | None = None,
) -> dict:
    """更新任务执行状态。status: pending | in_progress | completed | paused | cancelled"""
    payload: dict = {"status": status}
    if progress is not None:
        payload["progress"] = progress
    if remark:
        payload["remark"] = remark

    data = await biz.put(tenant_id, f"/ai-diagnosis/exec-task/{task_id}/status", payload)
    return {"task_id": task_id, "status": status, "updated": True, **data}


@server.tool()
async def create_coupon_campaign(
    tenant_id: str,
    store_id: str,
    campaign_config: dict,
) -> dict:
    """
    创建优惠券营销活动（方案执行动作之一）。

    campaign_config:
    {"coupon_name", "coupon_type", "full_price", "reduce_price",
     "target_customers", "start_time", "end_time"}
    """
    coupon_data = await biz.post(tenant_id, "/coupon/create", {
        "storeId": store_id,
        "couponName": campaign_config.get("coupon_name"),
        "couponType": campaign_config.get("coupon_type", 1),
        "fullPrice": campaign_config.get("full_price"),
        "reducePrice": campaign_config.get("reduce_price"),
        "startTime": campaign_config.get("start_time"),
        "endTime": campaign_config.get("end_time"),
    })
    coupon_id = coupon_data.get("id", coupon_data.get("couponId", ""))

    distribute_data = await biz.post(tenant_id, "/coupon/distribute", {
        "storeId": store_id,
        "couponId": coupon_id,
        "targetCustomers": campaign_config.get("target_customers", "all"),
    })

    return {
        "coupon_id": coupon_id,
        "distributed_count": distribute_data.get("count", 0),
        "campaign_config": campaign_config,
    }


@server.tool()
async def create_seckill_activity(
    tenant_id: str,
    store_id: str,
    activity_config: dict,
) -> dict:
    """创建秒杀活动（方案执行动作之一）。"""
    data = await biz.post(tenant_id, "/seckill-apply/create", {
        "storeId": store_id,
        **activity_config,
    })
    return {"activity_id": data.get("id", ""), "status": "created"}


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
