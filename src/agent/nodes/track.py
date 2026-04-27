"""效果追踪节点 — 对比方案执行前后的指标变化，生成复盘报告。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from typing import Any

from src.agent.constants import DIMENSION_STATE_KEY
from src.agent.state import DiagnosisState
from src.agent.progress import emit_progress
from src.biz.client import tenant_client
from src.agent.prompts.review_analysis import REVIEW_ANALYSIS_SYSTEM, REVIEW_ANALYSIS_USER
from src.core.calculator import calculate_effect_changes, resolve_active_indicators
from src.agent.utils import get_admin_accounts as _get_admin_accounts
from src.core.config import CN_TZ, get_settings
from src.core.llm_caller import llm_call_json
from src.repositories.push_log import save_push_log
from src.repositories.effect_review import get_tracking, save_effect_tracking, save_review_report
from src.repositories.snapshot import list_snapshots
from src.repositories.solution_knowledge import save_effective_plan
from src.core.tracking_names import resolve_solution_name
from src.core.tenant_config import get_tenant_config

logger = logging.getLogger(__name__)


async def _llm_generate_review(
    tracking_data: dict,
    plans: list[dict],
    exec_tasks: list[dict],
    snapshots: list[dict] | None = None,
    *,
    runnable_config: Any | None = None,
) -> tuple[dict, dict | None]:
    settings = get_settings()
    if not settings.llm_enabled:
        logger.info("LLM_ENABLED=false，跳过复盘LLM分析")
        return {
            "overall_achievement_rate": 0,
            "improved_indicator_count": 0,
            "total_tracked_indicators": 0,
            "summary": "LLM未启用，无法生成复盘报告",
            "lessons_learned": [],
        }, None
    snapshots_text = ""
    if snapshots:
        snapshots_text = json.dumps(snapshots, ensure_ascii=False, indent=2)

    user_msg = REVIEW_ANALYSIS_USER.format(
        tracking_data=json.dumps(tracking_data, ensure_ascii=False, indent=2),
        plans=json.dumps(plans, ensure_ascii=False, indent=2),
        exec_tasks=json.dumps(exec_tasks, ensure_ascii=False, indent=2),
        snapshots=snapshots_text,
    )
    logger.info("LLM复盘分析输入: %d chars", len(user_msg))

    try:
        parsed, raw_text, usage = await llm_call_json(
            system_prompt=REVIEW_ANALYSIS_SYSTEM,
            user_prompt=user_msg,
            label="LLM复盘分析",
            temperature=0.3,
            runnable_config=runnable_config,
            model=get_settings().llm_model_review,
        )
    except Exception as e:
        logger.warning("LLM 复盘报告调用失败（如 403 请检查 API Key/工作区权限）: %s", e)
        return {
            "overall_achievement_rate": 0,
            "improved_indicator_count": 0,
            "total_tracked_indicators": 0,
            "summary": f"复盘生成暂不可用: {e!s}",
            "lessons_learned": [],
        }, None

    if isinstance(parsed, dict):
        return parsed, usage

    logger.warning("LLM复盘报告输出解析失败")
    return {
        "overall_achievement_rate": 0,
        "improved_indicator_count": 0,
        "total_tracked_indicators": 0,
        "summary": raw_text,
        "lessons_learned": [],
    }, usage


async def track_effects_node(state: DiagnosisState, config: Any = None) -> dict:
    emit_progress(state, "正在采集最新指标数据进行效果对比...", for_adoption_ui=False)

    active_dims, _active_inds = resolve_active_indicators(
        state.get("selected_dimensions"),
        state.get("selected_indicators"),
    )

    tenant_id = state["tenant_id"]
    store_id = state["store_id"]
    settings = get_settings()
    tenant_config = await get_tenant_config(tenant_id)
    lookback_days = int(tenant_config.get("analysis_period_days") or settings.diagnosis_lookback_days)
    _now = datetime.now(CN_TZ)
    now = _now.strftime("%Y-%m-%d %H:%M:%S")
    start = (_now - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")

    common_args = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "start_date": start,
        "end_date": now,
    }

    results = await asyncio.gather(*tasks)
    dim_results = dict(zip(ordered_dims, results))

    after = {dim: dim_results.get(dim, {}) for dim in ordered_dims}
    before = {dim: state.get(DIMENSION_STATE_KEY[dim], {}) for dim in ordered_dims}

    target_indicators = [a["indicator_code"] for a in state.get("anomalies", [])]
    tracking_data = calculate_effect_changes(before, after, target_indicators)

    thread_id = state.get("thread_id", "")
    # save_effect_tracking 为 jsonb || 合并：新 dict 若带占位 solution_name 会覆盖库内正确名称
    try:
        existing_row = await get_tracking(thread_id)
        if existing_row:
            ex = existing_row.get("tracking_data") or {}
            if isinstance(ex, str):
                ex = json.loads(ex)
            if isinstance(ex, dict) and ex:
                tracking_data = {**ex, **tracking_data}
    except Exception as e:
        logger.warning("合并已有效果追踪数据失败 thread=%s: %s", thread_id, e)

    snapshots = await list_snapshots(thread_id)

    emit_progress(state, "AI正在生成复盘分析报告...", for_adoption_ui=False)

    adopted_ids = (state.get("adopted_plan_ids") or [])[:1]
    adopted_plans = [p for p in state.get("solution_plans", []) if p.get("plan_id") in adopted_ids]
    primary_plan = adopted_plans[0] if adopted_plans else {}
    primary_plan_id = str(primary_plan.get("plan_id") or "").strip()
    primary_plan_name = str(primary_plan.get("plan_name") or "").strip()
    if primary_plan_id:
        tracking_data["plan_id"] = primary_plan_id
    tracking_data["solution_name"] = resolve_solution_name(
        tracking_data,
        fallback_plan_name=primary_plan_name,
    )

    review_report, _review_llm_usage = await _llm_generate_review(
        tracking_data=tracking_data,
        plans=adopted_plans,
        exec_tasks=state.get("exec_tasks", []),
        snapshots=snapshots if snapshots else None,
        runnable_config=config,
    )
    try:
        await save_effect_tracking(thread_id, tenant_id, store_id, tracking_data)
        await save_review_report(thread_id, tenant_id, store_id, review_report)
    except Exception as e:
        logger.warning("效果追踪/复盘报告落库失败: %s", e)

    try:
        achievement = review_report.get("overall_achievement_rate", 0)
        improved = review_report.get("improved_indicator_count", 0)
        total = review_report.get("total_tracked_indicators", 0)
        solution_name = tracking_data.get("solution_name", "")
        report_time = now
        tracking_period = f"{start[:10]}~{now[:10]}"

        review_summary = {
            "overall_achievement": achievement,
            "improved_count": improved,
            "total_indicators": total,
            "solution_name": solution_name,
            "report_time": report_time,
            "tracking_period": tracking_period,
        }
        await tc.send_review_report_notification(
            tenant_id=tenant_id,
            store_id=store_id,
            admin_account_ids=_get_admin_accounts(state.get("store_profile", {})),
            thread_id=thread_id,
            review_summary=review_summary,
        )

        push_title = f"方案复盘完成 — 达成率 {achievement:.0f}%"
        push_parts = []
        if solution_name:
            push_parts.append(f"方案: {solution_name}")
        push_parts.append(f"追踪区间: {tracking_period}")
        push_parts.append(f"达成率 {achievement:.0f}%（{improved}/{total} 项指标改善）")
        push_parts.append(f"报告时间: {report_time}")
        push_parts.append("报告详情请到【APP → AI智能诊断 → 效果追踪】中查看")
        push_content = " | ".join(push_parts)
        await save_push_log(
            thread_id,
            tenant_id,
            store_id,
            "message",
            "review_reports",
            push_title,
            push_content,
            review_summary,
        )
    except Exception as e:
        logger.warning("推送复盘通知失败: %s", e)

    # 方案沉淀：达成率 >= 50% 的方案写入知识库
    if achievement >= 50 and adopted_plans:
        industry_code = (state.get("store_profile") or {}).get("industry_code")
        indicator_changes = tracking_data.get("changes", [])
        lessons = review_report.get("lessons_learned", [])
        for plan in adopted_plans:
            try:
                await save_effective_plan(
                    tenant_id,
                    store_id,
                    thread_id,
                    plan,
                    achievement,
                    indicator_changes,
                    lessons,
                    industry_code=industry_code,
                )
            except Exception as e:
                logger.warning("方案沉淀失败 [%s]: %s", plan.get("plan_id"), e)
        emit_progress(state, f"已沉淀 {len(adopted_plans)} 个有效方案到知识库", for_adoption_ui=False)

    emit_progress(state, "复盘报告已生成并推送", for_adoption_ui=False)

    tracking_data["status"] = "completed"
    tracking_data["completed_at"] = now
    try:
        await save_effect_tracking(thread_id, tenant_id, store_id, tracking_data)
    except Exception as e:
        logger.warning("效果追踪完成态落库失败: %s", e)

    return {
        "tracking_data": tracking_data,
        "review_report": review_report,
    }
