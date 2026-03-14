"""周度自动诊断定时任务 — 遍历所有活跃租户执行诊断。"""

from __future__ import annotations

import asyncio
import logging

import psycopg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.api.deps import get_graph_app, generate_thread_id
from src.core.config import get_settings

logger = logging.getLogger(__name__)


async def _get_active_tenants() -> list[dict]:
    """从 tenant_registry 获取所有活跃租户和店铺。"""
    settings = get_settings()
    async with await psycopg.AsyncConnection.connect(settings.postgres_uri) as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT tenant_id, tenant_name, config FROM tenant_registry "
                "WHERE status=1 AND tenant_id != '__platform__'"
            )
            return await cur.fetchall()


async def _run_single_diagnosis(tenant_id: str, store_id: str):
    """为单个租户/店铺执行自动诊断。"""
    app = await get_graph_app()
    thread_id = generate_thread_id()
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": "scheduled",
        "triggered_by": "system",
        "progress_messages": [],
    }

    try:
        async for _ in app.astream_events(initial_state, config=config, version="v2"):
            pass
        logger.info("周度诊断完成: tenant=%s, store=%s, thread=%s", tenant_id, store_id, thread_id)
    except Exception as e:
        logger.error("周度诊断失败: tenant=%s, store=%s, error=%s", tenant_id, store_id, e)


async def run_weekly_diagnosis():
    """周度诊断入口 — 遍历所有活跃租户，串行执行。"""
    logger.info("===== 开始周度自动诊断 =====")
    tenants = await _get_active_tenants()
    logger.info("共 %d 个活跃租户", len(tenants))

    for tenant in tenants:
        tenant_id = tenant["tenant_id"]
        config = tenant.get("config", {})
        store_ids = config.get("store_ids", [tenant_id])

        for store_id in store_ids:
            await _run_single_diagnosis(tenant_id, store_id)
            await asyncio.sleep(1)

    logger.info("===== 周度自动诊断完成 =====")


def start_scheduler():
    """启动定时任务调度器。"""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_weekly_diagnosis,
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0),
        id="weekly_diagnosis",
        name="周度自动诊断",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("定时任务调度器已启动 (每周一凌晨2:00执行)")
    return scheduler
