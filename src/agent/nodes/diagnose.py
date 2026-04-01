"""诊断分析节点 — 规则计算 + LLM根因分析 + 生成报告。"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from langchain_openai import ChatOpenAI

from src.agent.state import DiagnosisState
from src.agent.tools import mcp_call, emit_progress
from src.agent.prompts.root_cause_analysis import (
    ROOT_CAUSE_ANALYSIS_SYSTEM,
    ROOT_CAUSE_ANALYSIS_USER,
)
from src.core.calculator import (
    INDICATOR_META,
    DEFAULT_BENCHMARKS,
    calculate_dimension_score,
    build_diagnosis_report,
    normalize_llm_root_causes,
    resolve_active_indicators,
    rebalance_weights,
)
from src.core.config import get_settings
from src.core.diagnosis_report_repo import save_report as save_report_to_db
from src.core.push_log_repo import save_push_log
from src.core.tenant_config import get_tenant_config

logger = logging.getLogger(__name__)


def _get_admin_accounts(profile: dict) -> list[str]:
    return profile.get("admin_account_ids", [])


def _message_text(resp) -> str:
    c = getattr(resp, "content", "")
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        parts: list[str] = []
        for block in c:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return str(c).strip()


def _coerce_root_cause_list(parsed: object) -> list[dict]:
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        for key in ("root_causes", "results", "data", "items", "analyses", "anomaly_analyses"):
            v = parsed.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        if any(k in parsed for k in ("anomaly_indicator", "cause", "indicator_code")):
            return [parsed]
    return []


def _root_causes_by_code(root_causes: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rc in root_causes:
        k = rc.get("anomaly_indicator")
        if isinstance(k, str) and k.strip():
            out[k.strip()] = rc
    return out


def _slim_anomalies(anomalies: list[dict]) -> list[dict]:
    return [
        {
            "indicator_code": a.get("indicator_code"),
            "indicator_name": a.get("indicator_name"),
            "dimension": a.get("dimension"),
            "current_value": a.get("current_value"),
            "benchmark_avg": a.get("benchmark_avg"),
            "deviation_pct": a.get("deviation_pct"),
            "severity": a.get("severity"),
        }
        for a in anomalies
    ]


def _slim_indicators(all_indicators: dict, anomalies: list[dict]) -> dict:
    anomaly_codes = {a["indicator_code"] for a in anomalies if a.get("indicator_code")}
    anomaly_dims = {a.get("dimension") for a in anomalies if a.get("dimension")}
    slim = {}
    for dim, data in all_indicators.items():
        if dim not in anomaly_dims:
            continue
        indicators = data.get("indicators", {})
        if not isinstance(indicators, dict):
            continue
        slim_indicators = {}
        for code, ind_data in indicators.items():
            if code in anomaly_codes:
                slim_indicators[code] = {
                    "value": ind_data.get("value"),
                    "unit": ind_data.get("unit"),
                }
        if slim_indicators:
            slim[dim] = {"indicators": slim_indicators}
    return slim


def _slim_store_profile(profile: dict) -> dict:
    return {
        "store_name": profile.get("store_name"),
        "industry_code": profile.get("industry_code"),
        "customer_count": profile.get("customer_count"),
        "monthly_gmv": profile.get("monthly_gmv"),
        "employee_count": profile.get("employee_count"),
    }


async def _llm_root_cause_analysis(
    store_profile: dict,
    anomalies: list[dict],
    all_indicators: dict,
) -> list[dict]:
    settings = get_settings()
    if not settings.llm_enabled:
        logger.info("LLM_ENABLED=false，跳过根因LLM分析")
        return []
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.3,
        max_tokens=8192,
        timeout=settings.llm_httpx_timeout(),
    )

    required_codes = json.dumps(
        [a["indicator_code"] for a in anomalies],
        ensure_ascii=False,
    )
    user_msg = ROOT_CAUSE_ANALYSIS_USER.format(
        store_profile=json.dumps(store_profile, ensure_ascii=False, indent=2),
        required_codes=required_codes,
        anomalies=json.dumps(anomalies, ensure_ascii=False, indent=2),
        all_indicators=json.dumps(all_indicators, ensure_ascii=False, indent=2),
    )
    logger.info("LLM根因分析输入: %d chars (异常数: %d)", len(user_msg), len(anomalies))

    try:
        resp = await llm.ainvoke(
            [
                {"role": "system", "content": ROOT_CAUSE_ANALYSIS_SYSTEM},
                {"role": "user", "content": user_msg},
            ]
        )
    except Exception as e:
        logger.warning("LLM根因分析调用失败: %s", e)
        return []

    text = ""
    try:
        text = _message_text(resp)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
        out = _coerce_root_cause_list(parsed)
        if out:
            return out
        logger.warning("LLM根因分析输出无法解析为根因列表: %s", type(parsed).__name__)
        return []
    except (json.JSONDecodeError, IndexError) as e:
        logger.warning("LLM根因分析 JSON 解析失败: %s，前 400 字: %s", e, text[:400] if text else "")
        return []


class DiagnosisDataMissingError(RuntimeError):
    """诊断所需的基础数据缺失（上游数据采集未成功完成）。"""


async def diagnose_node(state: DiagnosisState) -> dict:
    emit_progress(state, "正在计算运营健康度...", percent=45)

    # ── 前置校验：确保 collect_data_node 已成功产出数据 ──
    profile = state.get("store_profile")
    if not isinstance(profile, dict) or not profile:
        raise DiagnosisDataMissingError("企业画像数据缺失，上游数据采集可能已失败，请检查业务API连通性")

    dim_state_map = {
        "crm": "crm_indicators",
        "marketing": "marketing_indicators",
        "retention": "retention_indicators",
        "efficiency": "efficiency_indicators",
    }

    active_dims, active_inds = resolve_active_indicators(
        state.get("selected_dimensions"),
        state.get("selected_indicators"),
    )

    collected_dims = [
        dim
        for dim in active_dims
        if isinstance(state.get(dim_state_map.get(dim, ""), dict), dict) and state[dim_state_map[dim]].get("indicators")
    ]
    if not collected_dims:
        raise DiagnosisDataMissingError(
            f"所有维度指标数据均缺失（期望: {', '.join(active_dims)}），上游数据采集可能已失败，请检查业务API连通性"
        )

    weights = rebalance_weights(active_dims)

    benchmarks = state.get("benchmarks", {})
    if not isinstance(benchmarks, dict):
        logger.warning("benchmarks 类型异常，已降级为空对象: %s", type(benchmarks).__name__)
        benchmarks = {}
    benchmark_data = benchmarks.get("benchmarks", benchmarks)
    if not isinstance(benchmark_data, dict):
        logger.warning("benchmark_data 类型异常，已降级为空对象: %s", type(benchmark_data).__name__)
        benchmark_data = {}

    dimension_scores: dict = {}
    dimension_indicator_scores: dict[str, list[dict]] = {}
    anomalies: list[dict] = []

    for dim_name, state_key in dim_state_map.items():
        if dim_name not in active_dims:
            continue
        indicators = state.get(state_key, {})
        if not isinstance(indicators, dict):
            logger.warning("%s 类型异常，已降级为空对象: %s", state_key, type(indicators).__name__)
            indicators = {}
        weight = weights.get(dim_name, 0)

        if not indicators:
            dimension_scores[dim_name] = {"score": 60.0, "weight": weight}
            dimension_indicator_scores[dim_name] = []
            continue

        score, dim_anomalies, ind_scores = calculate_dimension_score(
            indicators=indicators,
            benchmarks=benchmark_data,
            dimension=dim_name,
            active_indicators=active_inds,
        )
        dimension_scores[dim_name] = {"score": score, "weight": weight}
        dimension_indicator_scores[dim_name] = ind_scores
        anomalies.extend(dim_anomalies)

    health_score = sum(d["score"] * d["weight"] for d in dimension_scores.values())

    dimension_benchmarks: dict[str, list[dict]] = {}
    for dim_name in dimension_scores:
        dim_indicators = [
            (code, meta)
            for code, meta in INDICATOR_META.items()
            if meta["dimension"] == dim_name and (active_inds is None or code in active_inds)
        ]
        dimension_benchmarks[dim_name] = []
        for code, meta in dim_indicators:
            bench = benchmark_data.get(code)
            if (isinstance(bench, dict) and bench.get("avg_value") in (None, 0)) or bench in (None, 0):
                bench = DEFAULT_BENCHMARKS.get(code, bench)
            if isinstance(bench, dict):
                dimension_benchmarks[dim_name].append(
                    {
                        "indicator_code": code,
                        "indicator_name": meta["name"],
                        "unit": meta["unit"],
                        "avg_value": round(bench.get("avg_value", 0), 2),
                        "median_value": round(bench["median_value"], 2)
                        if bench.get("median_value") is not None
                        else None,
                        "excellent_value": round(bench["excellent_value"], 2)
                        if bench.get("excellent_value") is not None
                        else None,
                    }
                )
            elif bench is not None:
                dimension_benchmarks[dim_name].append(
                    {
                        "indicator_code": code,
                        "indicator_name": meta["name"],
                        "unit": meta["unit"],
                        "avg_value": round(float(bench), 2),
                        "median_value": None,
                        "excellent_value": None,
                    }
                )
            else:
                dimension_benchmarks[dim_name].append(
                    {
                        "indicator_code": code,
                        "indicator_name": meta["name"],
                        "unit": meta["unit"],
                        "avg_value": None,
                        "median_value": None,
                        "excellent_value": None,
                    }
                )

    emit_progress(state, f"健康度评分: {health_score:.1f}分, 发现 {len(anomalies)} 项异常指标", percent=50)

    all_indicators = {dim: state.get(key, {}) for dim, key in dim_state_map.items() if dim in active_dims}
    slim_indicators = _slim_indicators(all_indicators, anomalies)
    slim_profile = _slim_store_profile(state.get("store_profile", {}))
    slim_anomalies = _slim_anomalies(anomalies)

    root_causes: list[dict] = []
    if anomalies:
        emit_progress(state, "AI正在分析异常根因...", percent=55)
        merged: dict[str, dict] = {}
        batch = await _llm_root_cause_analysis(
            store_profile=slim_profile,
            anomalies=slim_anomalies,
            all_indicators=slim_indicators,
        )
        batch = normalize_llm_root_causes(batch, anomalies)
        merged.update(_root_causes_by_code(batch))
        for _round in range(2):
            missing = [a for a in anomalies if a["indicator_code"] not in merged]
            if not missing:
                break
            emit_progress(
                state,
                f"补全遗漏根因 ({len(missing)}/{len(anomalies)})...",
                percent=56 + _round,
            )
            extra = await _llm_root_cause_analysis(
                store_profile=slim_profile,
                anomalies=_slim_anomalies(missing),
                all_indicators=slim_indicators,
            )
            extra = normalize_llm_root_causes(extra, missing)
            merged.update(_root_causes_by_code(extra))
        root_causes = list(merged.values())
        if len(merged) < len(anomalies):
            still = [a["indicator_code"] for a in anomalies if a["indicator_code"] not in merged]
            logger.warning(
                "根因仍未覆盖全部异常: %s/%s，缺: %s",
                len(merged),
                len(anomalies),
                still,
            )

    diagnosis_report = build_diagnosis_report(
        store_profile=state.get("store_profile", {}),
        health_score=health_score,
        dimension_scores=dimension_scores,
        dimension_indicator_scores=dimension_indicator_scores,
        dimension_benchmarks=dimension_benchmarks,
        anomalies=anomalies,
        root_causes=root_causes,
    )

    is_scheduled = state.get("trigger_type") == "scheduled"
    scope_label = "全企业" if not state.get("store_id") else f"店铺 {state['store_id']}"
    emit_progress(state, f"{scope_label}诊断完成，正在推送报告...", percent=68)

    try:
        tenant_config = await get_tenant_config(state["tenant_id"])
        analysis_period_days = tenant_config.get("analysis_period_days", 30)

        report_summary = {
            "health_score": health_score,
            "anomaly_count": len(anomalies),
            "top_anomaly": anomalies[0]["description"] if anomalies else None,
            "report_url": state.get("thread_id", ""),
            "analysis_period_days": analysis_period_days,
            "diagnosis_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        if is_scheduled:
            report_summary["notification_type"] = "ai_weekly_digest"
        await mcp_call(
            "notify-server",
            "send_diagnosis_report_notification",
            {
                "tenant_id": state["tenant_id"],
                "store_id": state["store_id"],
                "admin_account_ids": _get_admin_accounts(state.get("store_profile", {})),
                "report_summary": report_summary,
            },
        )
        notify_type = report_summary.get("notification_type", "ai_diagnosis_report")
        scope_tag = f"【{scope_label}】"
        title = f"{'【周度】' if notify_type == 'ai_weekly_digest' else ''}{scope_tag}AI诊断报告已生成 — 健康度 {health_score:.1f}分"
        analysis_period = report_summary.get("analysis_period_days", 30)
        diagnosis_time = report_summary.get("diagnosis_time", "")
        content = f"诊断时间: {diagnosis_time} | 近{analysis_period}天 | 共发现 {len(anomalies)} 项异常指标。"
        if report_summary.get("top_anomaly"):
            content += f"最突出问题：{report_summary.get('top_anomaly')}。"
        content += "详情请到APP/后台查看"
        await save_push_log(
            state.get("thread_id", ""),
            state["tenant_id"],
            state["store_id"],
            "message",
            notify_type,
            title,
            content,
            report_summary,
        )
    except Exception as e:
        logger.warning("推送诊断报告通知失败: %s", e)

    thread_id = state.get("thread_id")
    if thread_id:
        try:
            await save_report_to_db(
                thread_id=thread_id,
                tenant_id=state["tenant_id"],
                store_id=state["store_id"],
                trigger_type=state.get("trigger_type", "manual"),
                report=diagnosis_report,
            )
        except Exception as e:
            logger.exception("诊断报告落库失败")
            emit_progress(state, f"诊断报告落库失败，历史记录可能无法查看: {e}")

    return {
        "health_score": health_score,
        "dimension_scores": dimension_scores,
        "anomalies": anomalies,
        "root_causes": root_causes,
        "diagnosis_report": diagnosis_report,
    }
