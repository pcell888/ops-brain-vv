"""方案相关 HTTP 接口（获取方案列表、采纳方案、重新派发任务）。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from src.core.models import AdoptPlanRequest
from src.core.config import CN_TZ, get_settings
from src.api.deps import astream_events_with_retry, get_graph_app, manager, running_tasks, progress_cache
from src.agent.tools import set_progress_sender, clear_progress_sender
from src.core.exec_task_repo import get_tasks_by_plan_id, update_task_status
from src.core.diagnosis_errors import public_diagnosis_error_message
from src.agent.tools import mcp_call

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/solutions", tags=["方案"])

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


def _build_plan_detail(plan: dict, indicator_names: dict, adopted_ids: list[str]) -> dict:
    """为单个方案构建包含对比维度和采纳状态的详情。"""
    improvements = plan.get("expected_improvement", {})
    auto_actions = plan.get("auto_actions", [])
    steps = plan.get("steps", [])

    return {
        "plan_id": plan.get("plan_id"),
        "plan_name": plan.get("plan_name"),
        "description": plan.get("description"),
        "priority_level": plan.get("priority_level"),
        "adopted": plan.get("plan_id", "") in adopted_ids,
        "target_indicators": [
            {"code": c, "name": indicator_names.get(c, c)} for c in plan.get("target_indicators", [])
        ],
        "metrics": {
            "expected_roi": plan.get("expected_roi", 0),
            "difficulty_score": plan.get("difficulty_score", 5),
            "urgency_score": plan.get("urgency_score", 5),
            "priority_score": round(plan.get("priority_score", 0), 2),
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
    """从多个方案中选出推荐方案并给出理由。"""
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
        reasons.append(f"综合优先级得分最高（{round(best.get('priority_score', 0), 2)}）")
    return {
        "plan_id": best.get("plan_id"),
        "plan_name": best.get("plan_name"),
        "reasons": reasons,
    }


async def _get_state_values(thread_id: str) -> tuple[dict, list]:
    """获取 graph 状态，返回 (values, next_nodes)。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    values = state.values if state.values else {}
    next_nodes = list(state.next) if state.next else []
    return values, next_nodes


@router.get("/{thread_id}", summary="获取方案列表")
async def get_diagnosis_solutions(thread_id: str):
    """
    获取方案列表（含对比数据、采纳状态、AI推荐）。
    - 诊断完成后调用：展示所有方案 + 对比 + 推荐，status=pending_adoption
    - 已采纳后调用：展示所有方案 + 标记哪些已采纳，status=adopted
    """
    values, next_nodes = await _get_state_values(thread_id)
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

    plan_details = [_build_plan_detail(p, indicator_names, adopted_ids) for p in plans]
    recommendation = _build_recommendation(plans) if len(plans) >= 2 else {}

    return {
        "thread_id": thread_id,
        "status": status,
        "adopted_plan_ids": adopted_ids,
        "plan_count": len(plans),
        "plans": plan_details,
        "recommendation": recommendation,
    }


