"""效果追踪节点 — 对比方案执行前后的指标变化，生成复盘报告。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress
from src.agent.prompts.review_analysis import REVIEW_ANALYSIS_SYSTEM, REVIEW_ANALYSIS_USER
from src.core.calculator import calculate_effect_changes, resolve_active_indicators
from src.core.config import get_settings
from src.core.push_log_repo import save_push_log
from src.core.effect_review_repo import save_effect_tracking, save_review_report
from src.core.snapshot_repo import list_snapshots
from src.core.solution_knowledge_repo import save_effective_plan

logger = logging.getLogger(__name__)


def _get_admin_accounts(profile: dict) -> list[str]:
    return profile.get("admin_account_ids", [])


async def _llm_generate_review(
    tracking_data: dict,
    plans: list[dict],
    exec_tasks: list[dict],
    snapshots: list[dict] | None = None,
) -> dict:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.3,
    )

    snapshots_text = ""
    if snapshots:
        snapshots_text = json.dumps(snapshots, ensure_ascii=False, indent=2)

    user_msg = REVIEW_ANALYSIS_USER.format(
        tracking_data=json.dumps(tracking_data, ensure_ascii=False, indent=2),
        plans=json.dumps(plans, ensure_ascii=False, indent=2),
        exec_tasks=json.dumps(exec_tasks, ensure_ascii=False, indent=2),
        snapshots=snapshots_text,
    )

    try:
        resp = await llm.ainvoke([
            {"role": "system", "content": REVIEW_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_msg},
        ])
    except Exception as e:
        logger.warning("LLM 复盘报告调用失败（如 403 请检查 API Key/工作区权限）: %s", e)
        return {
            "overall_achievement_rate": 0,
            "improved_indicator_count": 0,
            "total_tracked_indicators": 0,
            "summary": f"复盘生成暂不可用: {e!s}",
            "lessons_learned": [],
        }

    try:
        text = resp.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        logger.warning("LLM复盘报告输出解析失败")
        return {
            "overall_achievement_rate": 0,
            "improved_indicator_count": 0,
            "total_tracked_indicators": 0,
            "summary": resp.content,
            "lessons_learned": [],
        }


DIMENSION_TOOL_MAP: dict[str, str] = {
    "crm": "get_crm_indicators",
    "marketing": "get_marketing_indicators",
    "retention": "get_retention_indicators",
    "efficiency": "get_efficiency_indicators",
}

DIMENSION_STATE_KEY: dict[str, str] = {
    "crm": "crm_indicators",
    "marketing": "marketing_indicators",
    "retention": "retention_indicators",
    "efficiency": "efficiency_indicators",
}


async def track_effects_node(state: DiagnosisState) -> dict:
    emit_progress(state, "正在采集最新指标数据进行效果对比...")

    active_dims, _active_inds = resolve_active_indicators(
        state.get("selected_dimensions"),
        state.get("selected_indicators"),
    )

    tenant_id = state["tenant_id"]
    store_id = state["store_id"]
    now = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    common_args = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "start_date": start,
        "end_date": now,
    }

    ordered_dims: list[str] = []
    tasks: list = []
    for dim in ("crm", "marketing", "retention", "efficiency"):
        if dim in active_dims:
            tasks.append(mcp_call("metrics-server", DIMENSION_TOOL_MAP[dim], common_args))
            ordered_dims.append(dim)

    results = await asyncio.gather(*tasks)
    dim_results = dict(zip(ordered_dims, results))

    after = {dim: dim_results.get(dim, {}) for dim in ordered_dims}
    before = {dim: state.get(DIMENSION_STATE_KEY[dim], {}) for dim in ordered_dims}

    target_indicators = [a["indicator_code"] for a in state.get("anomalies", [])]
    tracking_data = calculate_effect_changes(before, after, target_indicators)

    thread_id = state.get("thread_id", "")
    snapshots = await list_snapshots(thread_id)

    emit_progress(state, "AI正在生成复盘分析报告...")

    adopted_ids = state.get("adopted_plan_ids", [])
    adopted_plans = [p for p in state.get("solution_plans", []) if p.get("plan_id") in adopted_ids]

    review_report = await _llm_generate_review(
        tracking_data=tracking_data,
        plans=adopted_plans,
        exec_tasks=state.get("exec_tasks", []),
        snapshots=snapshots if snapshots else None,
    )

    try:
        await save_effect_tracking(thread_id, tenant_id, store_id, tracking_data)
        await save_review_report(thread_id, tenant_id, store_id, review_report)
    except Exception as e:
        logger.warning("效果追踪/复盘报告落库失败: %s", e)

    try:
        achievement = review_report.get("overall_achievement_rate", 0)
        improved = review_report.get("improved_indicator_count", 0)
        review_summary = {"overall_achievement": achievement, "improved_count": improved}
        await mcp_call("notify-server", "send_review_report_notification", {
            "tenant_id": tenant_id,
            "store_id": store_id,
            "admin_account_ids": _get_admin_accounts(state.get("store_profile", {})),
            "thread_id": thread_id,
            "review_summary": review_summary,
        })
        await save_push_log(
            thread_id, tenant_id, store_id,
            "message", "ai_review_report",
            f"AI复盘报告已生成 — 达成率 {achievement:.0f}%",
            f"共 {improved} 项指标得到改善。",
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
                    tenant_id, store_id, thread_id,
                    plan, achievement, indicator_changes, lessons,
                    industry_code=industry_code,
                )
            except Exception as e:
                logger.warning("方案沉淀失败 [%s]: %s", plan.get("plan_id"), e)
        emit_progress(state, f"已沉淀 {len(adopted_plans)} 个有效方案到知识库")

    emit_progress(state, "复盘报告已生成并推送")

    return {
        "tracking_data": tracking_data,
        "review_report": review_report,
    }
