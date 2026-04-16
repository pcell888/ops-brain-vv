"""兼容层 /solutions 业务逻辑：方案列表/详情格式转换、plan_id → thread_id 解析。"""

from __future__ import annotations

import logging
from datetime import datetime

from src.agent.tools import clear_progress_sender, mcp_call, set_progress_sender
from src.core.config import CN_TZ, format_delay_minutes_zh, get_settings
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.runtime.graph_app import get_graph_app
from src.runtime.graph_app import astream_events_with_retry
from src.runtime.diagnosis_ws_manager import manager
from src.runtime.progress_store import progress_cache
from src.runtime.progress_store import write_progress_cache
from src.runtime.running_tasks import running_tasks
from src.core.diagnosis_report_repo import find_thread_id_by_plan_id, list_reports, update_plan_ids
from src.core.exec_task_repo import get_tasks_by_plan_id, list_distinct_plan_ids_for_thread, update_task_status
from src.worker.arq_queue import enqueue_adoption_job
from src.services import async_job_service

logger = logging.getLogger(__name__)

_WORKFLOW_NODES = frozenset(
    {
        "collect_data",
        "diagnose",
        "generate_solutions",
        "wait_adoption",
        "execute_plans",
        "track_effects",
    }
)

_PHASE_NAME = {
    "adoption": "采纳",
    "execution": "执行",
    "tracking": "追踪",
    "completed": "已完成",
}

_PHASE_OVERALL_RANGE = {
    "adoption": (60, 75),
    "execution": (75, 90),
    "tracking": (90, 99),
    "completed": (100, 100),
}


def _calc_overall_progress(phase: str, phase_progress: int) -> int:
    p = max(0, min(100, int(phase_progress)))
    lo, hi = _PHASE_OVERALL_RANGE.get(phase, (0, 100))
    if lo == hi:
        return lo
    return int(round(lo + (hi - lo) * (p / 100.0)))


def _adopt_progress_payload(
    *,
    thread_id: str,
    status: str,
    is_running: bool,
    percent: int,
    message: str,
    last_ts: str | None,
    event_type: str | None,
    node: str | None,
    pending: str | None,
    adopted: list[str],
    phase: str,
) -> dict:
    p = max(0, min(100, int(percent)))
    return {
        "thread_id": thread_id,
        "status": status,
        "phase": phase,
        "phase_name": _PHASE_NAME.get(phase, phase),
        "is_running": is_running,
        "percent": p,  # 兼容旧字段
        "progress": p,  # 阶段内进度
        "overall_progress": _calc_overall_progress(phase, p),
        "message": message,
        "last_timestamp": last_ts,
        "event_type": event_type,
        "node": node,
        "pending_adopt_plan_id": pending,
        "adopted_plan_ids": adopted,
    }


class SolutionServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _build_plan_detail(plan: dict, indicator_names: dict, adopted_ids: list[str]) -> dict:
    improvements = plan.get("expected_improvement", {})
    auto_actions = plan.get("auto_actions", [])
    steps = plan.get("steps", [])
    return {
        "plan_id": plan.get("plan_id"),
        "plan_name": plan.get("plan_name"),
        "description": plan.get("description"),
        "priority_level": plan.get("priority_level"),
        "adopted": plan.get("plan_id", "") in adopted_ids,
        "target_indicators": [{"code": c, "name": indicator_names.get(c, c)} for c in plan.get("target_indicators", [])],
        "metrics": {
            "expected_roi": plan.get("expected_roi", 0),
            "difficulty_score": plan.get("difficulty_score", 5),
            "urgency_score": plan.get("urgency_score", 5),
            "priority_score": round(plan.get("priority_score") or 0, 2),
        },
        "execution": {
            "step_count": len(steps),
            "steps": steps,
            "auto_action_count": len(auto_actions),
            "auto_action_types": list({a.get("type", "") for a in auto_actions}),
            "departments_involved": sorted({s.get("owner_dept", "") for s in steps if s.get("owner_dept")}),
        },
        "expected_improvements": [
            {"indicator": indicator_names.get(k, k), "code": k, "expected_pct": v} for k, v in improvements.items()
        ],
        "auto_actions": auto_actions,
    }


