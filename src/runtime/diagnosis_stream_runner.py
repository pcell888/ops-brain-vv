"""流式执行诊断管道并推送进度。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.agent.progress import clear_progress_sender, set_progress_sender
from src.core.config import CN_TZ, log_diagnosis_run_context
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.core.diagnosis_engine import Phase, run_diagnosis_pipeline
from src.core.tracing import get_tracer

from .diagnosis_ws_manager import manager
from .progress_store import progress_cache, write_progress_cache
from .running_tasks import running_tasks

logger = logging.getLogger(__name__)
tracer = get_tracer("diagnosis")

_PHASE_START_PERCENT = {
    Phase.COLLECTING: 5,
    Phase.DIAGNOSING: 35,
    Phase.GENERATING: 70,
}

_PHASE_COMPLETE_PERCENT = {
    Phase.COLLECTING: 35,
    Phase.DIAGNOSING: 70,
    Phase.GENERATING: 100,
}

_PHASE_START_MESSAGE = {
    Phase.COLLECTING: "开始采集运营数据",
    Phase.DIAGNOSING: "开始诊断分析",
    Phase.GENERATING: "正在生成优化方案",
}

_PHASE_COMPLETE_MESSAGE = {
    Phase.COLLECTING: "数据采集完成",
    Phase.DIAGNOSING: "根因分析完成",
    Phase.GENERATING: "方案生成完成",
}


async def run_diagnosis_with_stream(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
    auth_token: str | None = None,
) -> None:
    log_diagnosis_run_context(
        logger,
        thread_id=thread_id,
        tenant_id=tenant_id,
        store_id=store_id,
        trigger_type=trigger_type,
    )

    try:
        with tracer.start_as_current_span(
            "diagnosis.run",
            attributes={
                "diagnosis.thread_id": thread_id,
                "diagnosis.tenant_id": tenant_id,
                "diagnosis.store_id": store_id,
                "diagnosis.trigger_type": trigger_type,
            },
        ) as _:
            await progress_cache.aclear_run(thread_id)
            set_progress_sender(thread_id, manager, write_progress_cache)
            started_ts = datetime.now(CN_TZ).isoformat()
            write_progress_cache(
                thread_id,
                {
                    "type": "progress",
                    "message": "已启动诊断任务",
                    "percent": 5,
                    "timestamp": started_ts,
                },
            )
            await manager.send_progress(
                thread_id,
                {
                    "type": "progress",
                    "message": "已启动诊断任务",
                    "percent": 5,
                    "timestamp": started_ts,
                },
            )

            await _run_pipeline_with_progress(
                thread_id=thread_id,
                tenant_id=tenant_id,
                store_id=store_id,
                trigger_type=trigger_type,
                triggered_by=triggered_by,
                selected_dimensions=selected_dimensions,
                selected_indicators=selected_indicators,
                auth_token=auth_token,
            )

    except asyncio.CancelledError:
        logger.info("诊断流程已取消: thread=%s", thread_id)
        raise
    except Exception as e:
        logger.exception("诊断流程异常 thread=%s", thread_id)
        err_msg = public_diagnosis_error_message(e)
        await progress_cache.aset(
            thread_id,
            {
                "type": "error",
                "message": err_msg,
                "percent": 0,
                "timestamp": datetime.now(CN_TZ).isoformat(),
            },
        )
        await manager.send_progress(
            thread_id,
            {
                "type": "error",
                "message": err_msg,
                "timestamp": datetime.now(CN_TZ).isoformat(),
            },
        )
        raise
    finally:
        clear_progress_sender()


async def _run_pipeline_with_progress(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
    auth_token: str | None = None,
) -> None:
    from src.core.diagnosis_engine import Phase, run_phase
    from src.repositories.diagnosis_session import (
        create_session,
        get_session,
        update_session_phase,
        update_session_state,
    )

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
    phases = [Phase.COLLECTING, Phase.DIAGNOSING, Phase.GENERATING]

    for phase in phases:
        if await running_tasks.is_cancel_requested(thread_id):
            raise asyncio.CancelledError()

        await update_session_phase(thread_id, phase, state)

        if phase in _PHASE_START_MESSAGE:
            start_payload = {
                "type": "node_start",
                "node": phase.value,
                "timestamp": datetime.now(CN_TZ).isoformat(),
            }
            if phase in _PHASE_START_PERCENT:
                start_payload["percent"] = _PHASE_START_PERCENT[phase]
            if phase in _PHASE_START_MESSAGE:
                start_payload["message"] = _PHASE_START_MESSAGE[phase]
                if phase not in (Phase.GENERATING, Phase.DIAGNOSING):
                    write_progress_cache(
                        thread_id,
                        {
                            "type": "progress",
                            "message": _PHASE_START_MESSAGE[phase],
                            "percent": start_payload.get("percent"),
                            "timestamp": start_payload["timestamp"],
                        },
                    )
            await manager.send_progress(thread_id, start_payload)

        result = await run_phase(thread_id, phase, state)
        if not isinstance(result, dict):
            result = {}
        state.update(result)
        await update_session_state(thread_id, result)

        if phase in _PHASE_COMPLETE_MESSAGE:
            complete_payload = {
                "type": "node_complete",
                "node": phase.value,
                "timestamp": datetime.now(CN_TZ).isoformat(),
            }
            if phase in _PHASE_COMPLETE_PERCENT:
                complete_payload["percent"] = _PHASE_COMPLETE_PERCENT[phase]
            if phase in _PHASE_COMPLETE_MESSAGE:
                complete_payload["message"] = _PHASE_COMPLETE_MESSAGE[phase]
                if phase not in (Phase.DIAGNOSING, Phase.COLLECTING):
                    write_progress_cache(
                        thread_id,
                        {
                            "type": "progress",
                            "message": _PHASE_COMPLETE_MESSAGE[phase],
                            "percent": complete_payload.get("percent"),
                            "timestamp": complete_payload["timestamp"],
                        },
                    )
            await manager.send_progress(thread_id, complete_payload)

        if phase == Phase.DIAGNOSING and isinstance(result, dict) and "health_score" in result:
            await manager.send_progress(
                thread_id,
                {
                    "type": "diagnosis_result",
                    "health_score": result["health_score"],
                    "anomaly_count": len(result.get("anomalies", [])),
                    "dimension_scores": result.get("dimension_scores"),
                },
            )

        if phase == Phase.GENERATING and isinstance(result, dict) and "solution_plans" in result:
            await manager.send_progress(
                thread_id,
                {
                    "type": "solutions_ready",
                    "plans": result["solution_plans"],
                },
            )

    anomalies = state.get("anomalies")
    plans = state.get("solution_plans")
    if anomalies and plans:
        await update_session_phase(thread_id, Phase.WAITING_ADOPTION, state)
        await manager.send_progress(
            thread_id,
            {
                "type": "completed",
                "message": "方案已生成，请选择需要采纳的方案",
                "percent": 100,
            },
        )
    else:
        await update_session_phase(thread_id, Phase.COMPLETED, state)
        await manager.send_progress(
            thread_id,
            {
                "type": "completed",
                "message": "诊断流程已完成",
                "percent": 100,
            },
        )
