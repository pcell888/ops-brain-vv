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

logger = logging.getLogger(__name__)


def _get_admin_accounts(profile: dict) -> list[str]:
    return profile.get("admin_account_ids", [])


async def _llm_generate_solutions(
    store_profile: dict,
    anomalies: list[dict],
    root_causes: list[dict],
    benchmarks: dict,
    indicators: dict,
) -> list[dict]:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.5,
    )

    user_msg = SOLUTION_GENERATION_USER.format(
        store_profile=json.dumps(store_profile, ensure_ascii=False, indent=2),
        anomalies=json.dumps(anomalies, ensure_ascii=False, indent=2),
        root_causes=json.dumps(root_causes, ensure_ascii=False, indent=2),
        benchmarks=json.dumps(benchmarks, ensure_ascii=False, indent=2),
        all_indicators=json.dumps(indicators, ensure_ascii=False, indent=2),
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
    )

    for plan in plans:
        roi = plan.get("expected_roi", 0)
        diff = plan.get("difficulty_score", 5)
        urgency = plan.get("urgency_score", 5)
        plan["priority_score"] = roi * 0.6 + (10 - diff) * 0.2 + urgency * 0.2

    plans.sort(key=lambda p: p.get("priority_score", 0), reverse=True)

    emit_progress(state, f"已生成 {len(plans)} 个优化方案，等待采纳")

    try:
        await mcp_call("notify-server", "send_plan_adoption_request", {
            "tenant_id": state["tenant_id"],
            "store_id": state["store_id"],
            "admin_account_ids": _get_admin_accounts(store_profile),
            "plans_summary": [
                {"name": p.get("plan_name", ""), "priority": p.get("priority_level", "medium")}
                for p in plans
            ],
        })
    except Exception as e:
        logger.warning("推送方案采纳通知失败: %s", e)

    return {"solution_plans": plans}
