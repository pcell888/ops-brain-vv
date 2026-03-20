"""前端兼容层 — /solutions 系列接口。

将后端 plan-based 方案数据转换为前端 SolutionGenerateResponse 格式。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.api.deps import get_graph_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/solutions", tags=["方案(兼容层)"])


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
    adopted_ids = values.get("adopted_plan_ids") or []
    anomalies = values.get("anomalies") or []

    if not plans:
        return {
            "diagnosis_id": diagnosis_id,
            "solutions": [],
            "total": 0,
            "generated_at": None,
            "ai_recommendation": None,
        }

    solutions = []
    for rank, plan in enumerate(plans, 1):
        plan_id = plan.get("plan_id", "")
        improvements = plan.get("expected_improvement", {})
        steps = plan.get("steps", [])

        target_anomaly_ids = []
        for target_code in plan.get("target_indicators", []):
            for a in anomalies:
                if a.get("indicator_code") == target_code:
                    target_anomaly_ids.append(a.get("indicator_code"))

        status = "adopted" if plan_id in adopted_ids else "pending"

        solutions.append({
            "rank": rank,
            "solution_id": plan_id,
            "name": plan.get("plan_name", f"方案{rank}"),
            "score": round(plan.get("priority_score", 0), 1),
            "recommendation_reason": plan.get("description", ""),
            "estimated_cost": 0,
            "estimated_duration": len(steps) * 7,
            "success_rate": min(0.95, 0.6 + plan.get("expected_roi", 0) * 0.01),
            "anomaly_ids": target_anomaly_ids,
            "status": status,
            "execution_plan": None,
        })

    ai_recommendation = None
    if len(plans) >= 2:
        best = max(plans, key=lambda p: p.get("priority_score", 0))
        ai_recommendation = {
            "recommended_solution_id": best.get("plan_id", ""),
            "reason": f"综合优先级得分最高（{round(best.get('priority_score', 0), 2)}）",
            "comparison_summary": f"共 {len(plans)} 个方案，推荐方案「{best.get('plan_name', '')}」ROI 为 {best.get('expected_roi', 0)}",
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
            adopted_ids = state.values.get("adopted_plan_ids") or []
            anomalies = state.values.get("anomalies") or []

            for plan in plans:
                if plan.get("plan_id") != solution_id:
                    continue

                steps = plan.get("steps", [])
                improvements = plan.get("expected_improvement", {})

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
                                "solution_tags": [],
                            })

                tasks = []
                offset = 0
                for i, step in enumerate(steps):
                    dur = step.get("duration_days", 7)
                    tasks.append({
                        "id": f"{solution_id}_task_{i}",
                        "task_id": step.get("task_id", f"step_{i}"),
                        "name": step.get("name", f"步骤{i+1}"),
                        "description": step.get("description", ""),
                        "duration_days": dur,
                        "execution_type": step.get("execution_type", "manual"),
                        "dependencies": step.get("dependencies", []),
                        "start_offset": offset,
                        "end_offset": offset + dur,
                    })
                    offset += dur

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
                    "estimated_duration": sum(s.get("duration_days", 7) for s in steps) if steps else 14,
                    "success_rate": min(0.95, 0.6 + plan.get("expected_roi", 0) * 0.01),
                    "ranking_score": round(plan.get("priority_score", 0), 1),
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
