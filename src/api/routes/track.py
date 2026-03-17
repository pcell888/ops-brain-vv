"""追踪相关 HTTP 接口（效果追踪、快照）。"""

from __future__ import annotations

from fastapi import APIRouter

from src.core.snapshot_repo import list_snapshots

router = APIRouter(prefix="/track", tags=["追踪"])


@router.get("/{thread_id}/snapshots", summary="获取指标快照列表")
async def get_effect_snapshots(thread_id: str):
    """获取该次诊断追踪期间的指标快照列表（按时间正序）。"""
    snapshots = await list_snapshots(thread_id)
    return {"thread_id": thread_id, "count": len(snapshots), "snapshots": snapshots}
