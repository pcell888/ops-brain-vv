"""方案生成节点 — 基于异常指标 + LLM 生成优化方案。"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid

from typing import Any

from src.agent.state import DiagnosisState
from src.agent.progress import emit_progress
from src.biz.client import tenant_client
from src.agent.prompts.solution_generation import (
    SOLUTION_GENERATION_SYSTEM,
    SOLUTION_GENERATION_USER,
)
from src.agent.utils import get_admin_accounts as _get_admin_accounts, slim_anomalies as _slim_anomalies, slim_indicators as _slim_indicators, slim_benchmarks as _slim_benchmarks, slim_root_causes as _slim_root_causes
from src.core.config import get_settings
from src.core.dept_resolver import dept_keyword_match as _dept_keyword_match
from src.core.llm_caller import llm_call_json
from src.repositories.diagnosis_report import update_plan_ids
from src.repositories.push_log import save_push_log
from src.repositories.solution_knowledge import search_similar_plans
from src.core.indicator_push_rules import (
    INDICATOR_PUSH_RULES,
    collect_mandatory_task_specs,
    format_indicator_rules_for_prompt,
)

logger = logging.getLogger(__name__)


async def _solution_generation_heartbeat(state: DiagnosisState, *, start_percent: int = 88) -> None:
    """方案生成期间定时写入心跳，避免前端/CLI长期停在同一条进度。"""
    waited_seconds = 0
    while True:
        await asyncio.sleep(20)
        waited_seconds += 20
        emit_progress(
            state,
            f"正在生成优化方案...（已等待 {waited_seconds}s）",
            percent=start_percent,
        )

def _anomaly_data_context_line(anomalies: list[dict], indicator_code: str) -> str:
    for a in anomalies:
        if a.get("indicator_code") != indicator_code:
            continue
        name = a.get("indicator_name") or indicator_code
        cur = a.get("current_value")
        avg = a.get("benchmark_avg")
        dev = a.get("deviation_pct")
        u = a.get("unit") or ""
        if cur is not None and avg is not None and dev is not None:
            abs_gap = round(abs(cur - avg), 1)
            direction = "偏低" if dev < 0 else "偏高"
            if u == "%":
                return f"{name} {cur}%（均值 {avg}%，{direction} {abs_gap}个百分点）"
            return f"{name} {cur}{u}（均值 {avg}{u}，{direction} {abs_gap}{u}）"
        if cur is not None:
            return f"{name} {cur}{u}"
        return f"指标 {indicator_code}"
    return f"指标 {indicator_code}"


def _generate_acceptance_criteria(anomalies: list[dict], indicator_codes: list[str]) -> list[str]:
    criteria: list[str] = []
    for code in indicator_codes:
        for a in anomalies:
            if a.get("indicator_code") != code:
                continue
            name = a.get("indicator_name") or code
            cur = a.get("current_value")
            avg = a.get("benchmark_avg")
            u = a.get("unit") or "%"
            if cur is not None and avg is not None and cur < avg:
                target = round(cur + (avg - cur) * 0.5, 1)
                criteria.append(f"{name} ≥ {target}{u}")
                break
            break
    return criteria[:5]


def _mandatory_task_is_covered(plans: list[dict], task_name: str, owner_dept: str) -> bool:
    tn = (task_name or "").strip()
    if not tn:
        return False
    for plan in plans:
        for step in plan.get("steps") or []:
            if not _dept_keyword_match(owner_dept, str(step.get("owner_dept", ""))):
                continue
            action = str(step.get("action") or "")
            impl = step.get("implementation_steps") or []
            impl_text = " ".join(str(x) for x in impl) if isinstance(impl, list) else ""
            if tn in action or tn in impl_text:
                return True
            if len(tn) >= 4 and tn[:4] in action:
                return True
    return False


def _step_from_mandatory_spec(spec: dict, step_no: int, anomalies: list[dict]) -> dict:
    ind = spec.get("indicator_code", "")
    impl = spec.get("implementation_steps")
    if not isinstance(impl, list) or len(impl) < 1:
        impl = [f"完成「{spec.get('task_name', '')}」并留痕复盘"]
    impl_list = [str(x).strip() for x in impl if str(x).strip()][:30]
    od = spec.get("owner_dept") or "运营"
    action = f"{od}：{spec.get('task_name', '优化任务')}（{spec.get('timeline', '按规范期限')}）"
    return {
        "step": step_no,
        "action": action[:200],
        "owner_dept": od,
        "timeline": spec.get("timeline") or "3天内",
        "data_context": _anomaly_data_context_line(anomalies, ind),
        "implementation_steps": impl_list,
    }


def _coupon_already_present(plan: dict, target_customers: str | None) -> bool:
    if not target_customers:
        return False
    for act in plan.get("auto_actions") or []:
        if act.get("type") != "coupon_campaign":
            continue
        cfg = act.get("config") or {}
        if cfg.get("target_customers") == target_customers:
            return True
    return False


def _ensure_mandatory_coupon_auto_actions(plans: list[dict], anomalies: list[dict]) -> None:
    if not plans:
        return
    for a in anomalies:
        ind = a.get("indicator_code")
        if not ind:
            continue
        rule = INDICATOR_PUSH_RULES.get(ind)
        if not rule:
            continue
        cc = rule.get("coupon_campaign")
        if not cc:
            continue
        plan = next(
            (p for p in plans if ind in (p.get("target_indicators") or [])),
            plans[0],
        )
        tgt = cc.get("target_customers")
        if _coupon_already_present(plan, tgt):
            continue
        actions = list(plan.get("auto_actions") or [])
        actions.append({"type": "coupon_campaign", "config": dict(cc)})
        plan["auto_actions"] = actions
        ti = list(plan.get("target_indicators") or [])
        if ind not in ti:
            ti.append(ind)
            plan["target_indicators"] = ti


def _ensure_mandatory_task_steps(plans: list[dict], mandatory: list[dict], anomalies: list[dict]) -> list[dict]:
    """规则保底：补全 LLM 遗漏的 tasks[] 对应 step（写入优先级最高的方案）。"""
    if not mandatory:
        return plans
    if not plans:
        pid = f"plan_{uuid.uuid4().hex[:8]}"
        codes = list({m["indicator_code"] for m in mandatory if m.get("indicator_code")})
        plans = [
            {
                "plan_id": pid,
                "plan_name": "5.2.3 规则保底方案",
                "description": "由系统根据 5.2.3 规则保底任务生成，请结合业务采纳或合并到其他方案。",
                "target_indicators": codes,
                "expected_improvement": {},
                "expected_roi": 1.0,
                "difficulty_score": 5,
                "urgency_score": 7,
                "priority_level": "high",
                "steps": [],
                "auto_actions": [],
            }
        ]
    target = plans[0]
    steps = list(target.get("steps") or [])
    next_no = 0
    for s in steps:
        sn = s.get("step")
        if isinstance(sn, int) and sn > next_no:
            next_no = sn
    if next_no == 0:
        next_no = len(steps)
    for spec in mandatory:
        if _mandatory_task_is_covered(plans, spec.get("task_name", ""), spec.get("owner_dept", "")):
            continue
        next_no += 1
        steps.append(_step_from_mandatory_spec(spec, next_no, anomalies))
        logger.info(
            "方案生成保底：补全规则任务 %s / %s",
            spec.get("indicator_code"),
            spec.get("task_name"),
        )
    target["steps"] = steps
    return plans


def _build_plans_when_llm_disabled(anomalies: list[dict], mandatory: list[dict]) -> list[dict]:
    """LLM 关闭时：仅规则保底步骤 + 规则券。"""
    pid = f"plan_{uuid.uuid4().hex[:8]}"
    codes = [a.get("indicator_code") for a in anomalies if a.get("indicator_code")]
    steps = [_step_from_mandatory_spec(s, i + 1, anomalies) for i, s in enumerate(mandatory)]
    auto: list[dict] = []
    seen_tgt: set[str] = set()
    for a in anomalies:
        ind = a.get("indicator_code")
        rule = INDICATOR_PUSH_RULES.get(ind) if ind else None
        if not rule:
            continue
        cc = rule.get("coupon_campaign")
        if not cc:
            continue
        tgt = str(cc.get("target_customers") or "")
        if tgt in seen_tgt:
            continue
        seen_tgt.add(tgt)
        auto.append({"type": "coupon_campaign", "config": dict(cc)})
    return [
        {
            "plan_id": pid,
            "plan_name": "规则保底优化方案（LLM 已关闭）",
            "description": "LLM 未启用，步骤与券活动均来自 5.2.3 规则表。",
            "target_indicators": codes[:10],
            "expected_improvement": {},
            "expected_roi": 1.0,
            "difficulty_score": 5,
            "urgency_score": 6,
            "priority_level": "medium",
            "steps": steps,
            "auto_actions": auto,
        }
    ]


async def _llm_generate_solutions(
    store_profile: dict,
    anomalies: list[dict],
    root_causes: list[dict],
    benchmarks: dict,
    indicators: dict,
    historical_cases: list[dict] | None = None,
    indicator_push_rules: str = "",
    mandatory_rule_tasks: str = "",
    *,
    runnable_config: Any | None = None,
) -> tuple[list[dict], dict | None]:
    settings = get_settings()
    mandatory_specs = collect_mandatory_task_specs(anomalies)
    if not settings.llm_enabled:
        logger.info("LLM_ENABLED=false，使用规则保底方案")
        return _build_plans_when_llm_disabled(anomalies, mandatory_specs), None

    cases_text = ""
    if historical_cases:
        cases_text = json.dumps(historical_cases[:3], ensure_ascii=False)

    mr_block = mandatory_rule_tasks or json.dumps(
        collect_mandatory_task_specs(anomalies),
        ensure_ascii=False,
    )
    if mr_block.strip() in ("[]", ""):
        mr_block = "（本次涉及指标在规则表中无 tasks 条目；若有券/消息类要求见上文 5.2.3 规范 JSON。）"

    slim_profile = {
        "store_name": store_profile.get("store_name"),
        "industry_code": store_profile.get("industry_code"),
        "customer_count": store_profile.get("customer_count"),
        "monthly_gmv": store_profile.get("monthly_gmv"),
    }
    user_msg = SOLUTION_GENERATION_USER.format(
        store_profile=json.dumps(slim_profile, ensure_ascii=False),
        anomalies=json.dumps(anomalies, ensure_ascii=False),
        root_causes=json.dumps(root_causes, ensure_ascii=False),
        benchmarks=json.dumps(benchmarks, ensure_ascii=False),
        all_indicators=json.dumps(indicators, ensure_ascii=False),
        indicator_push_rules=indicator_push_rules or format_indicator_rules_for_prompt(anomalies),
        mandatory_rule_tasks=mr_block,
        historical_cases=cases_text,
    )
    logger.info(
        "LLM方案生成输入: %d chars (异常数: %d, 案例数: %d)",
        len(user_msg),
        len(anomalies),
        len(historical_cases) if historical_cases else 0,
    )

    try:
        parsed, raw_text, usage = await llm_call_json(
            system_prompt=SOLUTION_GENERATION_SYSTEM,
            user_prompt=user_msg,
            label="LLM方案生成",
            temperature=0.5,
            max_tokens=4096,
            runnable_config=runnable_config,
            model=get_settings().llm_model_solution,
        )
    except Exception as e:
        logger.warning("LLM方案生成调用失败: %s", e)
        return _build_plans_when_llm_disabled(anomalies, mandatory_specs), None

    if parsed is not None:
        if isinstance(parsed, dict):
            plans = [parsed]
        elif isinstance(parsed, list):
            plans = parsed
        else:
            plans = []
        for plan in plans:
            if isinstance(plan, dict):
                # 忽略 LLM 返回的占位 plan_id（如 plan_001），统一生成全局唯一 ID，避免跨诊断冲突。
                plan["plan_id"] = f"plan_{uuid.uuid4().hex[:8]}"
        return (plans if plans else []), usage

    logger.warning("LLM方案生成输出解析失败")
    return [
        {
            "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
            "plan_name": "默认优化方案（解析失败）",
            "description": (raw_text or "")[:8000],
            "target_indicators": [a["indicator_code"] for a in anomalies[:3]],
            "expected_improvement": {},
            "expected_roi": 1.0,
            "difficulty_score": 5,
            "urgency_score": 5,
            "priority_level": "medium",
            "steps": [],
            "auto_actions": [],
        }
    ], usage


async def generate_solutions_node(state: DiagnosisState, config: Any = None) -> dict:
    anomalies = state.get("anomalies", [])
    if not anomalies:
        return {"solution_plans": []}

    emit_progress(state, "正在生成优化方案", percent=70)
    emit_progress(state, "正在匹配优化方案模板...", percent=78)

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

    emit_progress(state, "正在生成优化方案...", percent=88)

    rules_text = format_indicator_rules_for_prompt(anomalies)
    mandatory_specs = collect_mandatory_task_specs(anomalies)
    mandatory_json = json.dumps(mandatory_specs, ensure_ascii=False)

    all_indicators = {
        "crm": state.get("crm_indicators", {}),
        "marketing": state.get("marketing_indicators", {}),
        "retention": state.get("retention_indicators", {}),
        "efficiency": state.get("efficiency_indicators", {}),
    }

    heartbeat_task = asyncio.create_task(_solution_generation_heartbeat(state))
    try:
        plans, _solution_generation_llm_usage = await _llm_generate_solutions(
            store_profile=store_profile,
            anomalies=_slim_anomalies(anomalies),
            root_causes=_slim_root_causes(state.get("root_causes", [])),
            benchmarks=_slim_benchmarks(benchmarks, anomalies),
            indicators=_slim_indicators(all_indicators, anomalies),
            historical_cases=historical_cases if historical_cases else None,
            indicator_push_rules=rules_text,
            mandatory_rule_tasks=mandatory_json,
            runnable_config=config,
        )
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
    if not isinstance(plans, list):
        plans = []
    plans = _ensure_mandatory_task_steps(plans, mandatory_specs, anomalies)
    _ensure_mandatory_coupon_auto_actions(plans, anomalies)

    for plan in plans:
        roi = plan.get("expected_roi", 0)
        diff = plan.get("difficulty_score", 5)
        urgency = plan.get("urgency_score", 5)
        plan["priority_score"] = roi * 0.6 + (10 - diff) * 0.2 + urgency * 0.2

    plans.sort(key=lambda p: p.get("priority_score", 0), reverse=True)

    emit_progress(state, f"已生成 {len(plans)} 个优化方案，等待采纳", percent=98)

    try:
        plans_summary = [{"name": p.get("plan_name", ""), "priority": p.get("priority_level", "medium")} for p in plans]
        tc = tenant_client(state["tenant_id"])
        await tc.send_plan_adoption_request(
            tenant_id=state["tenant_id"],
            store_id=state["store_id"],
            admin_account_ids=await _get_admin_accounts(
                store_profile,
                tenant_id=state.get("tenant_id"),
            ),
            thread_id=state.get("thread_id", ""),
            plans_summary=plans_summary,
        )
        plan_names = "、".join(p.get("name", "") for p in plans_summary[:3])
        await save_push_log(
            state.get("thread_id", ""),
            state["tenant_id"],
            state["store_id"],
            "message",
            "ai_plan_adoption",
            f"您有 {len(plans)} 个 AI 优化方案待审阅采纳",
            f"AI 已基于当前业务数据，为您生成了 {len(plans)} 份针对性优化方案（{plan_names}）。方案详情已准备就绪，请前往 【企业APP → AI智能诊断 → 推荐方案】 尽快查看并选择采纳，以便及时落地执行。",
            {"plans_summary": plans_summary},
        )
    except Exception as e:
        logger.warning("推送方案采纳通知失败: %s", e)

    plan_id_list = [p.get("plan_id") for p in plans if p.get("plan_id")]
    thread_id = state.get("thread_id")
    if plan_id_list and thread_id:
        try:
            await update_plan_ids(thread_id, plan_id_list)
        except Exception as e:
            logger.warning("同步 plan_ids 到 DB 失败: %s", e)

    return {
        "solution_plans": plans,
    }
