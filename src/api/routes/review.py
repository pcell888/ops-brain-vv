"""复盘相关 HTTP 接口（立即开始复盘、进度轮询）。"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from src.agent.tools import clear_progress_sender, set_progress_sender
from src.api.deps import astream_events_with_retry, get_graph_app, manager, progress_cache, running_tasks, send_thread_progress
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.core.effect_review_repo import review_report_exists
from src.core.pending_review_repo import cancel_pending_review, get_pending_review_by_thread
from src.core.solution_knowledge_repo import list_knowledge

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


def _last_effect_track_hint(values: dict, cached: dict) -> tuple[str, str | None, int | None]:
    """(message, timestamp_iso, percent) 优先 effect_track 缓存，其次 progress_messages。"""
    if cached.get("stage") == "effect_track":
        msg = str(cached.get("message", "") or "").strip()
        ts = cached.get("timestamp")
        pct = cached.get("percent")
        try:
            pi = int(float(pct)) if pct is not None else None
        except (TypeError, ValueError):
            pi = None
        return msg, ts, pi
    for msg in reversed(values.get("progress_messages") or []):
        if not isinstance(msg, dict) or msg.get("stage") != "effect_track":
            continue
        content = str(msg.get("content", "") or "").strip()
        ts = msg.get("timestamp")
        pct = msg.get("percent")
        try:
            pi = int(float(pct)) if pct is not None else None
        except (TypeError, ValueError):
            pi = None
        return content, ts, pi
    return "", None, None


def _effect_track_signal(values: dict, cached: dict) -> bool:
    if cached.get("stage") == "effect_track":
        return True
    for msg in reversed(values.get("progress_messages") or []):
        if isinstance(msg, dict) and msg.get("stage") == "effect_track":
            return True
    return False


def _progress_payload(
    thread_id: str,
    *,
    status: str,
    is_running: bool,
    percent: int,
    message: str,
    last_ts: str | None,
    event_type,
    node: str | None,
    review_due_date: str | None = None,
) -> dict:
    out = {
        "thread_id": thread_id,
        "tracking_id": thread_id,
        "status": status,
        "is_running": is_running,
        "stage": "effect_track",
        "percent": percent,
        "message": message,
        "last_timestamp": last_ts,
        "event_type": event_type,
        "node": node,
    }
    if review_due_date is not None:
        out["review_due_date"] = review_due_date
    return out


async def build_review_progress(thread_id: str) -> dict:
    """供 HTTP 轮询：效果追踪 / 复盘进度（与 WS `stage=effect_track`、progress_cache 一致）。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}
    next_nodes = list(state.next) if state and state.next else []
    wait_track = "track_effects" in next_nodes

    cached = progress_cache.get(thread_id) or {}
    event_type = cached.get("type")
    stage = cached.get("stage")
    node = cached.get("node") if isinstance(cached.get("node"), str) else None

    task = running_tasks.get(thread_id)
    is_running = task is not None and not task.done()

    msg_hint, last_ts, pct_hint = _last_effect_track_hint(values, cached)
    rp_state = values.get("review_report")
    has_report = bool(rp_state) or await review_report_exists(thread_id)

    # 完成追踪：复盘报告已 INSERT 后仍会执行「沉淀方案」等，并继续 send_thread_progress(type=progress)。
    # 若仅依据 has_report 则此处会过早返回 completed/100%，与真实收尾不一致。
    if stage == "effect_track" and event_type == "progress":
        p = max(0, min(100, pct_hint if pct_hint is not None else 50))
        return _progress_payload(
            thread_id,
            status="running",
            is_running=True,
            percent=p,
            message=msg_hint or "处理中…",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
        )

    if has_report:
        # 报告已落库且缓存已非 progress（通常为 completed），或兼容无缓存时认为已结束
        return _progress_payload(
            thread_id,
            status="completed",
            is_running=False,
            percent=100,
            message="追踪已完成，复盘报告已生成",
            last_ts=last_ts,
            event_type="completed",
            node=node,
        )

    if stage == "effect_track" and event_type == "error":
        return _progress_payload(
            thread_id,
            status="failed",
            is_running=False,
            percent=0,
            message=msg_hint or "复盘失败",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
        )

    if stage == "effect_track" and event_type == "completed":
        return _progress_payload(
            thread_id,
            status="completed",
            is_running=False,
            percent=100,
            message=msg_hint or "复盘已完成",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
        )

    if wait_track:
        if is_running:
            p = 50 if pct_hint is None else max(0, min(100, pct_hint))
            return _progress_payload(
                thread_id,
                status="running",
                is_running=True,
                percent=p,
                message=msg_hint or "复盘进行中…",
                last_ts=last_ts,
                event_type=event_type,
                node=node,
            )
        pr = await get_pending_review_by_thread(thread_id)
        if pr:
            due = pr.get("review_due_date")
            due_s = due.isoformat() if hasattr(due, "isoformat") else str(due) if due else ""
            return _progress_payload(
                thread_id,
                status="scheduled",
                is_running=False,
                percent=0,
                message=msg_hint or (f"复盘已排程，将于 {due_s} 自动执行" if due_s else "复盘已排程"),
                last_ts=last_ts,
                event_type=event_type,
                node=node,
                review_due_date=due_s or None,
            )
        return _progress_payload(
            thread_id,
            status="ready",
            is_running=False,
            percent=0,
            message=msg_hint or "可立即开始复盘",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
        )

    if is_running and _effect_track_signal(values, cached):
        p = 50 if pct_hint is None else max(0, min(100, pct_hint))
        return _progress_payload(
            thread_id,
            status="running",
            is_running=True,
            percent=p,
            message=msg_hint or "复盘进行中…",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
        )

    if stage == "effect_track":
        p = max(0, min(100, pct_hint if pct_hint is not None else 0))
        return _progress_payload(
            thread_id,
            status="running",
            is_running=is_running,
            percent=p,
            message=msg_hint or "复盘进行中…",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
        )

    return {
        "thread_id": thread_id,
        "tracking_id": thread_id,
        "status": "idle",
        "is_running": False,
        "stage": None,
        "percent": 0,
        "message": msg_hint,
        "last_timestamp": last_ts,
        "event_type": event_type,
        "node": node,
    }


@router.get("/{thread_id}/progress", summary="查询复盘进度")
async def get_review_progress(thread_id: str):
    """轮询效果追踪 / 复盘执行进度（与 WebSocket `stage=effect_track` 同源缓存）。"""
    return await build_review_progress(thread_id)


async def _resume_track_effects(thread_id: str, config: dict):
    """恢复 graph 执行 track_effects 节点，并打通 emit_progress → WS / progress_cache。"""
    try:
        set_progress_sender(thread_id, manager)
        async for _ in astream_events_with_retry(None, config):
            pass
        logger.info("手动触发复盘完成: thread=%s", thread_id)
    except Exception as e:
        logger.exception("手动触发复盘失败 thread=%s", thread_id)
        await send_thread_progress(
            thread_id,
            {
                "type": "error",
                "stage": "effect_track",
                "message": public_diagnosis_error_message(e),
            },
        )
    finally:
        clear_progress_sender()


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
