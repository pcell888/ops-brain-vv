"""前端兼容层 — /tracking 系列接口。

基于 ai_effect_tracking / ai_effect_snapshot / ai_review_report /
ai_solution_knowledge 表提供效果追踪与复盘接口。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.agent.prompts.review_analysis import REVIEW_ANALYSIS_SYSTEM, REVIEW_ANALYSIS_USER
from src.agent.tools import MCPToolInvocationError, mcp_call, unwrap_mcp_json_value
from src.core.calculator import (
    INDICATOR_META,
    NOT_APPLICABLE_MAP,
    calculate_dimension_score,
    extract_indicator_codes,
    rebalance_weights,
    resolve_active_indicators,
)
from src.core.config import CN_TZ, get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_effect_tracking, ensure_ai_pending_review
from src.core.pending_review_repo import cancel_pending_review, get_pending_review, get_pending_review_by_thread
from src.core.solution_knowledge_repo import save_effective_plan
from src.core.tracking_report_enrichment import needs_llm_enrichment
from src.core.tenant_config import get_tenant_config
from src.api.deps import send_thread_progress
from src.core.tracking_names import resolve_solution_name
from src.mcp_servers.biz_scope import effective_store_id_for_biz

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tracking", tags=["效果追踪"])

_complete_tracking_inflight: set[str] = set()
_complete_tracking_lock = asyncio.Lock()


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


def _ser(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _to_float(v) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _parse_dt(v) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    text = str(v).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_generic_solution_name(v: object) -> bool:
    name = str(v or "").strip()
    return (not name) or name.startswith("效果追踪")


async def _get_diagnosis_health_score(cur, thread_id: str) -> float | None:
    """从 ai_diagnosis_report 取诊断时的健康评分，作为快照未采集时的兜底。"""
    try:
        await cur.execute(
            "SELECT report FROM ai_diagnosis_report WHERE thread_id = %s",
            (thread_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        report = row.get("report")
        if isinstance(report, str):
            report = json.loads(report)
        if not isinstance(report, dict):
            return None
        val = report.get("health_score")
        if val is None:
            return None
        return round(float(val), 1)
    except Exception:
        return None


async def _scheduled_row_enrichment(thread_id: str) -> tuple[str, float | None]:
    """待自动复盘且无 ai_effect_tracking 行时：采纳方案名 + 诊断 health_score。"""
    adopted_label: str | None = None
    health: float | None = None
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                adopted_label = await _derive_adopted_plan_name(cur, thread_id, {})
                health = await _get_diagnosis_health_score(cur, thread_id)
    except Exception:
        logger.exception("待复盘行展示字段查询失败 thread=%s", thread_id)
    solution_name = resolve_solution_name({}, adopted_label)
    return solution_name, health


async def _earliest_exec_task_created_at(thread_id: str) -> datetime | None:
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT MIN(created_at) AS t FROM ai_exec_task WHERE thread_id = %s",
                    (thread_id,),
                )
                row = await cur.fetchone()
                t = (row or {}).get("t")
                if t is None:
                    return None
                if isinstance(t, datetime):
                    return t
                return _parse_dt(str(t))
    except Exception:
        return None


async def _scheduled_tracking_started_at(pr: dict, thread_id: str) -> datetime | None:
    """待自动复盘时「开始时间」语义：进入效果追踪等待期（写入 ai_pending_review）的时刻；否则最早执行任务。"""
    ca = pr.get("created_at")
    if ca is not None:
        if isinstance(ca, datetime):
            return ca
        parsed = _parse_dt(str(ca))
        if parsed:
            return parsed
    return await _earliest_exec_task_created_at(thread_id)


def _extract_plan_name_from_desc(desc: object) -> str | None:
    text = str(desc or "").strip()
    if not text:
        return None
    m = re.match(r"^\[(.+?)\]", text)
    if not m:
        return None
    name = m.group(1).strip()
    return name or None


def _safe_json_dict(text: str) -> dict | None:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class LLMReviewReportError(Exception):
    """完成追踪等场景在 strict_llm 下要求 LLM 成功；失败时不静默回退规则模板。"""


async def _llm_review_report(
    tracking_data: dict,
    snapshots: list[dict],
    exec_tasks: list[dict],
    *,
    strict_llm: bool = False,
) -> dict | None:
    settings = get_settings()
    if not settings.llm_enabled or not settings.llm_api_key:
        return None

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.3,
        timeout=settings.llm_httpx_timeout(),
        max_retries=0,
    )
    user_msg = REVIEW_ANALYSIS_USER.format(
        tracking_data=json.dumps(tracking_data, ensure_ascii=False, indent=2),
        plans="[]",
        exec_tasks=json.dumps(exec_tasks, ensure_ascii=False, indent=2),
        snapshots=json.dumps(snapshots, ensure_ascii=False, indent=2),
    )
    try:
        resp = await llm.ainvoke(
            [
                {"role": "system", "content": REVIEW_ANALYSIS_SYSTEM},
                {"role": "user", "content": user_msg},
            ]
        )
    except Exception as e:
        logger.warning("LLM 复盘生成失败: %s", e)
        if strict_llm:
            raise LLMReviewReportError("AI 复盘生成失败，请稍后重试") from e
        return None

    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    parsed = _safe_json_dict(content)
    if not parsed:
        logger.warning("LLM 复盘生成解析失败")
        if strict_llm:
            raise LLMReviewReportError("AI 复盘结果解析失败，请重试")
        return None
    return parsed


def _derive_tracking_status(tracking_data: dict) -> str:
    """统一追踪状态推断：仅接受显式状态，禁止用达成率隐式判定完成。"""
    raw = str(tracking_data.get("status") or "").strip().lower()
    if raw in {"active", "completed", "cancelled", "scheduled"}:
        return raw
    return "active"


def _is_tracking_completed(tracking_data: dict) -> bool:
    return _derive_tracking_status(tracking_data) == "completed"


def _metric_status_by_change(change_pct: float) -> str:
    if change_pct >= 10:
        return "exceeds_expectation"
    if change_pct >= 0:
        return "meets_expectation"
    if change_pct <= -10:
        return "negative"
    return "below_expectation"


def _build_metric_effects(snapshot_rows: list[dict]) -> list[dict]:
    if len(snapshot_rows) < 2:
        return []

    first_sd = snapshot_rows[0].get("snapshot_data") or {}
    last_sd = snapshot_rows[-1].get("snapshot_data") or {}
    if isinstance(first_sd, str):
        first_sd = json.loads(first_sd)
    if isinstance(last_sd, str):
        last_sd = json.loads(last_sd)

    first_ind = (first_sd.get("indicators") or {}) if isinstance(first_sd, dict) else {}
    last_ind = (last_sd.get("indicators") or {}) if isinstance(last_sd, dict) else {}
    effects: list[dict] = []
    for code, raw_cur in last_ind.items():
        raw_base = first_ind.get(code)
        if raw_base is None:
            continue
        cur_val = raw_cur.get("value") if isinstance(raw_cur, dict) else raw_cur
        base_val = raw_base.get("value") if isinstance(raw_base, dict) else raw_base
        cur_num = _to_float(cur_val)
        base_num = _to_float(base_val)
        if cur_num is None or base_num is None:
            continue

        actual_change = round(cur_num - base_num, 2)
        change_pct = 0.0 if base_num == 0 else round((actual_change / abs(base_num)) * 100.0, 2)
        effects.append(
            {
                "metric_name": code,
                "baseline_value": round(base_num, 2),
                "current_value": round(cur_num, 2),
                "expected_change": 0,
                "actual_change": actual_change,
                "change_percentage": change_pct,
                "status": _metric_status_by_change(change_pct),
            }
        )
    return effects


def _build_sections(report: dict) -> list[dict]:
    sections = report.get("sections")
    if isinstance(sections, list) and sections:
        return sections

    built: list[dict] = []
    summary = str(report.get("summary") or "").strip()
    if summary:
        built.append({"title": "复盘总结", "content": summary})

    indicator_analysis = report.get("indicator_analysis")
    if isinstance(indicator_analysis, list) and indicator_analysis:
        lines: list[str] = []
        for item in indicator_analysis:
            if not isinstance(item, dict):
                continue
            code = str(item.get("indicator_code") or item.get("metric_name") or "未知指标")
            trend = str(item.get("trend") or "无变化")
            analysis = str(item.get("analysis") or "").strip()
            lines.append(f"- **{code}**：趋势 `{trend}`。{analysis}".strip())
        if lines:
            built.append({"title": "指标分析", "content": "\n".join(lines)})
    return built


def _normalize_report_payload(
    tracking_id: str,
    report: dict,
    tracking_data: dict,
    report_created_at,
    snapshot_rows: list[dict],
    preferred_solution_name: str | None = None,
) -> dict:
    out = dict(report)
    out["tracking_id"] = tracking_id

    preferred = str(preferred_solution_name or "").strip()
    report_name = str(out.get("solution_name") or "").strip()
    solution_name = report_name
    if preferred and (_is_generic_solution_name(report_name) or not report_name):
        solution_name = preferred
    if not solution_name:
        solution_name = resolve_solution_name(tracking_data, preferred)
    out["solution_name"] = solution_name
    out["title"] = out.get("title") or f"{solution_name}复盘报告"
    out["created_at"] = out.get("created_at") or _ser(report_created_at) or datetime.now(CN_TZ).isoformat()

    first_snapshot_at = _ser(snapshot_rows[0].get("snapshot_at")) if snapshot_rows else None
    last_snapshot_at = _ser(snapshot_rows[-1].get("snapshot_at")) if snapshot_rows else None
    started_at = out.get("started_at") or tracking_data.get("started_at") or first_snapshot_at
    completed_at = (
        out.get("completed_at") or tracking_data.get("completed_at") or last_snapshot_at or _ser(report_created_at)
    )
    out["started_at"] = started_at
    out["completed_at"] = completed_at

    snap_count = out.get("snapshot_count")
    if snap_count is None:
        snap_count = out.get("total_snapshots")
    if snap_count is None:
        snap_count = tracking_data.get("snapshot_count")
    if snap_count is None:
        snap_count = len(snapshot_rows)
    out["snapshot_count"] = int(snap_count or 0)

    duration_days = out.get("tracking_duration_days")
    if duration_days is None and started_at and completed_at:
        try:
            st = _parse_dt(started_at)
            ed = _parse_dt(completed_at)
            if st and ed:
                duration_days = max(1, (ed.date() - st.date()).days + 1)
            else:
                duration_days = None
        except (TypeError, ValueError):
            duration_days = None
    if duration_days is None:
        duration_days = 0
    out["tracking_duration_days"] = int(duration_days)

    if out.get("overall_score") is None:
        score = out.get("final_score") if out.get("final_score") is not None else out.get("overall_achievement_rate")
        score_num = _to_float(score)
        out["overall_score"] = round(score_num, 2) if score_num is not None else 0

    if not isinstance(out.get("recommendations"), list) or not out.get("recommendations"):
        lessons = out.get("lessons_learned")
        if isinstance(lessons, list) and lessons:
            out["recommendations"] = [str(x) for x in lessons if str(x).strip()]
        else:
            out["recommendations"] = ["继续保持当前优化策略", "关注核心指标变化趋势"]

    if not isinstance(out.get("metric_effects"), list) or not out.get("metric_effects"):
        out["metric_effects"] = _build_metric_effects(snapshot_rows)

    out["sections"] = _build_sections(out)
    return out


async def _derive_execution_summary(
    cur,
    tracking_id: str,
    current_summary: dict,
    started_at,
    completed_at,
) -> dict:
    summary = dict(current_summary) if isinstance(current_summary, dict) else {}

    await cur.execute(
        """
        SELECT COALESCE(status, 'pending') AS st, COUNT(*)::int AS cnt
        FROM ai_exec_task
        WHERE thread_id = %s
        GROUP BY COALESCE(status, 'pending')
        """,
        (tracking_id,),
    )
    stat_rows = await cur.fetchall()
    task_stats: dict[str, int] = {
        "pending": 0,
        "ready": 0,
        "running": 0,
        "paused": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0,
    }
    for sr in stat_rows or []:
        key = str(sr.get("st") or "").lower()
        if key in task_stats:
            task_stats[key] = int(sr.get("cnt") or 0)

    total_tasks = sum(task_stats.values())
    completed_tasks = task_stats["completed"]

    await cur.execute(
        """
        SELECT COUNT(DISTINCT assignee_user_id)::int AS team_size
        FROM ai_exec_task
        WHERE thread_id = %s
          AND assignee_user_id IS NOT NULL
        """,
        (tracking_id,),
    )
    team_row = await cur.fetchone()
    team_size_db = int((team_row or {}).get("team_size") or 0)

    planned_duration = _to_int(summary.get("planned_duration"))
    if planned_duration is None and total_tasks > 0:
        # 与 execution 兼容层保持一致：默认计划工期 30 天
        planned_duration = 30

    actual_duration = _to_int(summary.get("actual_duration"))
    if actual_duration is None:
        st = _parse_dt(started_at)
        ed = _parse_dt(completed_at)
        if st and ed:
            actual_duration = max(1, (ed.date() - st.date()).days + 1)

    completion_rate = _to_float(summary.get("completion_rate"))
    if completion_rate is None:
        completion_rate = round((completed_tasks / total_tasks) * 100.0, 2) if total_tasks > 0 else 0.0

    team_size = _to_int(summary.get("team_size"))
    if team_size is None:
        team_size = team_size_db if team_size_db > 0 else 0

    summary["task_stats"] = task_stats
    summary["completion_rate"] = completion_rate
    summary["planned_duration"] = planned_duration
    summary["actual_duration"] = actual_duration
    summary["team_size"] = team_size
    return summary


async def _derive_adopted_plan_name(cur, tracking_id: str, tracking_data: dict) -> str | None:
    await cur.execute(
        """SELECT plan_name FROM ai_solution_knowledge
           WHERE thread_id = %s
           ORDER BY created_at DESC LIMIT 1""",
        (tracking_id,),
    )
    sk = await cur.fetchone()
    plan_name = str((sk or {}).get("plan_name") or "").strip()
    if plan_name:
        return plan_name

    plan_id = str((tracking_data or {}).get("plan_id") or "").strip()
    if plan_id:
        await cur.execute(
            """SELECT description, task_name FROM ai_exec_task
               WHERE thread_id = %s AND plan_id = %s
               ORDER BY created_at ASC LIMIT 1""",
            (tracking_id, plan_id),
        )
    else:
        await cur.execute(
            """SELECT description, task_name FROM ai_exec_task
               WHERE thread_id = %s
               ORDER BY created_at ASC LIMIT 1""",
            (tracking_id,),
        )
    task_row = await cur.fetchone()
    if task_row:
        from_desc = _extract_plan_name_from_desc(task_row.get("description"))
        if from_desc:
            return from_desc
        from_task = str(task_row.get("task_name") or "").strip()
        if from_task and not from_task.startswith("执行计划 -"):
            return from_task
    return None


def _build_base_report(tracking_id: str, td: dict, now_iso: str, scores: list[float]) -> dict:
    return {
        "tracking_id": tracking_id,
        "plan_id": td.get("plan_id", ""),
        "solution_name": resolve_solution_name(td),
        "total_snapshots": len(scores),
        "started_at": td.get("started_at"),
        "completed_at": now_iso,
        "initial_score": scores[0] if scores else None,
        "final_score": scores[-1] if scores else None,
        "score_change": round(scores[-1] - scores[0], 1) if len(scores) >= 2 else 0,
        "trend": "improving" if len(scores) >= 2 and scores[-1] > scores[0] else "stable",
        "summary": f"追踪期间共采集 {len(scores)} 次快照",
        "recommendations": ["继续保持当前优化策略", "关注核心指标变化趋势"],
    }


def _merge_llm_report(base_report: dict, llm_report: dict | None) -> dict:
    if not isinstance(llm_report, dict):
        return base_report

    merged = dict(base_report)
    for key in ("summary", "indicator_analysis", "sections"):
        val = llm_report.get(key)
        if val:
            merged[key] = val

    lessons = llm_report.get("lessons_learned")
    recs = llm_report.get("recommendations")
    if isinstance(recs, list) and recs:
        merged["recommendations"] = [str(x) for x in recs if str(x).strip()]
    elif isinstance(lessons, list) and lessons:
        merged["recommendations"] = [str(x) for x in lessons if str(x).strip()]

    for key in ("overall_achievement_rate", "improved_indicator_count", "total_tracked_indicators"):
        val = llm_report.get(key)
        if val is not None:
            merged[key] = val
    return merged


class SnapshotBody(BaseModel):
    """首次采集快照时若尚无追踪行，需传 enterprise_id（即 tenant_id）以创建。"""

    enterprise_id: str | None = Field(default=None, description="租户/企业 ID，与所选诊断一致")
    auth_token: str | None = Field(default=None, description="可选，透传企业业务 API 鉴权（与诊断采集一致）")


_TRACKING_METRIC_TOOLS: dict[str, str] = {
    "crm": "get_crm_indicators",
    "marketing": "get_marketing_indicators",
    "retention": "get_retention_indicators",
    "efficiency": "get_efficiency_indicators",
}


async def _build_effect_tracking_snapshot(
    tenant_id: str,
    store_id_db: str,
    tracking_data: dict,
    *,
    snapshot_at: datetime,
    auth_token: str | None,
) -> dict:
    """经 MCP 拉取各维度指标并计算与诊断一致的加权健康分；快照 indicators 为扁平结构供兼容前端。"""
    active_dims, active_inds = resolve_active_indicators(
        tracking_data.get("selected_dimensions"),
        tracking_data.get("selected_indicators"),
    )
    store_id = effective_store_id_for_biz(tenant_id, store_id_db or "")
    settings = get_settings()
    tenant_config = await get_tenant_config(tenant_id)
    lookback_days = int(tenant_config.get("analysis_period_days") or settings.diagnosis_lookback_days)
    end_date = snapshot_at.strftime("%Y-%m-%d %H:%M:%S")
    start_date = (snapshot_at - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")
    common_args: dict = {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    if auth_token:
        common_args["auth_token"] = auth_token

    ordered_dims = [d for d in ("crm", "marketing", "retention", "efficiency") if d in active_dims]
    profile_task = mcp_call(
        "crm-server",
        "get_store_profile",
        {"tenant_id": tenant_id, "store_id": store_id, **({"auth_token": auth_token} if auth_token else {})},
    )
    dim_tasks = [mcp_call("metrics-server", _TRACKING_METRIC_TOOLS[d], common_args) for d in ordered_dims]
    all_results = await asyncio.gather(profile_task, *dim_tasks)

    profile = all_results[0]
    if not isinstance(profile, dict):
        profile = unwrap_mcp_json_value(profile)
    if not isinstance(profile, dict):
        profile = {}

    dim_results: dict[str, dict] = {}
    for dim, raw in zip(ordered_dims, all_results[1:]):
        v = raw
        if not isinstance(v, dict):
            v = unwrap_mcp_json_value(v)
        dim_results[dim] = v if isinstance(v, dict) else {}

    business_mode = profile.get("business_mode", "hybrid")
    na_codes = NOT_APPLICABLE_MAP.get(business_mode, set())
    for _dim, dim_data in dim_results.items():
        if dim_data and na_codes:
            raw_inds = dim_data.get("indicators", {})
            if isinstance(raw_inds, dict):
                for code in na_codes:
                    if code in raw_inds and isinstance(raw_inds[code], dict):
                        raw_inds[code]["not_applicable"] = True

    indicator_dicts = [dim_results[d] for d in ordered_dims]
    codes_for_benchmark = [c for c in extract_indicator_codes(*indicator_dicts) if c in active_inds]
    benchmarks = await mcp_call(
        "benchmark-server",
        "get_industry_benchmark",
        {
            "tenant_id": tenant_id,
            "industry_code": profile.get("industry_code", ""),
            "indicator_codes": codes_for_benchmark,
        },
    )
    if not isinstance(benchmarks, dict):
        benchmarks = unwrap_mcp_json_value(benchmarks)
    if not isinstance(benchmarks, dict):
        benchmarks = {}

    benchmark_payload = benchmarks.get("benchmarks", benchmarks)
    if not isinstance(benchmark_payload, dict):
        benchmark_payload = {}

    weights = rebalance_weights(active_dims)
    dimension_scores: dict = {}
    for dim_name in ("crm", "marketing", "retention", "efficiency"):
        if dim_name not in active_dims:
            continue
        indicators = dim_results.get(dim_name, {})
        weight = weights.get(dim_name, 0.0)
        if not indicators:
            dimension_scores[dim_name] = {"score": 60.0, "weight": weight}
            continue
        score, _, _ = calculate_dimension_score(
            indicators=indicators,
            benchmarks=benchmark_payload,
            dimension=dim_name,
            active_indicators=active_inds,
        )
        dimension_scores[dim_name] = {"score": score, "weight": weight}

    health_score = sum(d["score"] * d["weight"] for d in dimension_scores.values())

    flat: dict[str, dict] = {}
    for dim_name in ordered_dims:
        pack = dim_results.get(dim_name) or {}
        inds = pack.get("indicators", {}) if isinstance(pack, dict) else {}
        if not isinstance(inds, dict):
            continue
        for code, spec in inds.items():
            if code not in INDICATOR_META:
                continue
            if isinstance(spec, dict) and spec.get("not_applicable"):
                continue
            meta = INDICATOR_META[code]
            raw_val = spec.get("value") if isinstance(spec, dict) else spec
            try:
                val_f = round(float(raw_val), 2)
            except (TypeError, ValueError):
                continue
            unit = meta.get("unit", "")
            if isinstance(spec, dict) and spec.get("unit"):
                unit = str(spec.get("unit"))
            flat[code] = {"name": meta["name"], "value": val_f, "unit": unit}

    return {
        "snapshot_at": snapshot_at.isoformat(),
        "health_score": round(float(health_score), 1),
        "indicators": flat,
        "snapshot_type": "periodic",
        "period": {"start_date": start_date, "end_date": end_date},
        "source": "mcp_metrics",
    }


async def _ensure_effect_tracking_row(
    cur,
    thread_id: str,
    tenant_id: str,
) -> tuple[str, str, dict]:
    """若不存在则插入一条效果追踪（主键为诊断 thread_id）。返回 (store_id, tenant_id, tracking_data)。"""
    await cur.execute(
        "SELECT tenant_id, store_id, tracking_data FROM ai_effect_tracking WHERE thread_id = %s",
        (thread_id,),
    )
    row = await cur.fetchone()
    if row:
        if row["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="追踪记录与当前企业不匹配")
        td = row["tracking_data"] or {}
        if isinstance(td, str):
            td = json.loads(td)
        return row["store_id"], row["tenant_id"], td

    await cur.execute(
        """SELECT plan_id, store_id FROM ai_exec_task
           WHERE thread_id = %s AND tenant_id = %s ORDER BY created_at ASC LIMIT 1""",
        (thread_id, tenant_id),
    )
    et = await cur.fetchone()
    plan_id = (et["plan_id"] or "") if et else ""
    store_id = (et["store_id"] or "") if et else ""
    now = datetime.now(CN_TZ)
    now_iso = now.isoformat()
    td = {
        "plan_id": plan_id,
        "status": "active",
        "solution_name": (f"方案 {plan_id[:8]}" if plan_id else "效果追踪"),
        "current_score": None,
        "snapshot_count": 0,
        "started_at": now_iso,
        "last_snapshot_at": None,
        "completed_at": None,
        "source": "bootstrap_snapshot",
    }
    await cur.execute(
        """INSERT INTO ai_effect_tracking (thread_id, tenant_id, store_id, tracking_data, created_at)
           VALUES (%s, %s, %s, %s, %s)""",
        (thread_id, tenant_id, store_id, json.dumps(td), now),
    )
    try:
        await cancel_pending_review(thread_id)
    except Exception as e:
        logger.warning("取消待复盘记录（bootstrap）: %s", e)
    return store_id, tenant_id, td


# ── 启动追踪 ──────────────────────────────────────────────────────


@router.post("/start", summary="启动效果追踪")
async def start_tracking(data: dict):
    """前端 POST /tracking/start
    body: { enterprise_id, plan_id, tracking_interval_days? }
    """
    enterprise_id = data.get("enterprise_id", "")
    plan_id = data.get("plan_id", "")
    interval_days = data.get("tracking_interval_days", 7)

    if not enterprise_id or not plan_id:
        raise HTTPException(status_code=400, detail="enterprise_id 和 plan_id 必填")

    thread_id = f"trk_{uuid.uuid4().hex[:16]}"
    now = datetime.now(CN_TZ)

    tracking_data = {
        "plan_id": plan_id,
        "status": "active",
        "solution_name": f"方案 {plan_id[:8]}",
        "current_score": None,
        "snapshot_count": 0,
        "started_at": now.isoformat(),
        "last_snapshot_at": None,
        "completed_at": None,
        "tracking_interval_days": interval_days,
    }

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO ai_effect_tracking (thread_id, tenant_id, store_id, tracking_data, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (thread_id, enterprise_id, "", json.dumps(tracking_data), now),
                )
            await conn.commit()

        return {"tracking_id": thread_id, "status": "active", "message": "追踪已启动"}
    except Exception as e:
        logger.exception("启动追踪失败")
        raise HTTPException(status_code=500, detail="启动追踪失败，请稍后重试") from e


# ── 追踪列表 ─────────────────────────────────────────────────────


def _pending_list_item(
    thread_id: str,
    diagnosis_id: str,
    review_due_date,
    *,
    solution_name: str | None = None,
    current_score: float | None = None,
    tracking_started_at=None,
) -> dict:
    due = _ser(review_due_date)
    return {
        "tracking_id": thread_id,
        "plan_id": "",
        "diagnosis_id": diagnosis_id,
        "solution_name": solution_name or "效果追踪",
        "status": "scheduled",
        "current_score": current_score,
        "snapshot_count": 0,
        "started_at": _ser(tracking_started_at) if tracking_started_at is not None else None,
        "last_snapshot_at": None,
        "completed_at": None,
        "review_due_date": due,
        "scheduled": True,
    }


@router.get("/list", summary="追踪列表")
async def list_trackings(
    enterprise_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    diagnosis_id: str | None = Query(default=None, description="诊断 thread_id，仅返回该次诊断关联执行计划下的追踪"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        await ensure_ai_pending_review()

        # effect_track_delay_days>0 时图在 track_effects 前中断，复盘未跑则无 ai_effect_tracking 行；
        # 从 ai_pending_review 补一行「待自动复盘」，避免列表空白。
        pending_row = None
        pending_bonus = 0
        if enterprise_id and diagnosis_id:
            pending_row = await get_pending_review(enterprise_id, diagnosis_id)
            if pending_row and (not status or status == "scheduled"):
                pending_bonus = 1

        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_parts = []
                params: list = []
                if enterprise_id:
                    where_parts.append("t.tenant_id = %s")
                    params.append(enterprise_id)
                if diagnosis_id:
                    # LangGraph 落库：thread_id = 诊断 thread_id，tracking_data 无 plan_id；
                    # 兼容层 POST /tracking/start：thread_id = trk_*，需用 exec_task 关联诊断。
                    where_parts.append(
                        """(
                        t.thread_id = %s
                        OR EXISTS (
                            SELECT 1 FROM ai_exec_task e
                            WHERE (t.tracking_data->>'plan_id') IS NOT NULL
                              AND (t.tracking_data->>'plan_id') <> ''
                              AND e.plan_id = (t.tracking_data->>'plan_id')
                              AND e.thread_id = %s
                              AND e.tenant_id = t.tenant_id
                        )
                    )"""
                    )
                    params.append(diagnosis_id)
                    params.append(diagnosis_id)
                where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

                await cur.execute(f"SELECT COUNT(*) FROM ai_effect_tracking t {where_sql}", params)
                total_db = (await cur.fetchone() or {}).get("count", 0)
                total = int(total_db) + pending_bonus

                db_skip = max(0, skip - pending_bonus)
                db_limit = limit
                if pending_bonus and skip == 0:
                    db_limit = max(0, limit - 1)

                await cur.execute(
                    f"""SELECT t.thread_id, t.tenant_id, t.tracking_data, t.created_at,
                        (SELECT MIN(e.thread_id) FROM ai_exec_task e
                         WHERE e.plan_id = (t.tracking_data->>'plan_id')
                           AND e.tenant_id = t.tenant_id) AS diagnosis_id
                        ,(SELECT sk.plan_name FROM ai_solution_knowledge sk
                          WHERE sk.thread_id = t.thread_id
                          ORDER BY sk.created_at DESC LIMIT 1) AS adopted_plan_name
                        FROM ai_effect_tracking t
                        {where_sql}
                        ORDER BY t.created_at DESC OFFSET %s LIMIT %s""",
                    params + [db_skip, db_limit],
                )
                rows = await cur.fetchall()

        items = []
        if pending_bonus and pending_row and skip == 0:
            sol, sc = await _scheduled_row_enrichment(pending_row["thread_id"])
            track_started = await _scheduled_tracking_started_at(pending_row, pending_row["thread_id"])
            items.append(
                _pending_list_item(
                    pending_row["thread_id"],
                    diagnosis_id or pending_row["thread_id"],
                    pending_row["review_due_date"],
                    solution_name=sol,
                    current_score=sc,
                    tracking_started_at=track_started,
                )
            )

        for row in rows:
            td = row["tracking_data"] or {}
            if isinstance(td, str):
                td = json.loads(td)

            eff_status = _derive_tracking_status(td)
            if status and eff_status != status:
                continue

            items.append(
                {
                    "tracking_id": row["thread_id"],
                    "plan_id": td.get("plan_id", ""),
                    "diagnosis_id": row.get("diagnosis_id") or row["thread_id"],
                    "solution_name": resolve_solution_name(td, row.get("adopted_plan_name")),
                    "status": eff_status,
                    "current_score": td.get("current_score")
                    if td.get("current_score") is not None
                    else td.get("overall_achievement_rate"),
                    "snapshot_count": td.get("snapshot_count", 0),
                    "started_at": td.get("started_at", _ser(row["created_at"])),
                    "last_snapshot_at": td.get("last_snapshot_at"),
                    "completed_at": td.get("completed_at"),
                }
            )

        # 对 current_score 仍为 None 的条目，从诊断报告回退取 health_score
        missing_ids = [it["tracking_id"] for it in items if it.get("current_score") is None]
        if missing_ids:
            try:
                async with await AsyncConnection.connect(_conninfo()) as conn2:
                    async with conn2.cursor(row_factory=dict_row) as cur2:
                        await cur2.execute(
                            """SELECT thread_id, report->>'health_score' AS hs
                               FROM ai_diagnosis_report WHERE thread_id = ANY(%s)""",
                            (missing_ids,),
                        )
                        diag_rows = await cur2.fetchall()
                        diag_map = {
                            r["thread_id"]: round(float(r["hs"]), 1) for r in diag_rows if r.get("hs") is not None
                        }
                        for it in items:
                            if it.get("current_score") is None and it["tracking_id"] in diag_map:
                                it["current_score"] = diag_map[it["tracking_id"]]
            except Exception:
                pass

        return {"items": items, "total": total}
    except Exception:
        logger.exception("查询追踪列表失败")
        return {"items": [], "total": 0}


# ── 案例搜索（静态路由，须在 /{tracking_id} 之前） ────────────────


@router.get("/cases/search", summary="案例搜索")
async def search_cases(
    plan_name: str | None = Query(default=None, description="方案名称，模糊匹配"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_parts = []
                params: list = []
                key = (plan_name or "").strip()
                if key:
                    where_parts.append("plan_name ILIKE %s ESCAPE '\\'")
                    like = "%" + key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                    params.append(like)

                where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

                await cur.execute(f"SELECT COUNT(*) FROM ai_solution_knowledge {where_sql}", params)
                total = (await cur.fetchone() or {}).get("count", 0)

                await cur.execute(
                    f"""SELECT id, tenant_id, plan_name, target_indicators, industry_code,
                               achievement_rate, indicator_changes, created_at
                        FROM ai_solution_knowledge {where_sql}
                        ORDER BY achievement_rate DESC OFFSET %s LIMIT %s""",
                    params + [skip, limit],
                )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            items.append(
                {
                    "case_id": str(row["id"]),
                    "plan_name": row["plan_name"],
                    "industry": row.get("industry_code", ""),
                    "target_indicators": row.get("target_indicators", []),
                    "achievement_rate": row.get("achievement_rate", 0),
                    "indicator_changes": row.get("indicator_changes", []),
                    "created_at": _ser(row["created_at"]),
                }
            )

        return {"items": items, "total": total}
    except Exception:
        logger.exception("搜索案例失败")
        return {"items": [], "total": 0}


@router.get("/cases/similar", summary="相似案例")
async def get_similar_cases(
    indicators: str = Query(default=""),
    industry: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
):
    indicator_list = [i.strip() for i in indicators.split(",") if i.strip()]

    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if indicator_list:
                    await cur.execute(
                        """SELECT id, plan_name, target_indicators, industry_code,
                                  achievement_rate, indicator_changes, created_at
                           FROM ai_solution_knowledge
                           WHERE target_indicators && %s
                           ORDER BY achievement_rate DESC LIMIT %s""",
                        (indicator_list, limit),
                    )
                else:
                    where = "WHERE industry_code = %s" if industry else ""
                    params: list = [industry] if industry else []
                    await cur.execute(
                        f"""SELECT id, plan_name, target_indicators, industry_code,
                                   achievement_rate, indicator_changes, created_at
                            FROM ai_solution_knowledge {where}
                            ORDER BY achievement_rate DESC LIMIT %s""",
                        params + [limit],
                    )
                rows = await cur.fetchall()

        items = []
        for row in rows:
            items.append(
                {
                    "case_id": str(row["id"]),
                    "plan_name": row["plan_name"],
                    "industry": row.get("industry_code", ""),
                    "target_indicators": row.get("target_indicators", []),
                    "achievement_rate": row.get("achievement_rate", 0),
                    "indicator_changes": row.get("indicator_changes", []),
                    "created_at": _ser(row["created_at"]),
                }
            )

        return {"items": items, "total": len(items)}
    except Exception:
        logger.exception("查询相似案例失败")
        return {"items": [], "total": 0}


@router.get("/cases/{case_id}", summary="案例详情")
async def get_case_detail(case_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM ai_solution_knowledge WHERE id = %s",
                    (int(case_id),),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="案例不存在")

        return {
            "case_id": str(row["id"]),
            "tenant_id": row["tenant_id"],
            "thread_id": row["thread_id"],
            "plan_id": row["plan_id"],
            "plan_name": row["plan_name"],
            "industry": row.get("industry_code", ""),
            "target_indicators": row.get("target_indicators", []),
            "achievement_rate": row.get("achievement_rate", 0),
            "indicator_changes": row.get("indicator_changes", []),
            "plan_detail": row.get("plan_detail", {}),
            "lessons_learned": row.get("lessons_learned", []),
            "created_at": _ser(row["created_at"]),
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的案例ID")
    except Exception as e:
        logger.exception("查询案例详情失败")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试") from e


@router.get("/snapshots/{snapshot_id}/dashboard", summary="快照看板")
async def get_snapshot_dashboard(snapshot_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot WHERE id = %s",
                    (int(snapshot_id),),
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="快照不存在")

        sd = row["snapshot_data"] or {}
        if isinstance(sd, str):
            sd = json.loads(sd)

        return {
            "snapshot_id": snapshot_id,
            "snapshot_at": _ser(row["snapshot_at"]),
            "health_score": sd.get("health_score"),
            "indicators": sd.get("indicators", {}),
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的快照ID")
    except Exception as e:
        logger.exception("查询快照看板失败")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试") from e


# ── 追踪摘要 ─────────────────────────────────────────────────────


@router.get("/{tracking_id}", summary="追踪摘要")
async def get_tracking_summary(tracking_id: str):
    try:
        await ensure_ai_pending_review()
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                adopted_plan_name = None
                if row:
                    await cur.execute(
                        """SELECT plan_name FROM ai_solution_knowledge
                           WHERE thread_id = %s
                           ORDER BY created_at DESC LIMIT 1""",
                        (tracking_id,),
                    )
                    sk = await cur.fetchone()
                    adopted_plan_name = (sk or {}).get("plan_name")

        if not row:
            pr = await get_pending_review_by_thread(tracking_id)
            if pr:
                due = pr["review_due_date"]
                sol, scheduled_score = await _scheduled_row_enrichment(tracking_id)
                track_started = await _scheduled_tracking_started_at(pr, tracking_id)
                return {
                    "tracking_id": tracking_id,
                    "plan_id": "",
                    "solution_name": sol,
                    "status": "scheduled",
                    "current_score": scheduled_score,
                    "snapshot_count": 0,
                    "started_at": _ser(track_started) if track_started else None,
                    "last_snapshot_at": None,
                    "completed_at": None,
                    "review_due_date": _ser(due),
                    "scheduled": True,
                }
            raise HTTPException(status_code=404, detail="追踪不存在")

        td = row["tracking_data"] or {}
        if isinstance(td, str):
            td = json.loads(td)

        # 仅使用方案计划总天数字段，不做兜底
        total_duration_days = td.get("total_duration_days")
        effective_score = td.get("current_score")
        if effective_score is None:
            effective_score = td.get("overall_achievement_rate")
        if effective_score is None:
            try:
                async with await AsyncConnection.connect(_conninfo()) as conn2:
                    async with conn2.cursor(row_factory=dict_row) as cur2:
                        effective_score = await _get_diagnosis_health_score(cur2, tracking_id)
            except Exception:
                pass
        return {
            "tracking_id": row["thread_id"],
            "plan_id": td.get("plan_id", ""),
            "solution_name": resolve_solution_name(td, adopted_plan_name),
            "status": _derive_tracking_status(td),
            "current_score": effective_score,
            "snapshot_count": td.get("snapshot_count", 0),
            "started_at": td.get("started_at", _ser(row["created_at"])),
            "last_snapshot_at": td.get("last_snapshot_at"),
            "completed_at": td.get("completed_at"),
            "total_duration_days": total_duration_days,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("查询追踪摘要失败")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试") from e


# ── 采集快照 ─────────────────────────────────────────────────────


@router.post("/{tracking_id}/snapshot", summary="采集快照")
async def take_snapshot(tracking_id: str, body: SnapshotBody | None = None):
    """采集指标快照（经 MCP metrics-server 拉真实指标并计算健康分）。若尚无 ai_effect_tracking 行，请求体传 enterprise_id 则自动创建。"""
    b = body or SnapshotBody()
    now = datetime.now(CN_TZ)
    auth_token = b.auth_token.strip() if b.auth_token and str(b.auth_token).strip() else None

    try:
        await ensure_ai_effect_tracking()
        tenant_id: str = ""
        store_id: str = ""
        td: dict = {}

        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tracking_data, tenant_id, store_id FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if not row:
                    if not b.enterprise_id:
                        raise HTTPException(
                            status_code=400,
                            detail="尚无效果追踪记录，请在请求体中传入 enterprise_id 以首次创建并采集快照",
                        )
                    store_id, tenant_id, td = await _ensure_effect_tracking_row(
                        cur, tracking_id, b.enterprise_id.strip()
                    )
                else:
                    td = row["tracking_data"] or {}
                    if isinstance(td, str):
                        td = json.loads(td)
                    tenant_id = row["tenant_id"]
                    store_id = row["store_id"]

                snapshot_count_before = int(td.get("snapshot_count") or 0)
            await conn.commit()

        try:
            snapshot_data = await _build_effect_tracking_snapshot(
                tenant_id,
                store_id,
                td,
                snapshot_at=now,
                auth_token=auth_token,
            )
        except MCPToolInvocationError as e:
            logger.exception(
                "采集快照 MCP 业务错误 tracking_id=%s enterprise_id=%s",
                tracking_id,
                (b.enterprise_id or "").strip() or "-",
            )
            raise HTTPException(
                status_code=502,
                detail="指标采集失败，请稍后重试",
            ) from e
        except RuntimeError as e:
            logger.exception(
                "采集快照指标服务不可用 tracking_id=%s enterprise_id=%s",
                tracking_id,
                (b.enterprise_id or "").strip() or "-",
            )
            raise HTTPException(
                status_code=502,
                detail="指标服务暂不可用，请稍后重试",
            ) from e

        snapshot_data["snapshot_type"] = "baseline" if snapshot_count_before <= 0 else "periodic"

        td["snapshot_count"] = snapshot_count_before + 1
        td["last_snapshot_at"] = now.isoformat()
        td["current_score"] = snapshot_data.get("health_score")

        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                    (json.dumps(td), tracking_id),
                )
                await cur.execute(
                    """INSERT INTO ai_effect_snapshot (thread_id, tenant_id, store_id, snapshot_data, snapshot_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (tracking_id, tenant_id, store_id, json.dumps(snapshot_data), now),
                )
            await conn.commit()

        return {"status": "ok", "message": "快照已采集", "snapshot_at": now.isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("采集快照失败 tracking_id=%s", tracking_id)
        raise HTTPException(status_code=500, detail="采集快照失败，请稍后重试") from e


# ── 效果分析 ─────────────────────────────────────────────────────


@router.get("/{tracking_id}/analyze", summary="效果分析")
async def analyze_tracking(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at""",
                    (tracking_id,),
                )
                snapshots = await cur.fetchall()

        if not snapshots:
            diagnosis_score = None
            try:
                async with await AsyncConnection.connect(_conninfo()) as conn2:
                    async with conn2.cursor(row_factory=dict_row) as cur2:
                        diagnosis_score = await _get_diagnosis_health_score(cur2, tracking_id)
            except Exception:
                pass
            recommendations = [
                "建议先完成基线快照采集，再进行趋势分析",
                "建议提高采集频次，至少形成 2-3 个时间点的数据",
            ]
            return {
                "tracking_id": tracking_id,
                "trend": "no_data",
                "snapshots": 0,
                "analysis": "暂无快照数据",
                "latest_score": diagnosis_score,
                "first_score": diagnosis_score,
                "score_change": 0,
                "recommendations": recommendations,
                "risk_hint": "⚠ 数据采集不足，无法准确评估风险",
            }

        scores: list[float] = []
        for s in snapshots:
            sd = s["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            val = sd.get("health_score", 0)
            try:
                scores.append(float(val))
            except (TypeError, ValueError):
                scores.append(0.0)

        if len(scores) >= 2:
            trend = "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
        else:
            trend = "insufficient_data"
        score_change = round(scores[-1] - scores[0], 1) if len(scores) >= 2 else 0.0
        latest_score = round(scores[-1], 1) if scores else None
        first_score = round(scores[0], 1) if scores else None
        snapshot_count = len(snapshots)

        recent_change = round(scores[-1] - scores[-2], 1) if len(scores) >= 2 else 0.0
        recent3 = scores[-3:] if len(scores) >= 3 else scores
        recent_diffs = [recent3[i] - recent3[i - 1] for i in range(1, len(recent3))]
        rising_steps = sum(1 for d in recent_diffs if d > 0)
        falling_steps = sum(1 for d in recent_diffs if d < 0)

        avg_score = (sum(scores) / len(scores)) if scores else 0.0
        volatility = (sum((x - avg_score) ** 2 for x in scores) / len(scores)) ** 0.5 if len(scores) >= 2 else 0.0

        recommendations: list[str] = []

        # 阶段建议：每增加快照阶段都会变化
        if snapshot_count <= 1:
            recommendations.append("当前为基线阶段，建议尽快补充第 2-3 次快照，形成可比趋势")
        elif snapshot_count == 2:
            recommendations.append("已形成初步对比，建议保持固定周期采集，避免判断受偶然波动影响")
        elif 3 <= snapshot_count <= 4:
            recommendations.append("趋势进入成形期，建议按周复盘关键动作并记录干预前后变化")
        else:
            recommendations.append("样本已较充分，建议按月沉淀有效策略并复用到相似场景")

        # 总体变化分档建议
        if score_change <= -15:
            recommendations.append("整体评分显著下滑（>=15分），建议立即排查执行偏差并启动纠偏")
        elif score_change <= -5:
            recommendations.append("整体评分持续回落，建议优先处理负向变化最大的核心指标")
        elif score_change < 5:
            recommendations.append("总体变化不明显，建议聚焦 1-2 个高价值指标做针对性优化")
        elif score_change < 15:
            recommendations.append("整体评分稳步提升，建议固化当前有效动作并扩大覆盖范围")
        else:
            recommendations.append("整体评分显著提升（>=15分），建议沉淀为标准化执行模板")

        # 短期动量建议：解决“刚采集完不变”
        if snapshot_count >= 3:
            if rising_steps >= 2:
                recommendations.append("近 3 次快照连续向好，可适度提高目标阈值以释放增长空间")
            elif falling_steps >= 2:
                recommendations.append("近 3 次快照连续下行，建议缩小优化面并优先止损关键环节")
            elif recent_change > 0:
                recommendations.append("最近一次快照出现回升，建议继续观察 1-2 个周期确认趋势反转")
            elif recent_change < 0:
                recommendations.append("最近一次快照出现回落，建议复查近期新增动作对结果的影响")

        # 波动强度建议
        if snapshot_count >= 3:
            if volatility >= 8:
                recommendations.append("评分波动较大，建议统一采集口径并拆分活动/非活动时段观察")
            elif volatility <= 3:
                recommendations.append("评分波动较小，建议逐步提高优化目标，避免进入平台期")

        # 去重并截断
        deduped: list[str] = []
        for item in recommendations:
            if item not in deduped:
                deduped.append(item)
        recommendations = deduped[:4] if deduped else ["继续保持当前优化策略", "关注核心指标变化趋势"]

        # 风险提示分级
        if snapshot_count < 2:
            risk_level = "low_confidence"
            risk_hint = "⚠ 数据采集不足，分析置信度低，请先补齐快照样本"
        elif score_change <= -15 or (snapshot_count >= 3 and falling_steps >= 2):
            risk_level = "high"
            risk_hint = "⚠ 高风险：评分持续下行，建议立即进行专项排查与纠偏"
        elif score_change < -5 or recent_change < 0:
            risk_level = "medium"
            risk_hint = "⚠ 中风险：近期存在下行信号，建议优先处理负向指标"
        elif volatility >= 8:
            risk_level = "medium"
            risk_hint = "⚠ 中风险：结果波动较大，建议稳定采集口径并分场景复盘"
        else:
            risk_level = "low"
            risk_hint = "✅ 当前风险整体可控，请继续保持稳定采集与复盘"

        return {
            "tracking_id": tracking_id,
            "trend": trend,
            "snapshots": snapshot_count,
            "first_score": first_score,
            "latest_score": latest_score,
            "score_change": score_change,
            "recent_change": recent_change,
            "volatility": round(volatility, 2),
            "risk_level": risk_level,
            "analysis": f"共采集 {snapshot_count} 次快照，评分趋势: {trend}",
            "recommendations": recommendations[:4],
            "risk_hint": risk_hint,
        }
    except Exception:
        logger.exception("效果分析失败")
        diag_score: float | None = None
        try:
            async with await AsyncConnection.connect(_conninfo()) as conn_e:
                async with conn_e.cursor(row_factory=dict_row) as cur_e:
                    diag_score = await _get_diagnosis_health_score(cur_e, tracking_id)
        except Exception:
            pass
        return {
            "tracking_id": tracking_id,
            "trend": "error",
            "snapshots": 0,
            "score_change": 0,
            "analysis": "分析失败",
            "latest_score": diag_score,
            "first_score": diag_score,
            "recommendations": ["分析服务暂不可用，请稍后重试", "建议先检查快照采集是否正常"],
            "risk_hint": "⚠ 分析服务异常，当前结果仅供参考",
        }


# ── 完成追踪 ─────────────────────────────────────────────────────


async def _complete_tracking_background(tracking_id: str):
    now = datetime.now(CN_TZ)
    settings = get_settings()
    try:
        await send_thread_progress(
            tracking_id,
            {
                "type": "progress",
                "stage": "effect_track",
                "message": "正在完成追踪（收尾快照与数据汇总）…",
            },
        )
        row: dict | None = None
        td_work: dict = {}
        closing_data: dict | None = None
        should_create_closing_snapshot = False
        snapshot_payload: list[dict] = []
        scores: list[float] = []
        report: dict = {}
        exec_tasks: list[dict] = []

        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tracking_data, tenant_id, store_id FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if not row:
                    await send_thread_progress(
                        tracking_id,
                        {
                            "type": "error",
                            "stage": "effect_track",
                            "message": "追踪不存在或已删除",
                        },
                    )
                    return

                td = row["tracking_data"] or {}
                if isinstance(td, str):
                    td = json.loads(td)

                td_work = dict(td)
                td_work["status"] = "completed"
                td_work["completed_at"] = now.isoformat()

                await cur.execute(
                    """SELECT id, snapshot_data FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at DESC LIMIT 1""",
                    (tracking_id,),
                )
                latest_snapshot = await cur.fetchone()

                should_create_closing_snapshot = True
                if latest_snapshot:
                    latest_sd = latest_snapshot["snapshot_data"] or {}
                    if isinstance(latest_sd, str):
                        latest_sd = json.loads(latest_sd)
                    if latest_sd.get("snapshot_type") == "closing":
                        should_create_closing_snapshot = False

                if should_create_closing_snapshot:
                    closing_data = {
                        "snapshot_at": now.isoformat(),
                        "health_score": td_work.get("current_score"),
                        "indicators": {},
                        "snapshot_type": "closing",
                    }
                    if latest_snapshot:
                        latest_sd = latest_snapshot["snapshot_data"] or {}
                        if isinstance(latest_sd, str):
                            latest_sd = json.loads(latest_sd)
                        closing_data["indicators"] = latest_sd.get("indicators", {}) or {}
                        if latest_sd.get("health_score") is not None:
                            closing_data["health_score"] = latest_sd.get("health_score")
                    td_work["snapshot_count"] = (td_work.get("snapshot_count") or 0) + 1
                    td_work["last_snapshot_at"] = now.isoformat()
                    td_work["current_score"] = closing_data.get("health_score")

                await cur.execute(
                    """SELECT snapshot_data FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at""",
                    (tracking_id,),
                )
                snap_rows = await cur.fetchall()

                for sr in snap_rows:
                    sd = sr["snapshot_data"] or {}
                    if isinstance(sd, str):
                        sd = json.loads(sd)
                    score = _to_float(sd.get("health_score"))
                    scores.append(score if score is not None else 0.0)
                    snapshot_payload.append(
                        {
                            "snapshot_at": sd.get("snapshot_at"),
                            "health_score": sd.get("health_score"),
                            "snapshot_type": sd.get("snapshot_type"),
                            "indicators": sd.get("indicators", {}),
                        }
                    )

                if should_create_closing_snapshot and closing_data:
                    cscore = _to_float(closing_data.get("health_score"))
                    scores.append(cscore if cscore is not None else 0.0)
                    snapshot_payload.append(
                        {
                            "snapshot_at": closing_data.get("snapshot_at"),
                            "health_score": closing_data.get("health_score"),
                            "snapshot_type": closing_data.get("snapshot_type"),
                            "indicators": closing_data.get("indicators", {}),
                        }
                    )

                base_report = _build_base_report(tracking_id, td_work, now.isoformat(), scores)
                await cur.execute(
                    """SELECT task_name, status, description, deadline
                       FROM ai_exec_task
                       WHERE thread_id = %s
                       ORDER BY created_at ASC""",
                    (tracking_id,),
                )
                exec_tasks = await cur.fetchall() or []

        llm_tracking_data = {
            **td_work,
            "tracking_id": tracking_id,
            "score_change": base_report.get("score_change"),
            "total_snapshots": len(scores),
            "started_at": base_report.get("started_at"),
            "completed_at": base_report.get("completed_at"),
        }

        strict = bool(settings.llm_enabled and settings.llm_api_key)
        if strict:
            await send_thread_progress(
                tracking_id,
                {
                    "type": "progress",
                    "stage": "effect_track",
                    "message": "正在生成 AI 复盘报告，请稍候…",
                },
            )
        llm_report = await _llm_review_report(
            tracking_data=llm_tracking_data,
            snapshots=snapshot_payload,
            exec_tasks=exec_tasks,
            strict_llm=strict,
        )
        report = _merge_llm_report(base_report, llm_report)

        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if should_create_closing_snapshot and closing_data:
                    await cur.execute(
                        """INSERT INTO ai_effect_snapshot (thread_id, tenant_id, store_id, snapshot_data, snapshot_at)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (
                            tracking_id,
                            row["tenant_id"],
                            row["store_id"],
                            json.dumps(closing_data),
                            now,
                        ),
                    )

                await cur.execute(
                    "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                    (json.dumps(td_work), tracking_id),
                )

                await cur.execute(
                    """INSERT INTO ai_review_report (thread_id, tenant_id, store_id, report, created_at)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (thread_id) DO UPDATE SET report = EXCLUDED.report""",
                    (tracking_id, row["tenant_id"], row["store_id"], json.dumps(report), now),
                )
            await conn.commit()

        await send_thread_progress(
            tracking_id,
            {
                "type": "progress",
                "stage": "effect_track",
                "message": "正在沉淀有效方案…",
            },
        )
        try:
            achievement = 0.0
            if len(scores) >= 2:
                achievement = min(
                    100.0,
                    max(50.0, 50.0 + (float(scores[-1]) - float(scores[0])) * 2.0),
                )
            elif len(scores) == 1:
                achievement = 60.0
            if achievement >= 50.0:
                lessons = report.get("recommendations", [])
                if not isinstance(lessons, list):
                    lessons = []
                lessons_str = [str(x) for x in lessons[:5]]
                await save_effective_plan(
                    row["tenant_id"],
                    row["store_id"],
                    tracking_id,
                    {
                        "plan_id": td_work.get("plan_id", ""),
                        "plan_name": td_work.get("solution_name", "效果追踪"),
                        "target_indicators": [],
                    },
                    achievement,
                    [],
                    lessons_str,
                    industry_code=None,
                )
        except Exception as e:
            logger.warning("完成追踪后方案沉淀失败: %s", e)

        await send_thread_progress(
            tracking_id,
            {
                "type": "completed",
                "stage": "effect_track",
                "message": "追踪已完成，复盘报告已生成",
            },
        )
    except LLMReviewReportError as e:
        logger.warning("完成追踪：LLM 失败 %s", e)
        await send_thread_progress(
            tracking_id,
            {
                "type": "error",
                "stage": "effect_track",
                "message": str(e) or "AI 复盘失败，请稍后重试",
            },
        )
    except Exception:
        logger.exception("完成追踪失败")
        await send_thread_progress(
            tracking_id,
            {
                "type": "error",
                "stage": "effect_track",
                "message": "完成追踪失败，请稍后重试",
            },
        )


@router.post("/{tracking_id}/complete", summary="完成追踪")
async def complete_tracking(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT 1 FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                if not await cur.fetchone():
                    raise HTTPException(status_code=404, detail="追踪不存在")

        async with _complete_tracking_lock:
            if tracking_id in _complete_tracking_inflight:
                return {
                    "status": "accepted",
                    "message": "完成追踪正在处理中，请留意页面进度",
                }
            _complete_tracking_inflight.add(tracking_id)

        async def _run():
            try:
                await _complete_tracking_background(tracking_id)
            finally:
                async with _complete_tracking_lock:
                    _complete_tracking_inflight.discard(tracking_id)

        asyncio.create_task(_run())
        return {
            "status": "accepted",
            "message": "已开始完成追踪，耗时操作将在后台执行并通过 WebSocket 推送进度",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("完成追踪任务启动失败")
        async with _complete_tracking_lock:
            _complete_tracking_inflight.discard(tracking_id)
        raise HTTPException(status_code=500, detail="完成追踪失败，请稍后重试") from e


# ── 取消追踪 ─────────────────────────────────────────────────────


@router.post("/{tracking_id}/cancel", summary="取消追踪")
async def cancel_tracking(tracking_id: str):
    try:
        row = None
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tracking_data FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if row:
                    td = row["tracking_data"] or {}
                    if isinstance(td, str):
                        td = json.loads(td)

                    td["status"] = "cancelled"

                    await cur.execute(
                        "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                        (json.dumps(td), tracking_id),
                    )
            await conn.commit()

        if row:
            return {"status": "ok", "message": "追踪已停止"}

        pr = await get_pending_review_by_thread(tracking_id)
        if pr:
            await cancel_pending_review(tracking_id)
            return {"status": "ok", "message": "已取消待复盘调度"}

        raise HTTPException(status_code=404, detail="追踪不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("取消追踪失败")
        raise HTTPException(status_code=500, detail="取消失败，请稍后重试") from e


# ── 指标趋势 ─────────────────────────────────────────────────────


@router.get("/{tracking_id}/trends", summary="指标趋势")
async def get_trends(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at""",
                    (tracking_id,),
                )
                rows = await cur.fetchall()

        trends: dict[str, list] = {}
        timestamps = []

        for row in rows:
            sd = row["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            timestamps.append(_ser(row["snapshot_at"]))
            for code, val in (sd.get("indicators") or {}).items():
                if code not in trends:
                    trends[code] = []
                trends[code].append(val.get("value") if isinstance(val, dict) else val)

        return {
            "tracking_id": tracking_id,
            "timestamps": timestamps,
            "indicators": trends,
        }
    except Exception:
        logger.exception("查询趋势失败 tracking_id=%s", tracking_id)
        return {"tracking_id": tracking_id, "timestamps": [], "indicators": {}}


# ── 复盘报告 ─────────────────────────────────────────────────────


@router.get("/{tracking_id}/report", summary="复盘报告")
async def get_report(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT report, created_at FROM ai_review_report WHERE thread_id = %s",
                    (tracking_id,),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="复盘报告不存在，请先完成追踪")

                report = row["report"] or {}
                if isinstance(report, str):
                    report = json.loads(report)
                if not isinstance(report, dict):
                    report = {}

                await cur.execute(
                    "SELECT tracking_data FROM ai_effect_tracking WHERE thread_id = %s",
                    (tracking_id,),
                )
                track_row = await cur.fetchone()
                tracking_data = (track_row or {}).get("tracking_data") or {}
                if isinstance(tracking_data, str):
                    tracking_data = json.loads(tracking_data)
                if not isinstance(tracking_data, dict):
                    tracking_data = {}
                if not _is_tracking_completed(tracking_data):
                    raise HTTPException(status_code=400, detail="追踪未完成，暂不可查看复盘报告")

                adopted_plan_name = await _derive_adopted_plan_name(
                    cur=cur,
                    tracking_id=tracking_id,
                    tracking_data=tracking_data,
                )

                await cur.execute(
                    """SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at ASC""",
                    (tracking_id,),
                )
                snapshot_rows = await cur.fetchall()

                if needs_llm_enrichment(report):
                    snapshot_payload: list[dict] = []
                    scores: list[float] = []
                    for sr in snapshot_rows:
                        sd = sr["snapshot_data"] or {}
                        if isinstance(sd, str):
                            sd = json.loads(sd)
                        score = _to_float(sd.get("health_score"))
                        scores.append(score if score is not None else 0.0)
                        snapshot_payload.append(
                            {
                                "snapshot_at": sd.get("snapshot_at") or _ser(sr.get("snapshot_at")),
                                "health_score": sd.get("health_score"),
                                "snapshot_type": sd.get("snapshot_type"),
                                "indicators": sd.get("indicators", {}),
                            }
                        )
                    await cur.execute(
                        """SELECT task_name, status, description, deadline
                           FROM ai_exec_task
                           WHERE thread_id = %s
                           ORDER BY created_at ASC""",
                        (tracking_id,),
                    )
                    exec_tasks = await cur.fetchall()
                    base_report = _build_base_report(
                        tracking_id=tracking_id,
                        td=tracking_data,
                        now_iso=_ser(row.get("created_at")) or datetime.now(CN_TZ).isoformat(),
                        scores=scores,
                    )
                    llm_report = await _llm_review_report(
                        tracking_data={
                            **tracking_data,
                            "tracking_id": tracking_id,
                            "score_change": base_report.get("score_change"),
                            "total_snapshots": len(scores),
                        },
                        snapshots=snapshot_payload,
                        exec_tasks=exec_tasks or [],
                    )
                    if llm_report:
                        report = _merge_llm_report(base_report, llm_report)

                normalized = _normalize_report_payload(
                    tracking_id=tracking_id,
                    report=report,
                    tracking_data=tracking_data,
                    report_created_at=row.get("created_at"),
                    snapshot_rows=snapshot_rows,
                    preferred_solution_name=adopted_plan_name,
                )
                normalized["execution_summary"] = await _derive_execution_summary(
                    cur=cur,
                    tracking_id=tracking_id,
                    current_summary=normalized.get("execution_summary") or {},
                    started_at=normalized.get("started_at"),
                    completed_at=normalized.get("completed_at"),
                )

                # 补齐后的结构回写，后续读取稳定一致（不含执行摘要/任务执行字段）。
                if json.dumps(normalized, sort_keys=True, ensure_ascii=False) != json.dumps(
                    report, sort_keys=True, ensure_ascii=False
                ):
                    await cur.execute(
                        "UPDATE ai_review_report SET report = %s WHERE thread_id = %s",
                        (json.dumps(normalized, ensure_ascii=False), tracking_id),
                    )
                    await conn.commit()

        return normalized
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("查询复盘报告失败")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试") from e


# ── 快照列表 ─────────────────────────────────────────────────────


@router.get("/{tracking_id}/snapshots", summary="快照列表")
async def get_snapshots(tracking_id: str):
    try:
        async with await AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """SELECT id, snapshot_data, snapshot_at FROM ai_effect_snapshot
                       WHERE thread_id = %s ORDER BY snapshot_at ASC""",
                    (tracking_id,),
                )
                rows = await cur.fetchall()

        items = []
        prev_indicators: dict[str, float] = {}
        for row in rows:
            sd = row["snapshot_data"] or {}
            if isinstance(sd, str):
                sd = json.loads(sd)
            indicators = sd.get("indicators", {}) or {}
            indicator_changes: list[dict] = []
            current_indicators: dict[str, float] = {}
            for code, raw in indicators.items():
                if isinstance(raw, dict):
                    name = raw.get("name", code)
                    value = raw.get("value")
                    unit = raw.get("unit", "")
                else:
                    name = code
                    value = raw
                    unit = ""
                if value is None:
                    continue
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    continue
                last_val = prev_indicators.get(code)
                delta = None if last_val is None else round(num - last_val, 2)
                current_indicators[code] = num
                indicator_changes.append(
                    {
                        "indicator_code": code,
                        "name": name,
                        "value": round(num, 2),
                        "unit": unit,
                        "delta_vs_prev": delta,
                    }
                )
            # 变化幅度大的排前面，便于详情页直接展示关键差异
            indicator_changes.sort(
                key=lambda x: abs(x["delta_vs_prev"]) if x["delta_vs_prev"] is not None else -1,
                reverse=True,
            )
            items.append(
                {
                    "snapshot_id": str(row["id"]),
                    "snapshot_at": _ser(row["snapshot_at"]),
                    "health_score": sd.get("health_score"),
                    "snapshot_type": sd.get("snapshot_type", "periodic"),
                    "indicator_count": len(indicator_changes),
                    "indicator_changes": indicator_changes,
                }
            )
            prev_indicators = current_indicators
        # 前端时间线习惯按最近在前
        items.reverse()
        return {"items": items, "total": len(items)}
    except Exception:
        logger.exception("查询快照列表失败")
        return {"items": [], "total": 0}


# ── 看板数据（简化版） ───────────────────────────────────────────


@router.get("/{tracking_id}/dashboard/funnel", summary="转化漏斗")
async def get_dashboard_funnel(tracking_id: str):
    return {
        "tracking_id": tracking_id,
        "stages": [
            {"name": "浏览", "value": 10000},
            {"name": "加购", "value": 3500},
            {"name": "下单", "value": 1800},
            {"name": "支付", "value": 1500},
            {"name": "完成", "value": 1200},
        ],
    }


@router.get("/{tracking_id}/dashboard/teams", summary="团队对比")
async def get_dashboard_teams(tracking_id: str):
    return {
        "tracking_id": tracking_id,
        "teams": [
            {"name": "销售一组", "score": 82, "deals": 45},
            {"name": "销售二组", "score": 76, "deals": 38},
            {"name": "销售三组", "score": 88, "deals": 52},
        ],
    }


@router.get("/{tracking_id}/dashboard/ranking", summary="销售排名")
async def get_dashboard_ranking(tracking_id: str, limit: int = Query(default=10)):
    return {
        "tracking_id": tracking_id,
        "rankings": [
            {"rank": 1, "name": "张三", "amount": 125000, "deals": 18},
            {"rank": 2, "name": "李四", "amount": 98000, "deals": 15},
            {"rank": 3, "name": "王五", "amount": 87000, "deals": 12},
        ],
    }


@router.get("/{tracking_id}/dashboard/summary", summary="看板汇总")
async def get_dashboard_summary(tracking_id: str):
    funnel = await get_dashboard_funnel(tracking_id)
    teams = await get_dashboard_teams(tracking_id)
    ranking = await get_dashboard_ranking(tracking_id)
    return {
        "tracking_id": tracking_id,
        "funnel": funnel,
        "teams": teams,
        "ranking": ranking,
    }