def _build_recommendation(plans: list[dict]) -> dict:
    if not plans:
        return {}
    best = max(plans, key=lambda p: p.get("priority_score", 0))
    reasons = []
    roi_vals = [p.get("expected_roi", 0) for p in plans]
    diff_vals = [p.get("difficulty_score", 10) for p in plans]
    urg_vals = [p.get("urgency_score", 0) for p in plans]
    if best.get("expected_roi", 0) >= max(roi_vals):
        reasons.append(f"ROI 最高（{best.get('expected_roi', 0)}）")
    if best.get("difficulty_score", 10) <= min(diff_vals):
        reasons.append(f"执行难度最低（{best.get('difficulty_score')}）")
    if best.get("urgency_score", 0) >= max(urg_vals):
        reasons.append(f"紧急度最高（{best.get('urgency_score')}）")
    if not reasons:
        reasons.append(f"综合优先级得分最高（{round(best.get('priority_score') or 0, 2)}）")
    return {"plan_id": best.get("plan_id"), "plan_name": best.get("plan_name"), "reasons": reasons}


def _parse_impl_steps(raw: dict) -> list[str]:
    impl = raw.get("implementation_steps") or []
    if not isinstance(impl, list):
        return []
    return [str(x).strip() for x in impl if str(x).strip()][:30]


def _normalize_steps(steps: list) -> list[dict]:
    out: list[dict] = []
    for i, raw in enumerate(steps or []):
        if not isinstance(raw, dict):
            continue
        try:
            step_no = int(raw.get("step", i + 1))
        except (TypeError, ValueError):
            step_no = i + 1
        action = raw.get("action") or raw.get("description") or ""
        out.append(
            {
                "step": step_no,
                "action": str(action).strip(),
                "owner_dept": str(raw.get("owner_dept", "") or "").strip(),
                "timeline": str(raw.get("timeline", "") or "").strip(),
                "data_context": str(raw.get("data_context", "") or "").strip(),
                "implementation_steps": _parse_impl_steps(raw),
            }
        )
    return out


def _step_timelines(steps: list) -> list[str]:
    out: list[str] = []
    for s in steps or []:
        if not isinstance(s, dict):
            continue
        t = str(s.get("timeline") or "").strip()
        if t:
            out.append(t)
    return out[:8]


def _plan_to_list_item(
    plan: dict,
    rank: int,
    anomalies: list,
    adopted_ids: set,
) -> dict:
    plan_id = plan.get("plan_id", "")
    steps = plan.get("steps") or []

    target_anomaly_ids = []
    for target_code in plan.get("target_indicators", []):
        for a in anomalies:
            if a.get("indicator_code") == target_code:
                target_anomaly_ids.append(a.get("indicator_code"))

    status = "adopted" if plan_id in adopted_ids else "pending"
    roi = plan.get("expected_roi")
    try:
        expected_roi = float(roi) if roi is not None else 0.0
    except (TypeError, ValueError):
        expected_roi = 0.0

    return {
        "rank": rank,
        "solution_id": plan_id,
        "name": plan.get("plan_name", f"方案{rank}"),
        "score": round(float(plan.get("priority_score", 0) or 0), 1),
        "expected_roi": round(expected_roi, 2),
        "difficulty_score": int(plan.get("difficulty_score", 5) or 5),
        "urgency_score": int(plan.get("urgency_score", 5) or 5),
        "priority_level": plan.get("priority_level", "medium"),
        "step_count": len(steps),
        "step_timelines": _step_timelines(steps),
        "steps": _normalize_steps(steps),
        "recommendation_reason": plan.get("description", ""),
        "estimated_cost": 0,
        "anomaly_ids": target_anomaly_ids,
        "status": status,
        "execution_plan": None,
    }


