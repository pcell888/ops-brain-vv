"""每日效果追踪复盘检查 — 扫描到期的待复盘记录，恢复执行 track_effects 节点。"""

from __future__ import annotations

import logging

from src.repositories.pending_review import get_due_reviews, mark_review_done

logger = logging.getLogger(__name__)


async def check_pending_reviews():
    """扫描 review_due_date <= 当前时刻的待复盘记录，逐个恢复效果追踪。"""
    logger.info("===== 开始每日效果追踪复盘检查 =====")
    due_reviews = await get_due_reviews()
    if not due_reviews:
        logger.info("无到期复盘任务")
        return

    logger.info("发现 %d 个到期复盘任务", len(due_reviews))

    from src.core.diagnosis_engine import resume_track_effects

    for review in due_reviews:
        thread_id = review["thread_id"]
        try:
            await resume_track_effects(thread_id)
            await mark_review_done(thread_id)
            logger.info("效果追踪复盘完成: thread=%s, tenant=%s, store=%s",
                        thread_id, review["tenant_id"], review["store_id"])
        except Exception as e:
            logger.error("效果追踪复盘失败: thread=%s, error=%s", thread_id, e)

    logger.info("===== 每日效果追踪复盘检查完成 =====")