@router.post("/{thread_id}/adopt", summary="用户采纳方案")
async def adopt_plan(thread_id: str, request: AdoptPlanRequest):
    """用户采纳唯一方案（互斥）后继续执行。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}

    state = await app.aget_state(config)
    if not (state.next and "wait_adoption" in state.next):
        raise HTTPException(status_code=400, detail="该诊断不在待采纳状态")

    all_plan_ids = {p.get("plan_id") for p in (state.values.get("solution_plans") or [])}
    if request.plan_id not in all_plan_ids:
        raise HTTPException(status_code=400, detail=f"无效的 plan_id: {request.plan_id}")

    # 检查是否已有方案被采纳或待采纳
    existing_adopted = (state.values.get("adopted_plan_ids") or [])[:1]
    existing_pending = state.values.get("pending_adopt_plan_id")
    if existing_adopted and existing_adopted[0] != request.plan_id:
        raise HTTPException(400, detail="已有方案被采纳，不可再采纳其他方案")
    if existing_pending and existing_pending != request.plan_id:
        raise HTTPException(400, detail="已有方案待采纳，不可再采纳其他方案")

    # 仅记录用户选择，等待 MCP 推送成功后再更新 adopted_plan_ids
    await app.aupdate_state(config, {"pending_adopt_plan_id": request.plan_id})

    task = asyncio.create_task(_resume_after_adoption(thread_id, config))
    running_tasks[thread_id] = task
    task.add_done_callback(lambda _: running_tasks.pop(thread_id, None))

    return {"status": "resumed", "adopted_plan_id": request.plan_id}


async def _send_progress(thread_id: str, payload: dict):
    """发送进度并缓存，供重连时使用。"""
    # 写入缓存
    payload_copy = dict(payload)
    payload_copy["timestamp"] = datetime.now(CN_TZ).isoformat()
    progress_cache[thread_id] = payload_copy
    # 推送
    await manager.send_progress(thread_id, payload_copy)


async def _resume_after_adoption(thread_id: str, config: dict):
    """Resume LangGraph 执行。采纳蒙层只展示 execute_plans；track_effects 在后台进行，不推送到该 UI。"""
    adoption_completed_sent = False
    try:
        set_progress_sender(thread_id, manager)
        async for event in astream_events_with_retry(None, config):
            kind = event["event"]
            if kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event.get("data", {}).get("output", {})

                if node_name not in _WORKFLOW_NODES:
                    continue

                # 效果追踪（复盘）进度不进入「采纳并执行」WebSocket 蒙层
                if node_name == "track_effects":
                    continue

                if isinstance(output, dict) and "progress_messages" in output:
                    for msg in output["progress_messages"]:
                        if isinstance(msg, dict) and msg.get("stage") == "effect_track":
                            continue
                        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                        await _send_progress(
                            thread_id,
                            {
                                "type": "progress",
                                "stage": "execution",
                                "message": content,
                            },
                        )

                await _send_progress(
                    thread_id,
                    {
                        "type": "node_complete",
                        "stage": "execution",
                        "node": node_name,
                    },
                )

                if node_name == "execute_plans":
                    delay = get_settings().effect_track_delay_days
                    if delay > 0:
                        done_msg = f"方案执行任务已全部创建，效果追踪将在 {delay} 天后自动执行"
                    else:
                        done_msg = "方案执行任务已全部创建"
                    await _send_progress(
                        thread_id,
                        {
                            "type": "completed",
                            "stage": "execution",
                            "message": done_msg,
                        },
                    )
                    adoption_completed_sent = True
    except Exception as e:
        logger.exception("恢复执行异常 thread_id=%s", thread_id)
        await _send_progress(
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
            delay = get_settings().effect_track_delay_days
            await _send_progress(
                thread_id,
                {
                    "type": "completed",
                    "stage": "execution",
                    "message": f"方案执行任务已全部创建，效果追踪将在 {delay} 天后自动执行",
                },
            )
        else:
            await _send_progress(
                thread_id,
                {
                    "type": "completed",
                    "stage": "execution",
                    "message": "方案执行任务已全部创建",
                },
            )


@router.post("/{thread_id}/plans/{plan_id}/redistribute", summary="重新派发任务")
async def redistribute_tasks(thread_id: str, plan_id: str):
    """手动重新派发指定方案的任务（仅派发 pending/failed 状态的任务）。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": thread_id}}

    state = await app.aget_state(config)
    values = state.values if state.values else {}

    tenant_id = values.get("tenant_id")
    store_id = values.get("store_id")
    if not tenant_id or not store_id:
        raise HTTPException(status_code=400, detail="无法获取租户或门店信息")

    # 获取待派发的任务
    pending_tasks = await get_tasks_by_plan_id(tenant_id, store_id, plan_id, "pending")
    failed_tasks = await get_tasks_by_plan_id(tenant_id, store_id, plan_id, "failed")
    tasks_to_redistribute = pending_tasks + failed_tasks

    if not tasks_to_redistribute:
        raise HTTPException(status_code=400, detail="没有需要重新派发的任务")

    # 尝试重新派发
    redistributed = []
    failed_count = 0
    for task in tasks_to_redistribute:
        try:
            result = await mcp_call(
                "task-server",
                "create_execution_tasks",
                {
                    "tenant_id": tenant_id,
                    "store_id": store_id,
                    "plan_id": plan_id,
                    "tasks": [task],
                },
            )
            # 派发成功，更新状态为 running
            await update_task_status([task.get("task_id")], "running")
            redistributed.append(task.get("task_id"))
        except Exception as e:
            logger.warning("任务派发失败: task_id=%s, error=%s", task.get("task_id"), e)
            # 派发失败，更新状态为 failed
            await update_task_status([task.get("task_id")], "failed")
            failed_count += 1

    # 检查是否所有任务都派发成功
    remaining_pending = await get_tasks_by_plan_id(tenant_id, store_id, plan_id, "pending")
    remaining_failed = await get_tasks_by_plan_id(tenant_id, store_id, plan_id, "failed")
    all_success = len(remaining_pending) == 0 and len(remaining_failed) == 0

    # 如果所有任务都派发成功，更新 adopted_plan_ids
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