def _steps_to_tasks(solution_id: str, steps: list) -> list[dict]:
    tasks = []
    offset = 0
    for i, raw in enumerate(steps or []):
        if not isinstance(raw, dict):
            continue
        dur = raw.get("duration_days")
        try:
            dur_int = int(dur) if dur is not None else 7
        except (TypeError, ValueError):
            dur_int = 7
        if dur_int < 1:
            dur_int = 7
        step_no = raw.get("step", i + 1)
        name = f"步骤{step_no}" if step_no is not None else f"步骤{i + 1}"
        tasks.append(
            {
                "id": f"{solution_id}_task_{i}",
                "task_id": raw.get("task_id", f"step_{i}"),
                "name": name,
                "description": raw.get("action", "") or raw.get("description", ""),
                "owner_dept": raw.get("owner_dept", ""),
                "timeline": raw.get("timeline", ""),
                "data_context": raw.get("data_context", ""),
                "implementation_steps": _parse_impl_steps(raw),
                "duration_days": dur_int,
                "execution_type": raw.get("execution_type", "manual"),
                "dependencies": raw.get("dependencies", []),
                "start_offset": offset,
                "end_offset": offset + dur_int,
            }
        )
        offset += dur_int
    return tasks


def compat_active_generation_payload(diagnosis_id: str) -> dict:
    """兼容 GET /solutions/generate/active/{diagnosisId}；当前无异步队列。"""
    _ = diagnosis_id
    return {"task": None}


