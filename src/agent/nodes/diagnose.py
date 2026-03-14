"""诊断分析节点 — 规则计算 + LLM根因分析 + 生成报告。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress
from src.agent.prompts.root_cause_analysis import (
    ROOT_CAUSE_ANALYSIS_SYSTEM,
    ROOT_CAUSE_ANALYSIS_USER,
)
from src.core.calculator import (
    calculate_dimension_score,
    build_diagnosis_report,
    resolve_active_indicators,
    rebalance_weights,
)
from src.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_admin_accounts(profile: dict) -> list[str]:
    return profile.get("admin_account_ids", [])


async def _llm_root_cause_analysis(
    store_profile: dict,
    anomalies: list[dict],
    all_indicators: dict,
) -> list[dict]:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.3,
    )

    user_msg = ROOT_CAUSE_ANALYSIS_USER.format(
        store_profile=json.dumps(store_profile, ensure_ascii=False, indent=2),
        anomalies=json.dumps(anomalies, ensure_ascii=False, indent=2),
        all_indicators=json.dumps(all_indicators, ensure_ascii=False, indent=2),
    )

    resp = await llm.ainvoke([
        {"role": "system", "content": ROOT_CAUSE_ANALYSIS_SYSTEM},
        {"role": "user", "content": user_msg},
    ])

    try:
        text = resp.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        logger.warning("LLM根因分析输出解析失败，返回原始文本")
        return [{"anomaly_indicator": "unknown", "cause": text, "evidence": "", "confidence": 0.5}]


async def diagnose_node(state: DiagnosisState) -> dict:
    emit_progress(state, "正在计算运营健康度...")

    active_dims, active_inds = resolve_active_indicators(
        state.get("selected_dimensions"),
        state.get("selected_indicators"),
    )
    weights = rebalance_weights(active_dims)

    benchmarks = state.get("benchmarks", {})
    benchmark_data = benchmarks.get("benchmarks", benchmarks)

    dim_state_map = {
        "crm": "crm_indicators",
        "marketing": "marketing_indicators",
        "retention": "retention_indicators",
        "efficiency": "efficiency_indicators",
    }

    dimension_scores: dict = {}
    anomalies: list[dict] = []

    for dim_name, state_key in dim_state_map.items():
        if dim_name not in active_dims:
            continue
        indicators = state.get(state_key, {})
        weight = weights.get(dim_name, 0)

        if not indicators:
            dimension_scores[dim_name] = {"score": 60.0, "weight": weight}
            continue

        score, dim_anomalies = calculate_dimension_score(
            indicators=indicators,
            benchmarks=benchmark_data,
            dimension=dim_name,
            active_indicators=active_inds,
        )
        dimension_scores[dim_name] = {"score": score, "weight": weight}
        anomalies.extend(dim_anomalies)

    health_score = sum(d["score"] * d["weight"] for d in dimension_scores.values())

    emit_progress(state, f"健康度评分: {health_score:.1f}分, 发现 {len(anomalies)} 项异常指标")

    all_indicators = {
        dim: state.get(key, {})
        for dim, key in dim_state_map.items()
        if dim in active_dims
    }

    root_causes: list[dict] = []
    if anomalies:
        emit_progress(state, "AI正在分析异常根因...")
        root_causes = await _llm_root_cause_analysis(
            store_profile=state.get("store_profile", {}),
            anomalies=anomalies,
            all_indicators=all_indicators,
        )

    drill_details: dict[str, dict] = {}
    if anomalies:
        emit_progress(state, f"正在钻取 {len(anomalies)} 项异常指标的明细数据...")
        settings = get_settings()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=settings.diagnosis_lookback_days)).strftime("%Y-%m-%d")
        drill_tasks = {
            a["indicator_code"]: mcp_call("metrics-server", "drill_down_indicator", {
                "tenant_id": state["tenant_id"],
                "store_id": state["store_id"],
                "indicator_code": a["indicator_code"],
                "start_date": start_date,
                "end_date": end_date,
                "page": 1,
                "page_size": 5,
            })
            for a in anomalies
        }
        results = await asyncio.gather(*drill_tasks.values())
        drill_details = dict(zip(drill_tasks.keys(), results))

    for a in anomalies:
        a["drill_down"] = drill_details.get(a["indicator_code"])

    diagnosis_report = build_diagnosis_report(
        store_profile=state.get("store_profile", {}),
        health_score=health_score,
        dimension_scores=dimension_scores,
        anomalies=anomalies,
        root_causes=root_causes,
    )

    emit_progress(state, "诊断完成，正在推送报告...")

    try:
        await mcp_call("notify-server", "send_diagnosis_report_notification", {
            "tenant_id": state["tenant_id"],
            "store_id": state["store_id"],
            "admin_account_ids": _get_admin_accounts(state.get("store_profile", {})),
            "report_summary": {
                "health_score": health_score,
                "anomaly_count": len(anomalies),
                "top_anomaly": anomalies[0]["description"] if anomalies else None,
            },
        })
    except Exception as e:
        logger.warning("推送诊断报告通知失败: %s", e)

    return {
        "health_score": health_score,
        "dimension_scores": dimension_scores,
        "anomalies": anomalies,
        "root_causes": root_causes,
        "diagnosis_report": diagnosis_report,
    }
