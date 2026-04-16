"""每日效果追踪复盘检查 — 扫描到期的待复盘记录，恢复 LangGraph 执行 track_effects 节点。"""

from __future__ import annotations

import logging

from src.runtime.graph_app import astream_events_with_retry, get_graph_app
from src.core.pending_review_repo import get_due_reviews, mark_review_done

logger = logging.getLogger(__name__)


async def check_pending_reviews():
    """扫描 review_due_date <= 当前时刻的待复盘记录，逐个恢复 graph 执行效果追踪。"""
    logger.info("===== 开始每日效果追踪复盘检查 =====")
    due_reviews = await get_due_reviews()
    if not due_reviews:
        logger.info("无到期复盘任务")
        return

    logger.info("发现 %d 个到期复盘任务", len(due_reviews))
    app = await get_graph_app()

    for review in due_reviews:
        thread_id = review["thread_id"]
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = await app.aget_state(config)
            if not (state.next and "track_effects" in state.next):
                logger.warning("thread %s 不在 track_effects 中断状态，跳过", thread_id)
                await mark_review_done(thread_id)
                continue

            async for _ in astream_events_with_retry(None, config):
                pass

            await mark_review_done(thread_id)
            logger.info("效果追踪复盘完成: thread=%s, tenant=%s, store=%s",
                        thread_id, review["tenant_id"], review["store_id"])
        except Exception as e:
            logger.error("效果追踪复盘失败: thread=%s, error=%s", thread_id, e)

    logger.info("===== 每日效果追踪复盘检查完成 =====")