async def build_compat_solution_list(diagnosis_id: str) -> dict:
    app = await get_graph_app()
    config = {"configurable": {"thread_id": diagnosis_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}

    plans = values.get("solution_plans") or []
    adopted_ids = (values.get("adopted_plan_ids") or [])[:1]
    anomalies = values.get("anomalies") or []

    if not plans:
        task = running_tasks.get(diagnosis_id)
        is_running = (task is not None and not task.done()) or await running_tasks.is_running(diagnosis_id)
        if is_running:
            return {
                "diagnosis_id": diagnosis_id,
                "solutions": [],
                "total": 0,
                "generated_at": None,
                "ai_recommendation": None,
                "generating": True,
            }
        return {
            "diagnosis_id": diagnosis_id,
            "solutions": [],
            "total": 0,
            "generated_at": None,
            "ai_recommendation": None,
            "solution_generation_llm_usage": values.get("solution_generation_llm_usage"),
            "llm_usage_summary": values.get("llm_usage_summary"),
        }

    adopted_set = set(adopted_ids)
    solutions = [_plan_to_list_item(plan, rank, anomalies, adopted_set) for rank, plan in enumerate(plans, 1)]

    plan_ids = [p.get("plan_id") for p in plans if p.get("plan_id")]
    if plan_ids:
        try:
            await update_plan_ids(diagnosis_id, plan_ids)
        except Exception as e:
            logger.warning("同步 plan_ids 失败: %s", e)

    ai_recommendation = None
    if len(plans) >= 2:
        best = max(plans, key=lambda p: p.get("priority_score", 0))
        score = round(best.get("priority_score") or 0, 2)
        roi = best.get("expected_roi", 0)
        name = best.get("plan_name", "")
        ai_recommendation = {
            "recommended_solution_id": best.get("plan_id", ""),
            "reason": f"综合优先级得分最高（{score}），推荐方案「{name}」ROI 为 {roi}",
            "comparison_summary": "",
            "risk_warning": None,
        }

    return {
        "diagnosis_id": diagnosis_id,
        "solutions": solutions,
        "total": len(solutions),
        "generated_at": values.get("diagnosis_report", {}).get("generated_at"),
        "ai_recommendation": ai_recommendation,
        "solution_generation_llm_usage": values.get("solution_generation_llm_usage"),
        "llm_usage_summary": values.get("llm_usage_summary"),
    }


async def resolve_thread_id_for_plan(solution_id: str, *, prefer_wait_adoption: bool = False) -> str:
    """由 plan_id 解析诊断 thread_id。

    当 plan_id 在历史数据中重复时，可优先选择当前处于 wait_adoption 的诊断。
    """
    app = await get_graph_app()
    fallback_thread_id: str | None = None

    try:
        thread_id = await find_thread_id_by_plan_id(solution_id)
        if thread_id:
            config = {"configurable": {"thread_id": thread_id}}
            state = await app.aget_state(config)
            if state and state.values:
                plans = state.values.get("solution_plans") or []
                plan_ids = {p.get("plan_id") for p in plans}
                if solution_id in plan_ids:
                    if not prefer_wait_adoption or ("wait_adoption" in (state.next or [])):
                        return thread_id
                    fallback_thread_id = thread_id
    except Exception as e:
        logger.warning("从 plan_ids 索引查找失败: %s", e)

    page = 1
    page_size = 100
    while True:
        items, total = await list_reports(None, None, page, page_size)
        if not items:
            break

        for row in items:
            thread_id = row.get("thread_id", "")
            config = {"configurable": {"thread_id": thread_id}}
            try:
                state = await app.aget_state(config)
                if not state or not state.values:
                    continue
                plans = state.values.get("solution_plans") or []
                plan_ids = {p.get("plan_id") for p in plans}
                if solution_id in plan_ids:
                    if prefer_wait_adoption and ("wait_adoption" in (state.next or [])):
                        plan_id_list = [p.get("plan_id") for p in plans if p.get("plan_id")]
                        if plan_id_list:
                            try:
                                await update_plan_ids(thread_id, plan_id_list)
                            except Exception:
                                pass
                        return thread_id
                    if fallback_thread_id is None:
                        fallback_thread_id = thread_id
                    plan_id_list = [p.get("plan_id") for p in plans if p.get("plan_id")]
                    if plan_id_list:
                        try:
                            await update_plan_ids(thread_id, plan_id_list)
                        except Exception:
                            pass
            except Exception:
                continue

        if page * page_size >= total:
            break
        page += 1

    if fallback_thread_id:
        return fallback_thread_id

    raise SolutionServiceError(404, f"未找到包含方案 {solution_id} 的诊断")


async def get_solutions_payload(thread_id: str) -> dict:
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}
    next_nodes = list(state.next) if state and state.next else []
    plans = values.get("solution_plans") or []
    adopted_ids = (values.get("adopted_plan_ids") or [])[:1]
    anomalies = values.get("anomalies") or []
    indicator_names = {
        a["indicator_code"]: a.get("indicator_name", a["indicator_code"]) for a in anomalies if a.get("indicator_code")
    }
    if "wait_adoption" in next_nodes:
        status = "pending_adoption"
    elif adopted_ids:
        status = "adopted"
    elif not plans:
        status = "no_anomaly"
    else:
        status = "completed"
    return {
        "thread_id": thread_id,
        "status": status,
        "adopted_plan_ids": adopted_ids,
        "plan_count": len(plans),
        "plans": [_build_plan_detail(p, indicator_names, adopted_ids) for p in plans],
        "recommendation": _build_recommendation(plans) if len(plans) >= 2 else {},
        "solution_generation_llm_usage": values.get("solution_generation_llm_usage"),
        "llm_usage_summary": values.get("llm_usage_summary"),
    }


