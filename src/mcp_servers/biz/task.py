"""任务与审批 — 原 task-server 工具实现。"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.biz.shared import biz
from src.mcp_servers.biz_scope import effective_store_id_for_biz

logger = logging.getLogger(__name__)


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
      "deadline", "deadline_at", "priority", "related_resources"}]
    """
    logger.info(
        "Tool called: create_execution_tasks tenant=%s store=%s plan_id=%s task_count=%d",
        tenant_id,
        store_id,
        plan_id,
        len(tasks),
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    payload = {"storeId": sid, "planId": plan_id, "tasks": tasks}
    data = await biz.post(tenant_id, "/ai-diagnosis/exec-task/batch-create", payload)

    return {
        "plan_id": plan_id,
        "created_tasks": data.get("tasks", data.get("list", [])),
        "created_count": data.get("count", len(tasks)),
    }


async def create_approval_flow(
    tenant_id: str,
    store_id: str,
    plan_id: str,
    title: str,
    content: str,
    approver_user_id: int,
) -> dict:
    """发起方案审批流程（复用现有OA审批）。"""
    logger.info(
        "Tool called: create_approval_flow tenant=%s store=%s plan_id=%s approver=%s",
        tenant_id,
        store_id,
        plan_id,
        approver_user_id,
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    body = {
        "storeId": sid,
        "title": title,
        "content": content,
        "approverUserId": approver_user_id,
        "bizType": "ai_diagnosis",
        "bizId": plan_id,
    }
    data = await biz.post(tenant_id, "/examine-initiate/create", body)
    return {"approval_id": data.get("id", ""), "status": "pending"}


async def update_task_status(
    tenant_id: str,
    task_id: str,
    status: str,
    progress: float | None = None,
    remark: str | None = None,
) -> dict:
    """更新任务执行状态。status: pending | in_progress | completed | paused | cancelled"""
    logger.info("Tool called: update_task_status tenant=%s task_id=%s status=%s", tenant_id, task_id, status)
    payload: dict = {"status": status}
    if progress is not None:
        payload["progress"] = progress
    if remark:
        payload["remark"] = remark

    data = await biz.put(tenant_id, f"/ai-diagnosis/exec-task/{task_id}/status", payload)
    return {"task_id": task_id, "status": status, "updated": True, **data}


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
    logger.info(
        "Tool called: create_coupon_campaign tenant=%s store=%s config=%s",
        tenant_id,
        store_id,
        campaign_config.get("coupon_name"),
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    create_body = {
        "storeId": sid,
        "couponName": campaign_config.get("coupon_name"),
        "couponType": campaign_config.get("coupon_type", 1),
        "fullPrice": campaign_config.get("full_price"),
        "reducePrice": campaign_config.get("reduce_price"),
        "startTime": campaign_config.get("start_time"),
        "endTime": campaign_config.get("end_time"),
    }
    coupon_data = await biz.post(tenant_id, "/coupon/create", create_body)
    coupon_id = coupon_data.get("id", coupon_data.get("couponId", ""))

    dist_body = {
        "storeId": sid,
        "couponId": coupon_id,
        "targetCustomers": campaign_config.get("target_customers", "all"),
    }
    distribute_data = await biz.post(tenant_id, "/coupon/distribute", dist_body)

    return {
        "coupon_id": coupon_id,
        "distributed_count": distribute_data.get("count", 0),
        "campaign_config": campaign_config,
    }


async def create_seckill_activity(
    tenant_id: str,
    store_id: str,
    activity_config: dict,
) -> dict:
    """创建秒杀活动（方案执行动作之一）。"""
    logger.info("Tool called: create_seckill_activity tenant=%s store=%s", tenant_id, store_id)
    sid = effective_store_id_for_biz(tenant_id, store_id)
    body = dict(activity_config)
    body["storeId"] = sid
    data = await biz.post(tenant_id, "/seckill-apply/create", body)
    return {"activity_id": data.get("id", ""), "status": "created"}


def register(server: FastMCP) -> None:
    for fn in (
        create_execution_tasks,
        create_approval_flow,
        update_task_status,
        create_coupon_campaign,
        create_seckill_activity,
    ):
        server.add_tool(fn)
