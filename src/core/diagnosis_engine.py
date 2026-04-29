"""诊断状态机引擎 — 替代 LangGraph StateGraph 的线性管道编排。

Phase 枚举与转换规则：
  collecting → diagnosing → generating → waiting_adoption → executing → waiting_track → completed

中断点：
  - waiting_adoption: 等待用户采纳方案
  - waiting_track: 等待定时复盘调度

本模块与 LangGraph 完全解耦，节点函数签名不变。
效果追踪复盘由 tracking_lifecycle 统一处理。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum

from src.core.config import CN_TZ, get_settings
from src.repositories.diagnosis_session import (
    create_session,
    get_session,
    update_session_phase,
)
from src.repositories.tracking import create_tracking, get_tracking

logger = logging.getLogger(__name__)


class Phase(str, Enum):
    COLLECTING = "collecting"
    DIAGNOSING = "diagnosing"
    GENERATING = "generating"
    WAITING_ADOPTION = "waiting_adoption"
    EXECUTING = "executing"
    WAITING_TRACK = "waiting_track"
    TRACKING = "tracking"
    COMPLETED = "completed"
    FAILED = "failed"


PHASE_TO_NEXT_NODES = {
    Phase.COLLECTING: ["collect_data"],
    Phase.DIAGNOSING: ["diagnose"],
    Phase.GENERATING: ["generate_solutions"],
    Phase.WAITING_ADOPTION: ["wait_adoption"],
    Phase.EXECUTING: ["execute_plans"],
    Phase.WAITING_TRACK: ["track_effects"],
    Phase.TRACKING: ["track_effects"],
    Phase.COMPLETED: [],
    Phase.FAILED: [],
}


def phase_to_next_nodes(phase: str | None) -> list[str]:
    if phase is None:
        return []
    return PHASE_TO_NEXT_NODES.get(Phase(phase), [])


async def run_phase(thread_id: str, phase: Phase, state: dict) -> dict:
    if phase == Phase.COLLECTING:
        from src.agent.nodes.collect import collect_data_node
        return await collect_data_node(state)
    elif phase == Phase.DIAGNOSING:
        from src.agent.nodes.diagnose import diagnose_node
        return await diagnose_node(state)
    elif phase == Phase.GENERATING:
        from src.agent.nodes.generate import generate_solutions_node
        return await generate_solutions_node(state)
    elif phase == Phase.EXECUTING:
        from src.agent.nodes.execute import execute_plans_node
        return await execute_plans_node(state)
    else:
        logger.warning("run_phase: 不可执行的阶段 %s, thread_id=%s", phase, thread_id)
        return {}


async def _ensure_tracking_for_diagnosis(thread_id: str) -> str:
    existing = await get_tracking(thread_id)
    if existing:
        return thread_id

    session = await get_session(thread_id)
    if not session:
        raise RuntimeError(f"诊断会话不存在: {thread_id}")

    state = _session_state(session)
    tenant_id = state.get("tenant_id", "")
    store_id = state.get("store_id", "")

    adopted_ids = (state.get("adopted_plan_ids") or [])[:1]
    primary_plan_id = ""
    if adopted_ids:
        plans = state.get("solution_plans", [])
        primary_plan = next((p for p in plans if p.get("plan_id") in adopted_ids), {})
        primary_plan_id = str(primary_plan.get("plan_id") or "")

    tracking_data = {
        "plan_id": primary_plan_id,
        "status": "active",
        "current_score": None,
        "snapshot_count": 0,
        "started_at": datetime.now(CN_TZ).isoformat(),
        "last_snapshot_at": None,
        "completed_at": None,
    }

    now = datetime.now(CN_TZ)
    await create_tracking(
        thread_id=thread_id,
        tenant_id=tenant_id,
        store_id=store_id,
        tracking_data=tracking_data,
        created_at=now,
    )
    return thread_id


async def run_diagnosis_pipeline(
    thread_id: str,
    tenant_id: str,
    store_id: str = "",
    trigger_type: str = "manual",
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
    auth_token: str | None = None,
) -> None:
    """从 collecting 执行到第一个中断点或完成。供 ARQ Worker / 周度诊断调用。"""
    initial_state = {
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "store_id": store_id,
        "trigger_type": trigger_type,
        "triggered_by": triggered_by,
        "selected_dimensions": selected_dimensions,
        "selected_indicators": selected_indicators,
        "auth_token": auth_token,
        "progress_messages": [],
    }

    await create_session(
        thread_id=thread_id,
        tenant_id=tenant_id,
        store_id=store_id,
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        selected_dimensions=selected_dimensions,
        selected_indicators=selected_indicators,
        auth_token=auth_token,
        phase=Phase.COLLECTING,
        state_json=initial_state,
    )

    state = dict(initial_state)
    phase = Phase.COLLECTING

    while phase not in (Phase.WAITING_ADOPTION, Phase.WAITING_TRACK, Phase.COMPLETED, Phase.FAILED):
        await update_session_phase(thread_id, phase, state)
        try:
            result = await run_phase(thread_id, phase, state)
        except Exception as e:
            logger.exception("诊断阶段 %s 执行失败 thread_id=%s", phase, thread_id)
            await update_session_phase(thread_id, Phase.FAILED, {"error": str(e)[:2000]})
            raise

        if not isinstance(result, dict):
            result = {}
        state.update(result)

        next_phase = _resolve_next_phase(phase, state)
        phase = next_phase

    await update_session_phase(thread_id, phase, state)


async def resume_after_adoption(thread_id: str) -> None:
    """采纳方案后恢复执行：executing → waiting_track → completed。

    效果追踪复盘由 tracking_lifecycle 统一处理：
    - delay > 0: 进入 waiting_track，后续由定时复盘或手动触发完成
    - delay = 0: 立即委托 tracking_lifecycle 完成追踪
    """
    session = await get_session(thread_id)
    if not session:
        raise RuntimeError(f"诊断会话不存在: {thread_id}")

    state = _session_state(session)
    phase = Phase(session["phase"])

    if phase == Phase.WAITING_ADOPTION:
        phase = Phase.EXECUTING
    elif phase != Phase.EXECUTING:
        logger.warning("resume_after_adoption: 非预期阶段 %s, thread_id=%s", phase, thread_id)
        return

    await update_session_phase(thread_id, phase, state)

    try:
        result = await run_phase(thread_id, Phase.EXECUTING, state)
        if isinstance(result, dict):
            state.update(result)
    except Exception:
        logger.exception("执行阶段失败 thread_id=%s", thread_id)
        await update_session_phase(thread_id, Phase.FAILED, state)
        raise

    delay = float(get_settings().effect_track_delay_days)
    if delay > 0:
        await update_session_phase(thread_id, Phase.WAITING_TRACK, state)
    else:
        await update_session_phase(thread_id, Phase.TRACKING, state)
        try:
            tracking_id = await _ensure_tracking_for_diagnosis(thread_id)
            from src.services.tracking_lifecycle import _complete_tracking_background
            await _complete_tracking_background(tracking_id)
        except Exception:
            logger.exception("追踪阶段失败 thread_id=%s", thread_id)
            await update_session_phase(thread_id, Phase.FAILED, state)
            raise
        await update_session_phase(thread_id, Phase.COMPLETED, state)


async def resume_track_effects(thread_id: str) -> None:
    """恢复效果追踪：委托 tracking_lifecycle 完成追踪并推送通知。"""
    session = await get_session(thread_id)
    if not session:
        raise RuntimeError(f"诊断会话不存在: {thread_id}")

    state = _session_state(session)
    phase = Phase(session["phase"])

    if phase == Phase.WAITING_TRACK:
        phase = Phase.TRACKING
    elif phase != Phase.TRACKING:
        logger.warning("resume_track_effects: 非预期阶段 %s, thread_id=%s", phase, thread_id)
        return

    await update_session_phase(thread_id, phase, state)

    try:
        tracking_id = await _ensure_tracking_for_diagnosis(thread_id)
        from src.services.tracking_lifecycle import _complete_tracking_background
        await _complete_tracking_background(tracking_id)
    except Exception as e:
        logger.exception("追踪阶段失败 thread_id=%s", thread_id)
        await update_session_phase(thread_id, Phase.FAILED, {"error": str(e)[:2000]})
        raise

    await update_session_phase(thread_id, Phase.COMPLETED, state)


def _resolve_next_phase(current: Phase, state: dict) -> Phase:
    if current == Phase.COLLECTING:
        return Phase.DIAGNOSING
    elif current == Phase.DIAGNOSING:
        return Phase.GENERATING
    elif current == Phase.GENERATING:
        anomalies = state.get("anomalies")
        plans = state.get("solution_plans")
        if anomalies and plans:
            return Phase.WAITING_ADOPTION
        return Phase.COMPLETED
    elif current == Phase.EXECUTING:
        delay = float(get_settings().effect_track_delay_days)
        if delay > 0:
            return Phase.WAITING_TRACK
        return Phase.TRACKING
    elif current == Phase.TRACKING:
        return Phase.COMPLETED
    return current


def _session_state(session: dict) -> dict:
    raw = session.get("state_json")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}