async def adopt_plan_and_enqueue(thread_id: str, plan_id: str) -> dict:
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    if not (state.next and "wait_adoption" in state.next):
        raise SolutionServiceError(400, "该诊断不在待采纳状态")

    all_plan_ids = {p.get("plan_id") for p in (state.values.get("solution_plans") or [])}
    if plan_id not in all_plan_ids:
        raise SolutionServiceError(400, f"无效的 plan_id: {plan_id}")

    existing_adopted = (state.values.get("adopted_plan_ids") or [])[:1]
    existing_pending = state.values.get("pending_adopt_plan_id")
    if existing_adopted and existing_adopted[0] == plan_id:
        raise SolutionServiceError(400, "该方案已采纳，无需重复提交")
    if existing_pending and existing_pending == plan_id:
        raise SolutionServiceError(400, "采纳任务已提交，请查询进度")
    if existing_adopted and existing_adopted[0] != plan_id:
        raise SolutionServiceError(400, "已有方案被采纳，不可再采纳其他方案")
    if existing_pending and existing_pending != plan_id:
        raise SolutionServiceError(400, "已有方案待采纳，不可再采纳其他方案")

    db_plan_ids = await list_distinct_plan_ids_for_thread(thread_id)
    if len(db_plan_ids) > 1:
        raise SolutionServiceError(400, "该诊断已存在多个方案的执行任务，仅允许单一方案")
    if len(db_plan_ids) == 1 and db_plan_ids[0] != plan_id:
        raise SolutionServiceError(400, "该诊断已绑定其他方案的执行任务，不可采纳当前方案")

    await app.aupdate_state(config, {"pending_adopt_plan_id": plan_id})
    tenant_id = str((state.values or {}).get("tenant_id") or "")
    if not tenant_id:
        raise SolutionServiceError(400, "缺少 tenant_id，无法派发执行任务")

    job_id = await enqueue_adoption_job(thread_id=thread_id)
    await async_job_service.register_enqueued_job(
        job_id=job_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
        job_kind="adoption",
        payload={"thread_id": thread_id},
    )
    await running_tasks.register_job(thread_id, tenant_id, job_id)
    return {"status": "resumed", "adopted_plan_id": plan_id}


async def get_adopt_execution_progress_payload(thread_id: str) -> dict:
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}
    next_nodes = list(state.next) if state and state.next else []
    wait_adopt = "wait_adoption" in next_nodes

    cached = (await progress_cache.aget(thread_id)) or {}
    event_type = cached.get("type")
    stage = cached.get("stage")
    message = str(cached.get("message", "") or "").strip()
    last_ts = cached.get("timestamp")
    pct_raw = cached.get("percent")
    try:
        percent = int(float(pct_raw)) if pct_raw is not None else None
    except (TypeError, ValueError):
        percent = None

    task = running_tasks.get(thread_id)
    is_running = (task is not None and not task.done()) or await running_tasks.is_running(thread_id)
    pending = values.get("pending_adopt_plan_id")
    adopted = (values.get("adopted_plan_ids") or [])[:1]
    node = cached.get("node") if isinstance(cached.get("node"), str) else None

    if stage == "execution" and event_type == "error":
        return _adopt_progress_payload(
            thread_id=thread_id,
            status="failed",
            is_running=False,
            percent=0,
            message=message or "采纳执行失败",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
            pending=pending,
            adopted=adopted,
            phase="execution",
        )
    if stage == "execution" and event_type == "completed":
        return _adopt_progress_payload(
            thread_id=thread_id,
            status="completed",
            is_running=False,
            percent=100,
            message=message or "方案执行任务已全部创建",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
            pending=pending,
            adopted=adopted,
            phase="execution",
        )
    if adopted and not pending and not wait_adopt:
        p = 100 if percent is None else max(0, min(100, percent))
        return _adopt_progress_payload(
            thread_id=thread_id,
            status="completed",
            is_running=is_running,
            percent=p,
            message=message or "方案执行任务已全部创建",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
            pending=pending,
            adopted=adopted,
            phase="execution",
        )
    if wait_adopt and not pending:
        return _adopt_progress_payload(
            thread_id=thread_id,
            status="pending_adoption",
            is_running=False,
            percent=0,
            message="方案已生成，等待采纳",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
            pending=pending,
            adopted=adopted,
            phase="adoption",
        )
    adoption_exec_running = is_running and (pending is not None or (stage == "execution"))
    if adoption_exec_running:
        p = 50 if percent is None else max(0, min(100, percent))
        return _adopt_progress_payload(
            thread_id=thread_id,
            status="running",
            is_running=True,
            percent=p,
            message=message or "正在执行采纳方案…",
            last_ts=last_ts,
            event_type=event_type,
            node=node,
            pending=pending,
            adopted=adopted,
            phase="execution",
        )
    return _adopt_progress_payload(
        thread_id=thread_id,
        status="idle",
        is_running=False,
        percent=0,
        message=message,
        last_ts=last_ts,
        event_type=event_type,
        node=node,
        pending=pending,
        adopted=adopted,
        phase="adoption",
    )


