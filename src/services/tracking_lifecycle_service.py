"""追踪生命周期。"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime

from src.runtime.diagnosis_ws_manager import send_thread_progress
from src.core.compat_tracking_repo import (
    count_trackings,
    create_tracking,
    list_tracking_thread_ids_for_tenant_plan,
    get_diagnosis_scores,
    get_latest_snapshot,
    get_tracking,
    insert_snapshot,
    list_exec_tasks_for_report,
    list_snapshots,
    list_trackings as repo_list_trackings,
    tracking_exists,
    update_tracking_data,
    upsert_review_report,
)
from src.core.config import CN_TZ, get_settings
from src.core.db_init import ensure_ai_pending_review
from src.core.pending_review_repo import (
    cancel_pending_review,
    get_pending_review,
    get_pending_review_by_thread,
)
from src.core.solution_knowledge_repo import save_effective_plan
from src.core.tracking_names import resolve_solution_name

from src.services.tracking_error_service import LLMReviewReportError, TrackingServiceError
from src.services.tracking_helper_service import (
    _derive_adopted_plan_name,
    _derive_tracking_status,
    _get_diagnosis_health_score,
    _scheduled_row_enrichment,
    _scheduled_tracking_started_at,
    _ser,
    _to_float,
)
from src.services.tracking_report_service import (
    _build_base_report,
    _llm_review_report,
    _merge_llm_report,
    _pending_list_item,
)

logger = logging.getLogger(__name__)

_complete_tracking_inflight: set[str] = set()
_complete_tracking_lock = asyncio.Lock()


async def start_effect_tracking(enterprise_id: str, plan_id: str, interval_days: int) -> dict:
    if not enterprise_id or not plan_id:
        raise TrackingServiceError(400, "enterprise_id 和 plan_id 必填")

    existing_track = await list_tracking_thread_ids_for_tenant_plan(enterprise_id.strip(), plan_id.strip())
    if existing_track:
        raise TrackingServiceError(
            400,
            f"该方案已存在效果追踪，请使用 tracking_id={existing_track[0]}",
        )

    thread_id = f"trk_{uuid.uuid4().hex[:16]}"
    now = datetime.now(CN_TZ)
    tracking_data = {
        "plan_id": plan_id,
        "status": "active",
        "current_score": None,
        "snapshot_count": 0,
        "started_at": now.isoformat(),
        "last_snapshot_at": None,
        "completed_at": None,
        "tracking_interval_days": interval_days,
    }
    try:
        await create_tracking(
            thread_id=thread_id,
            tenant_id=enterprise_id,
            store_id="",
            tracking_data=tracking_data,
            created_at=now,
        )
        return {"tracking_id": thread_id, "status": "active", "message": "追踪已启动"}
    except Exception as e:
        logger.exception("启动追踪失败")
        raise TrackingServiceError(500, "启动追踪失败，请稍后重试") from e


async def list_tracking_items(
    enterprise_id: str | None,
    status: str | None,
    diagnosis_id: str | None,
    skip: int,
    limit: int,
) -> dict:
    try:
        await ensure_ai_pending_review()
        pending_row = None
        pending_bonus = 0
        if enterprise_id and diagnosis_id:
            pending_row = await get_pending_review(enterprise_id, diagnosis_id)
            if pending_row and (not status or status == "scheduled"):
                pending_bonus = 1

        total_db = await count_trackings(enterprise_id=enterprise_id, diagnosis_id=diagnosis_id)
        total = int(total_db) + pending_bonus
        db_skip = max(0, skip - pending_bonus)
        db_limit = max(0, limit - 1) if pending_bonus and skip == 0 else limit

        rows = await repo_list_trackings(
            enterprise_id=enterprise_id,
            diagnosis_id=diagnosis_id,
            skip=db_skip,
            limit=db_limit,
        )

        items: list[dict] = []
        if pending_bonus and pending_row and skip == 0:
            sol, sc = await _scheduled_row_enrichment(pending_row["thread_id"])
            track_started = await _scheduled_tracking_started_at(pending_row, pending_row["thread_id"])
            items.append(
                _pending_list_item(
                    pending_row["thread_id"],
                    diagnosis_id or pending_row["thread_id"],
                    pending_row["review_due_date"],
                    solution_name=sol,
                    current_score=sc,
                    tracking_started_at=track_started,
                )
            )

        for row in rows:
            td = row["tracking_data"] or {}
            if isinstance(td, str):
                td = json.loads(td)
            eff_status = _derive_tracking_status(td)
            if status and eff_status != status:
                continue
            items.append(
                {
                    "tracking_id": row["thread_id"],
                    "plan_id": td.get("plan_id", ""),
                    "diagnosis_id": row.get("diagnosis_id") or row["thread_id"],
                    "solution_name": resolve_solution_name(td, row.get("adopted_plan_name")),
                    "status": eff_status,
                    "current_score": td.get("current_score") if td.get("current_score") is not None else td.get("overall_achievement_rate"),
                    "snapshot_count": td.get("snapshot_count", 0),
                    "started_at": td.get("started_at", _ser(row["created_at"])),
                    "last_snapshot_at": td.get("last_snapshot_at"),
                    "completed_at": td.get("completed_at"),
                }
            )

        missing_ids = [it["tracking_id"] for it in items if it.get("current_score") is None]
        if missing_ids:
            try:
                diag_map = await get_diagnosis_scores(missing_ids)
                for it in items:
                    if it.get("current_score") is None and it["tracking_id"] in diag_map:
                        it["current_score"] = diag_map[it["tracking_id"]]
            except Exception:
                pass

        return {"items": items, "total": total}
    except Exception:
        logger.exception("查询追踪列表失败")
        return {"items": [], "total": 0}


async def get_tracking_summary_payload(tracking_id: str) -> dict:
    try:
        await ensure_ai_pending_review()
        row = await get_tracking(tracking_id)
        adopted_plan_name = (
            await _derive_adopted_plan_name(tracking_id=tracking_id, tracking_data=(row or {}).get("tracking_data") or {})
            if row
            else None
        )
        if not row:
            pr = await get_pending_review_by_thread(tracking_id)
            if pr:
                due = pr["review_due_date"]
                sol, scheduled_score = await _scheduled_row_enrichment(tracking_id)
                track_started = await _scheduled_tracking_started_at(pr, tracking_id)
                return {
                    "tracking_id": tracking_id,
                    "plan_id": "",
                    "solution_name": sol,
                    "status": "scheduled",
                    "current_score": scheduled_score,
                    "snapshot_count": 0,
                    "started_at": _ser(track_started) if track_started else None,
                    "last_snapshot_at": None,
                    "completed_at": None,
                    "review_due_date": _ser(due),
                    "scheduled": True,
                }
            raise TrackingServiceError(404, "追踪不存在")

        td = row["tracking_data"] or {}
        if isinstance(td, str):
            td = json.loads(td)
        total_duration_days = td.get("total_duration_days")
        effective_score = td.get("current_score")
        if effective_score is None:
            effective_score = td.get("overall_achievement_rate")
        if effective_score is None:
            effective_score = await _get_diagnosis_health_score(tracking_id)
        return {
            "tracking_id": row["thread_id"],
            "plan_id": td.get("plan_id", ""),
            "solution_name": resolve_solution_name(td, adopted_plan_name),
            "status": _derive_tracking_status(td),
            "current_score": effective_score,
            "snapshot_count": td.get("snapshot_count", 0),
            "started_at": td.get("started_at", _ser(row["created_at"])),
            "last_snapshot_at": td.get("last_snapshot_at"),
            "completed_at": td.get("completed_at"),
            "total_duration_days": total_duration_days,
        }
    except TrackingServiceError:
        raise
    except Exception as e:
        logger.exception("查询追踪摘要失败")
        raise TrackingServiceError(500, "查询失败，请稍后重试") from e


async def _complete_tracking_background(tracking_id: str) -> None:
    now = datetime.now(CN_TZ)
    settings = get_settings()
    try:
        await send_thread_progress(tracking_id, {"type": "progress", "stage": "effect_track", "message": "正在完成追踪（收尾快照与数据汇总）…"})

        row = await get_tracking(tracking_id)
        if not row:
            await send_thread_progress(tracking_id, {"type": "error", "stage": "effect_track", "message": "追踪不存在或已删除"})
            return

        td = row["tracking_data"] or {}
        if isinstance(td, str):
            td = json.loads(td)
        td_work = dict(td)
        td_work["status"] = "completed"
        td_work["completed_at"] = now.isoformat()

        latest_snapshot = await get_latest_snapshot(tracking_id)
        should_create_closing_snapshot = True
        if latest_snapshot:
            latest_sd = latest_snapshot["snapshot_data"] or {}
            if isinstance(latest_sd, str):
                latest_sd = json.loads(latest_sd)
            if latest_sd.get("snapshot_type") == "closing":
                should_create_closing_snapshot = False

        closing_data: dict | None = None
        if should_create_closing_snapshot:
            closing_data = {"snapshot_at": now.isoformat(), "health_score": td_work.get("current_score"), "indicators": {}, "snapshot_type": "closing"}
            if latest_snapshot:
                latest_sd = latest_snapshot["snapshot_data"] or {}
                if isinstance(latest_sd, str):
                    latest_sd = json.loads(latest_sd)
                closing_data["indicators"] = latest_sd.get("indicators", {}) or {}
                if latest_sd.get("health_score") is not None:
                    closing_data["health_score"] = latest_sd.get("health_score")
            td_work["snapshot_count"] = (td_work.get("snapshot_count") or 0) + 1
            td_work["last_snapshot_at"] = now.isoformat()
            td_work["current_score"] = closing_data.get("health_score")

        all_snapshots = await list_snapshots(tracking_id)
        scores: list[float] = []
        snapshot_payload: list[dict] = []
        for sr in all_snapshots:
            sd = sr["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            score = _to_float(sd.get("health_score"))
            scores.append(score if score is not None else 0.0)
            snapshot_payload.append(
                {
                    "snapshot_at": sd.get("snapshot_at"),
                    "health_score": sd.get("health_score"),
                    "snapshot_type": sd.get("snapshot_type"),
                    "indicators": sd.get("indicators", {}),
                }
            )
        if should_create_closing_snapshot and closing_data:
            cscore = _to_float(closing_data.get("health_score"))
            scores.append(cscore if cscore is not None else 0.0)
            snapshot_payload.append(
                {
                    "snapshot_at": closing_data.get("snapshot_at"),
                    "health_score": closing_data.get("health_score"),
                    "snapshot_type": closing_data.get("snapshot_type"),
                    "indicators": closing_data.get("indicators", {}),
                }
            )

        adopted_plan_name = await _derive_adopted_plan_name(tracking_id, td_work)
        base_report = _build_base_report(
            tracking_id,
            td_work,
            now.isoformat(),
            scores,
            preferred_solution_name=adopted_plan_name,
        )
        exec_tasks = await list_exec_tasks_for_report(tracking_id)
        llm_tracking_data = {
            **td_work,
            "tracking_id": tracking_id,
            "score_change": base_report.get("score_change"),
            "total_snapshots": len(scores),
            "started_at": base_report.get("started_at"),
            "completed_at": base_report.get("completed_at"),
        }
        strict = bool(settings.llm_enabled and settings.llm_api_key)
        if strict:
            await send_thread_progress(tracking_id, {"type": "progress", "stage": "effect_track", "message": "正在生成 AI 复盘报告，请稍候…"})
        llm_report, review_llm_usage = await _llm_review_report(
            tracking_data=llm_tracking_data,
            snapshots=snapshot_payload,
            exec_tasks=exec_tasks,
            strict_llm=strict,
            preferred_solution_name=adopted_plan_name,
        )
        report = _merge_llm_report(base_report, llm_report)
        if review_llm_usage:
            report["review_llm_usage"] = review_llm_usage

        if should_create_closing_snapshot and closing_data:
            await insert_snapshot(
                thread_id=tracking_id,
                tenant_id=row["tenant_id"],
                store_id=row["store_id"],
                snapshot_data=closing_data,
                snapshot_at=now,
            )
        await update_tracking_data(tracking_id, td_work)
        await upsert_review_report(
            thread_id=tracking_id,
            tenant_id=row["tenant_id"],
            store_id=row["store_id"],
            report=report,
            created_at=now,
        )

        await send_thread_progress(tracking_id, {"type": "progress", "stage": "effect_track", "message": "正在沉淀有效方案…"})
        try:
            achievement = 0.0
            if len(scores) >= 2:
                achievement = min(100.0, max(50.0, 50.0 + (float(scores[-1]) - float(scores[0])) * 2.0))
            elif len(scores) == 1:
                achievement = 60.0
            if achievement >= 50.0:
                lessons = report.get("recommendations", [])
                if not isinstance(lessons, list):
                    lessons = []
                await save_effective_plan(
                    row["tenant_id"],
                    row["store_id"],
                    tracking_id,
                    {
                        "plan_id": td_work.get("plan_id", ""),
                        "plan_name": td_work.get("solution_name", "效果追踪"),
                        "target_indicators": [],
                    },
                    achievement,
                    [],
                    [str(x) for x in lessons[:5]],
                    industry_code=None,
                )
        except Exception as e:
            logger.warning("完成追踪后方案沉淀失败: %s", e)

        await send_thread_progress(tracking_id, {"type": "completed", "stage": "effect_track", "message": "追踪已完成，复盘报告已生成"})
    except LLMReviewReportError as e:
        logger.warning("完成追踪：LLM 失败 %s", e)
        await send_thread_progress(tracking_id, {"type": "error", "stage": "effect_track", "message": str(e) or "AI 复盘失败，请稍后重试"})
    except Exception:
        logger.exception("完成追踪失败")
        await send_thread_progress(tracking_id, {"type": "error", "stage": "effect_track", "message": "完成追踪失败，请稍后重试"})


async def submit_complete_tracking(tracking_id: str) -> dict:
    try:
        if not await tracking_exists(tracking_id):
            raise TrackingServiceError(404, "追踪不存在")
        async with _complete_tracking_lock:
            if tracking_id in _complete_tracking_inflight:
                return {"tracking_id": tracking_id, "status": "accepted", "message": "完成追踪正在处理中，请留意页面进度"}
            _complete_tracking_inflight.add(tracking_id)

        async def _run():
            try:
                await _complete_tracking_background(tracking_id)
            finally:
                async with _complete_tracking_lock:
                    _complete_tracking_inflight.discard(tracking_id)

        asyncio.create_task(_run())
        return {
            "tracking_id": tracking_id,
            "status": "accepted",
            "message": "已开始完成追踪，耗时操作将在后台执行并通过 WebSocket 推送进度",
        }
    except TrackingServiceError:
        raise
    except Exception as e:
        logger.exception("完成追踪任务启动失败")
        async with _complete_tracking_lock:
            _complete_tracking_inflight.discard(tracking_id)
        raise TrackingServiceError(500, "完成追踪失败，请稍后重试") from e


async def cancel_tracking_request(tracking_id: str) -> dict:
    try:
        row = await get_tracking(tracking_id)
        if row:
            td = row["tracking_data"] or {}
            if isinstance(td, str):
                td = json.loads(td)
            td["status"] = "cancelled"
            await update_tracking_data(tracking_id, td)
            return {"status": "ok", "message": "追踪已停止"}

        pr = await get_pending_review_by_thread(tracking_id)
        if pr:
            await cancel_pending_review(tracking_id)
            return {"status": "ok", "message": "已取消待复盘调度"}

        raise TrackingServiceError(404, "追踪不存在")
    except TrackingServiceError:
        raise
    except Exception as e:
        logger.exception("取消追踪失败")
        raise TrackingServiceError(500, "取消失败，请稍后重试") from e
