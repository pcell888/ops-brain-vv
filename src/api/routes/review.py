"""复盘相关 HTTP 接口（立即开始复盘）。"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from src.core.pending_review_repo import cancel_pending_review
from src.core.solution_knowledge_repo import list_knowledge
from src.api.deps import get_graph_app, running_tasks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/review", tags=["复盘"])


@router.post("/{thread_id}/start", summary="立即开始复盘")
async def start_review(thread_id: str):
    """立即开始复盘（跳过剩余等待期，恢复 graph 运行 track_effects）。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}

    state = await app.aget_state(config)
    if not (state.next and "track_effects" in state.next):
        raise HTTPException(status_code=400, detail="该诊断不在效果追踪等待状态")

    await cancel_pending_review(thread_id)
    task = asyncio.create_task(_resume_track_effects(thread_id, config))
    running_tasks[thread_id] = task
    task.add_done_callback(lambda _: running_tasks.pop(thread_id, None))

    return {"status": "reviewing", "thread_id": thread_id, "message": "已触发立即复盘"}


async def _resume_track_effects(thread_id: str, config: dict):
    """恢复 graph 执行 track_effects 节点。"""
    app = await get_graph_app()
    try:
        async for _ in app.astream_events(None, config=config, version="v2"):
            pass
        logger.info("手动触发复盘完成: thread=%s", thread_id)
    except Exception as e:
        logger.error("手动触发复盘失败: thread=%s, error=%s", thread_id, e)


@router.get("/knowledge/list", summary="查询方案沉淀知识库")
async def get_solution_knowledge(
    tenant_id: str | None = Query(default=None),
    industry_code: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询方案沉淀知识库（分页）。"""
    items, total = await list_knowledge(tenant_id, industry_code, page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}