async def build_compat_solution_detail(solution_id: str) -> dict:
    app = await get_graph_app()

    items, _ = await list_reports(None, None, 1, 50)

    for row in items:
        thread_id = row.get("thread_id", "")
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = await app.aget_state(config)
            if not state or not state.values:
                continue
            plans = state.values.get("solution_plans") or []
            adopted_ids = (state.values.get("adopted_plan_ids") or [])[:1]
            anomalies = state.values.get("anomalies") or []

            for plan in plans:
                if plan.get("plan_id") != solution_id:
                    continue

                steps = plan.get("steps", [])
                improvements = plan.get("expected_improvement", {})
                try:
                    er = float(plan.get("expected_roi", 0) or 0)
                except (TypeError, ValueError):
                    er = 0.0

                related_anomalies = []
                for code in plan.get("target_indicators", []):
                    for a in anomalies:
                        if a.get("indicator_code") == code:
                            related_anomalies.append(
                                {
                                    "id": a.get("indicator_code"),
                                    "rule_name": a.get("indicator_name", code),
                                    "metric_name": code,
                                    "dimension": a.get("dimension", ""),
                                    "current_value": a.get("current_value", 0),
                                    "benchmark_value": a.get("benchmark_avg"),
                                    "gap_percentage": abs(a.get("deviation_pct", 0)),
                                    "severity": a.get("severity", "medium"),
                                }
                            )

                tasks = _steps_to_tasks(solution_id, steps)

                return {
                    "id": solution_id,
                    "name": plan.get("plan_name", ""),
                    "description": plan.get("description", ""),
                    "category": plan.get("priority_level", "medium"),
                    "executive_summary": plan.get("description", ""),
                    "problem_statement": "",
                    "solution_overview": plan.get("description", ""),
                    "expected_outcomes": "",
                    "implementation_roadmap": "",
                    "risk_assessment": "",
                    "success_criteria": "",
                    "estimated_impact": improvements,
                    "estimated_cost": 0,
                    "expected_roi": round(er, 2),
                    "difficulty_score": int(plan.get("difficulty_score", 5) or 5),
                    "urgency_score": int(plan.get("urgency_score", 5) or 5),
                    "step_count": len(steps),
                    "step_timelines": _step_timelines(steps),
                    "steps": _normalize_steps(steps),
                    "ranking_score": round(float(plan.get("priority_score", 0) or 0), 1),
                    "ranking_reason": "",
                    "status": "adopted" if solution_id in adopted_ids else "pending",
                    "related_anomalies": related_anomalies,
                    "tasks": tasks,
                    "execution_plan": None,
                    "created_at": state.values.get("diagnosis_report", {}).get("generated_at", ""),
                }
        except Exception:
            continue

    raise SolutionServiceError(404, f"方案 {solution_id} 不存在")


async def list_exec_tasks_by_plan_status(
    tenant_id: str,
    store_id: str,
    plan_id: str,
    status: str,
) -> list[dict]:
    return await get_tasks_by_plan_id(tenant_id, store_id, plan_id, status)


async def update_exec_tasks_status(task_ids: list[str], status: str) -> None:
    ids = [tid for tid in task_ids if tid]
    if ids:
        await update_task_status(ids, status)


async def _send_execution_progress(thread_id: str, payload: dict) -> None:
    payload_copy = dict(payload)
    payload_copy["timestamp"] = datetime.now(CN_TZ).isoformat()
    await progress_cache.aset(thread_id, payload_copy)
    await manager.send_progress(thread_id, payload_copy)


