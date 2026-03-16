"""定期指标快照采集 — 在效果追踪等待期间按间隔采集指标快照。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from src.api.deps import get_graph_app
from src.agent.tools import mcp_call
from src.core.config import get_settings
from src.core.calculator import resolve_active_indicators
from src.core.pending_review_repo import get_due_reviews
from src.core.snapshot_repo import save_snapshot, get_last_snapshot_time

logger = logging.getLogger(__name__)

DIMENSION_TOOL_MAP: dict[str, str] = {
    "crm": "get_crm_indicators",
    "marketing": "get_marketing_indicators",
    "retention": "get_retention_indicators",
    "efficiency": "get_efficiency_indicators",
    "inventory": "get_inventory_indicators",
}


async def _get_pending_threads() -> list[dict]:
    """获取所有处于追踪等待状态的 pending review 记录（含未到期的）。"""
    from src.core.db_init import _uri_to_conninfo, ensure_ai_pending_review
    import psycopg

    await ensure_ai_pending_review()
    conninfo = _uri_to_conninfo(get_settings().postgres_uri)
    try:
        async with await psycopg.AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT thread_id, tenant_id, store_id FROM ai_pending_review WHERE status = 'pending'"
                )
                return await cur.fetchall()
    except Exception as e:
        logger.warning("查询待追踪记录失败: %s", e)
        return []


async def _collect_snapshot_for_thread(thread: dict) -> None:
    thread_id = thread["thread_id"]
    tenant_id = thread["tenant_id"]
    store_id = thread["store_id"]

    settings = get_settings()
    interval = settings.effect_snapshot_interval_days
    if interval <= 0:
        return

    last_time = await get_last_snapshot_time(thread_id)
    if last_time and (datetime.now() - last_time) < timedelta(days=interval):
        return

    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    if not state.values:
        return

    active_dims, _ = resolve_active_indicators(
        state.values.get("selected_dimensions"),
        state.values.get("selected_indicators"),
    )

    now = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    common_args = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "start_date": start,
        "end_date": now,
    }

    ordered_dims: list[str] = []
    tasks: list = []
    for dim in ("crm", "marketing", "retention", "efficiency", "inventory"):
        if dim in active_dims:
            tasks.append(mcp_call("metrics-server", DIMENSION_TOOL_MAP[dim], common_args))
            ordered_dims.append(dim)

    if not tasks:
        return

    try:
        results = await asyncio.gather(*tasks)
        snapshot_data = dict(zip(ordered_dims, results))
        await save_snapshot(thread_id, tenant_id, store_id, snapshot_data)
        logger.info("快照采集完成: thread=%s", thread_id)
    except Exception as e:
        logger.error("快照采集失败: thread=%s, error=%s", thread_id, e)


async def collect_effect_snapshots():
    """入口：扫描所有追踪中的 thread，按间隔采集快照。"""
    settings = get_settings()
    if settings.effect_snapshot_interval_days <= 0:
        return

    logger.info("===== 开始效果追踪快照采集 =====")
    threads = await _get_pending_threads()
    if not threads:
        logger.info("无追踪中的诊断会话")
        return

    logger.info("共 %d 个追踪中的诊断会话", len(threads))
    for thread in threads:
        try:
            await _collect_snapshot_for_thread(thread)
        except Exception as e:
            logger.error("快照采集异常: thread=%s, error=%s", thread.get("thread_id"), e)

    logger.info("===== 效果追踪快照采集完成 =====")
