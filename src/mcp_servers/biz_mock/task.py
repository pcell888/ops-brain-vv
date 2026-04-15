"""任务与审批 — 与 biz/task.py 同名、同签名、同 register；进程内模拟。"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.biz_api_client import BizAPIError
from src.mcp_servers.biz_mock import client_sales_examine, task_message_coupon
from src.mcp_servers.biz_scope import effective_store_id_for_biz

logger = logging.getLogger(__name__)


async def create_execution_tasks(
    tenant_id: str,
    store_id: str,
    plan_id: str,
    tasks: list[dict],
) -> dict:
    logger.info(
        "Tool called: create_execution_tasks tenant=%s store=%s plan_id=%s task_count=%d",
        tenant_id,
        store_id,
        plan_id,
        len(tasks),
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    payload = {"storeId": sid, "planId": plan_id, "tasks": tasks}
    data = task_message_coupon.exec_task_batch_create(payload)
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
    data = client_sales_examine.examine_create(body)
    return {"approval_id": data.get("id", ""), "status": "pending"}


async def update_task_status(
    tenant_id: str,
    task_id: str,
    status: str,
    progress: float | None = None,
    remark: str | None = None,
) -> dict:
    _ = tenant_id
    logger.info("Tool called: update_task_status tenant=%s task_id=%s status=%s", tenant_id, task_id, status)
    payload: dict = {"status": status}
    if progress is not None:
        payload["progress"] = progress
    if remark:
        payload["remark"] = remark
    return task_message_coupon.exec_task_update_status(task_id, payload)


async def create_coupon_campaign(
    tenant_id: str,
    store_id: str,
    campaign_config: dict,
) -> dict:
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
    coupon_data = task_message_coupon.coupon_create(create_body)
    coupon_id = coupon_data.get("couponId", "")
    dist_body = {
        "storeId": sid,
        "couponId": coupon_id,
        "targetCustomers": campaign_config.get("target_customers", "all"),
    }
    distribute_data = task_message_coupon.coupon_distribute(dist_body)
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
    logger.info("Tool called: create_seckill_activity tenant=%s store=%s", tenant_id, store_id)
    sid = effective_store_id_for_biz(tenant_id, store_id)
    body = dict(activity_config)
    body["storeId"] = sid
    data = task_message_coupon.seckill_create(body)
    return {"activity_id": data.get("id", ""), "status": "created"}


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    """供 dispatch：exec-task / examine / coupon / seckill。"""
    m = method.upper()
    if m == "POST" and path == "examine-initiate/create":
        return client_sales_examine.examine_create(body)
    if m == "POST" and path == "ai-diagnosis/exec-task/batch-create":
        return task_message_coupon.exec_task_batch_create(body)
    if m == "PUT" and path.startswith("ai-diagnosis/exec-task/") and path.endswith("/status"):
        inner = path[len("ai-diagnosis/exec-task/") : -len("/status")]
        if not inner:
            raise BizAPIError(404, "缺少 task_id", path)
        return task_message_coupon.exec_task_update_status(inner, body)
    if m == "POST" and path == "coupon/create":
        return task_message_coupon.coupon_create(body)
    if m == "POST" and path == "coupon/distribute":
        return task_message_coupon.coupon_distribute(body)
    if m == "POST" and path == "seckill-apply/create":
        return task_message_coupon.seckill_create(body)
    _ = q
    return None


def register(server: FastMCP) -> None:
    """与 biz/task.register 相同。"""
    for fn in (
        create_execution_tasks,
        create_approval_flow,
        update_task_status,
        create_coupon_campaign,
        create_seckill_activity,
    ):
        server.add_tool(fn)