async def resume_after_adoption(thread_id: str, config: dict | None = None) -> None:
    if config is None:
        config = {"configurable": {"thread_id": thread_id}}

    adoption_completed_sent = False
    try:
        set_progress_sender(thread_id, manager, write_progress_cache)
        async for event in astream_events_with_retry(None, config):
            if await running_tasks.is_cancel_requested(thread_id):
                return
            if event["event"] != "on_chain_end":
                continue

            node_name = event.get("name", "")
            output = event.get("data", {}).get("output", {})

            if node_name not in _WORKFLOW_NODES:
                continue
            if node_name == "track_effects":
                continue

            if isinstance(output, dict) and "progress_messages" in output:
                for msg in output["progress_messages"]:
                    if isinstance(msg, dict) and msg.get("stage") == "effect_track":
                        continue
                    content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                    await _send_execution_progress(
                        thread_id,
                        {"type": "progress", "stage": "execution", "message": content},
                    )

            await _send_execution_progress(
                thread_id,
                {"type": "node_complete", "stage": "execution", "node": node_name},
            )

            if node_name == "execute_plans":
                delay = get_settings().effect_track_delay_minutes
                hint = format_delay_minutes_zh(delay)
                done_msg = (
                    f"方案执行任务已全部创建，效果追踪将在 {hint}后自动执行"
                    if delay > 0
                    else "方案执行任务已全部创建"
                )
                await _send_execution_progress(
                    thread_id,
                    {"type": "completed", "stage": "execution", "message": done_msg},
                )
                adoption_completed_sent = True
    except Exception as e:
        logger.exception("恢复执行异常 thread_id=%s", thread_id)
        await _send_execution_progress(
            thread_id,
            {
                "type": "error",
                "stage": "execution",
                "message": public_diagnosis_error_message(e),
            },
        )
        return
    finally:
        clear_progress_sender()

    if not adoption_completed_sent:
        app = await get_graph_app()
        state = await app.aget_state(config)
        if state.next and "track_effects" in state.next:
            delay = get_settings().effect_track_delay_minutes
            hint = format_delay_minutes_zh(delay)
            await _send_execution_progress(
                thread_id,
                {
                    "type": "completed",
                    "stage": "execution",
                    "message": f"方案执行任务已全部创建，效果追踪将在 {hint}后自动执行",
                },
            )
        else:
            await _send_execution_progress(
                thread_id,
                {
                    "type": "completed",
                    "stage": "execution",
                    "message": "方案执行任务已全部创建",
                },
            )


async def redistribute_plan_tasks(thread_id: str, plan_id: str) -> dict:
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state.values else {}

    tenant_id = values.get("tenant_id")
    store_id = values.get("store_id")
    if not tenant_id or not store_id:
        raise SolutionServiceError(400, "无法获取租户或门店信息")

    pending_tasks = await list_exec_tasks_by_plan_status(tenant_id, store_id, plan_id, "pending")
    failed_tasks = await list_exec_tasks_by_plan_status(tenant_id, store_id, plan_id, "failed")
    tasks_to_redistribute = pending_tasks + failed_tasks

    if not tasks_to_redistribute:
        raise SolutionServiceError(400, "没有需要重新派发的任务")

    redistributed = []
    failed_count = 0
    for task in tasks_to_redistribute:
        try:
            await mcp_call(
                "task-server",
                "create_execution_tasks",
                {
                    "tenant_id": tenant_id,
                    "store_id": store_id,
                    "plan_id": plan_id,
                    "tasks": [task],
                },
            )
            await update_exec_tasks_status([str(task.get("task_id") or "")], "running")
            redistributed.append(task.get("task_id"))
        except Exception as e:
            logger.warning("任务派发失败: task_id=%s, error=%s", task.get("task_id"), e)
            await update_exec_tasks_status([str(task.get("task_id") or "")], "failed")
            failed_count += 1

    remaining_pending = await list_exec_tasks_by_plan_status(tenant_id, store_id, plan_id, "pending")
    remaining_failed = await list_exec_tasks_by_plan_status(tenant_id, store_id, plan_id, "failed")
    all_success = len(remaining_pending) == 0 and len(remaining_failed) == 0

    if all_success:
        pending_id = values.get("pending_adopt_plan_id")
        if pending_id == plan_id:
            await app.aupdate_state(config, {"adopted_plan_ids": [plan_id], "pending_adopt_plan_id": None})

    return {
        "plan_id": plan_id,
        "redistributed_count": len(redistributed),
        "failed_count": failed_count,
        "remaining_pending": len(remaining_pending) + len(remaining_failed),
        "all_success": all_success,
    }
