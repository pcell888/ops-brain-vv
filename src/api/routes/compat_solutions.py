"""前端兼容层 — /solutions 系列接口。

将后端 plan-based 方案数据转换为前端 SolutionGenerateResponse 格式。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.api.deps import get_graph_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/solutions", tags=["方案(兼容层)"])


def _parse_impl_steps(raw: dict) -> list[str]:
    impl = raw.get("implementation_steps") or []
    if not isinstance(impl, list):
        return []
    return [str(x).strip() for x in impl if str(x).strip()][:30]


def _normalize_steps(steps: list) -> list[dict]:
    """与 LLM 约定一致：step / action / owner_dept / timeline / data_context / implementation_steps。"""
    out: list[dict] = []
    for i, raw in enumerate(steps or []):
        if not isinstance(raw, dict):
            continue
        try:
            step_no = int(raw.get("step", i + 1))
        except (TypeError, ValueError):
            step_no = i + 1
        action = raw.get("action") or raw.get("description") or ""
        out.append({
            "step": step_no,
            "action": str(action).strip(),
            "owner_dept": str(raw.get("owner_dept", "") or "").strip(),
            "timeline": str(raw.get("timeline", "") or "").strip(),
            "data_context": str(raw.get("data_context", "") or "").strip(),
            "implementation_steps": _parse_impl_steps(raw),
        })
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
        tasks.append({
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
        })
        offset += dur_int
    return tasks


@router.get("/generate/active/{diagnosis_id}", summary="活跃生成任务(兼容)")
async def compat_active_generation(diagnosis_id: str):
    """兼容前端 GET /solutions/generate/active/{diagnosisId}。

    当前后端不使用异步生成队列，直接返回无活跃任务。
    """
    return {"task": None}


@router.get("/list/{diagnosis_id}", summary="方案列表(兼容)")
async def compat_solution_list(diagnosis_id: str):
    """兼容前端 GET /solutions/list/{diagnosisId}。

    将后端 plans[] 转换为前端 SolutionGenerateResponse 格式。
    """
    app = await get_graph_app()
    config = {"configurable": {"thread_id": diagnosis_id}}
    state = await app.aget_state(config)
    values = state.values if state and state.values else {}

    plans = values.get("solution_plans") or []
    adopted_ids = (values.get("adopted_plan_ids") or [])[:1]
    anomalies = values.get("anomalies") or []

    if not plans:
        return {
            "diagnosis_id": diagnosis_id,
            "solutions": [],
            "total": 0,
            "generated_at": None,
            "ai_recommendation": None,
        }

    adopted_set = set(adopted_ids)
    solutions = [
        _plan_to_list_item(plan, rank, anomalies, adopted_set)
        for rank, plan in enumerate(plans, 1)
    ]

    ai_recommendation = None
    if len(plans) >= 2:
        best = max(plans, key=lambda p: p.get("priority_score", 0))
        score = round(best.get("priority_score", 0), 2)
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
    }


@router.put("/{solution_id}/adopt", summary="采纳方案(兼容)")
async def compat_adopt_solution(solution_id: str):
    """兼容前端 PUT /solutions/{solutionId}/adopt。

    前端按 solution_id（即 plan_id）采纳，后端需要 thread_id + plan_id。
    遍历 running_tasks 和 graph state 找到包含该 plan_id 的 thread。
    """
    from src.api.routes.solutions import adopt_plan
    from src.core.models import AdoptPlanRequest

    app = await get_graph_app()

    from src.core.diagnosis_report_repo import list_reports
    items, _ = await list_reports(None, None, 1, 50)

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
                return await adopt_plan(thread_id, AdoptPlanRequest(plan_id=solution_id))
        except Exception:
            continue

    raise HTTPException(status_code=404, detail=f"未找到包含方案 {solution_id} 的诊断")


@router.get("/detail/{solution_id}", summary="方案详情(兼容)")
async def compat_solution_detail(solution_id: str):
    """兼容前端 GET /solutions/detail/{solutionId}。

    从 graph state 中查找方案详情。
    """
    app = await get_graph_app()
    from src.core.diagnosis_report_repo import list_reports

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
                            related_anomalies.append({
                                "id": a.get("indicator_code"),
                                "rule_name": a.get("indicator_name", code),
                                "metric_name": code,
                                "dimension": a.get("dimension", ""),
                                "current_value": a.get("current_value", 0),
                                "benchmark_value": a.get("benchmark_avg"),
                                "gap_percentage": abs(a.get("deviation_pct", 0)),
                                "severity": a.get("severity", "medium"),
                            })

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

    raise HTTPException(status_code=404, detail=f"方案 {solution_id} 不存在")
