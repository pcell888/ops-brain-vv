"""方案生成节点 — 基于异常指标 + LLM 生成优化方案。"""

from __future__ import annotations

import json
import logging
import uuid

from langchain_openai import ChatOpenAI

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress
from src.agent.prompts.solution_generation import (
    SOLUTION_GENERATION_SYSTEM,
    SOLUTION_GENERATION_USER,
)
from src.core.config import get_settings
from src.core.push_log_repo import save_push_log
from src.core.solution_knowledge_repo import search_similar_plans

logger = logging.getLogger(__name__)


def _get_admin_accounts(profile: dict) -> list[str]:
    return profile.get("admin_account_ids", [])


async def _llm_generate_solutions(
    store_profile: dict,
    anomalies: list[dict],
    root_causes: list[dict],
    benchmarks: dict,
    indicators: dict,
    historical_cases: list[dict] | None = None,
) -> list[dict]:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.5,
    )

    cases_text = ""
    if historical_cases:
        cases_text = json.dumps(historical_cases, ensure_ascii=False, indent=2)

    user_msg = SOLUTION_GENERATION_USER.format(
        store_profile=json.dumps(store_profile, ensure_ascii=False, indent=2),
        anomalies=json.dumps(anomalies, ensure_ascii=False, indent=2),
        root_causes=json.dumps(root_causes, ensure_ascii=False, indent=2),
        benchmarks=json.dumps(benchmarks, ensure_ascii=False, indent=2),
        all_indicators=json.dumps(indicators, ensure_ascii=False, indent=2),
        historical_cases=cases_text,
    )

    resp = await llm.ainvoke([
        {"role": "system", "content": SOLUTION_GENERATION_SYSTEM},
        {"role": "user", "content": user_msg},
    ])

    try:
        text = resp.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        plans = json.loads(text)
        for plan in plans:
            if not plan.get("plan_id"):
                plan["plan_id"] = f"plan_{uuid.uuid4().hex[:8]}"
        return plans
    except (json.JSONDecodeError, IndexError):
        logger.warning("LLM方案生成输出解析失败")
        return [{
            "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
            "plan_name": "默认优化方案",
            "description": resp.content,
            "target_indicators": [a["indicator_code"] for a in anomalies[:3]],
            "expected_improvement": {},
            "expected_roi": 1.0,
            "difficulty_score": 5,
            "urgency_score": 5,
            "priority_level": "medium",
            "steps": [],
            "auto_actions": [],
        }]


async def generate_solutions_node(state: DiagnosisState) -> dict:
    anomalies = state.get("anomalies", [])
    if not anomalies:
        return {"solution_plans": []}

    emit_progress(state, "正在匹配优化方案模板...")

    store_profile = state.get("store_profile", {})
    benchmarks = state.get("benchmarks", {})

    target_codes = [a.get("indicator_code") for a in anomalies if a.get("indicator_code")]
    industry_code = store_profile.get("industry_code")
    historical_cases: list[dict] = []
    try:
        historical_cases = await search_similar_plans(target_codes, industry_code=industry_code)
    except Exception as e:
        logger.warning("检索方案知识库失败: %s", e)

    if historical_cases:
        emit_progress(state, f"已匹配 {len(historical_cases)} 个历史成功案例作为参考")

    emit_progress(state, "AI正在生成个性化优化方案...")

    plans = await _llm_generate_solutions(
        store_profile=store_profile,
        anomalies=anomalies,
        root_causes=state.get("root_causes", []),
        benchmarks=benchmarks,
        indicators={
            "crm": state.get("crm_indicators", {}),
            "marketing": state.get("marketing_indicators", {}),
            "retention": state.get("retention_indicators", {}),
            "efficiency": state.get("efficiency_indicators", {}),
        },
        historical_cases=historical_cases if historical_cases else None,
    )

    for plan in plans:
        roi = plan.get("expected_roi", 0)
        diff = plan.get("difficulty_score", 5)
        urgency = plan.get("urgency_score", 5)
        plan["priority_score"] = roi * 0.6 + (10 - diff) * 0.2 + urgency * 0.2

    plans.sort(key=lambda p: p.get("priority_score", 0), reverse=True)

    emit_progress(state, f"已生成 {len(plans)} 个优化方案，等待采纳")

    try:
        plans_summary = [{"name": p.get("plan_name", ""), "priority": p.get("priority_level", "medium")} for p in plans]
        await mcp_call("notify-server", "send_plan_adoption_request", {
            "tenant_id": state["tenant_id"],
            "store_id": state["store_id"],
            "admin_account_ids": _get_admin_accounts(store_profile),
            "thread_id": state.get("thread_id", ""),
            "plans_summary": plans_summary,
        })
        plan_names = "、".join(p.get("name", "") for p in plans_summary[:3])
        await save_push_log(
            state.get("thread_id", ""), state["tenant_id"], state["store_id"],
            "message", "ai_plan_adoption",
            "AI优化方案待采纳",
            f"已生成 {len(plans)} 个优化方案（{plan_names}），请查看并选择采纳。",
            {"plans_summary": plans_summary},
        )
    except Exception as e:
        logger.warning("推送方案采纳通知失败: %s", e)

    return {"solution_plans": plans}
