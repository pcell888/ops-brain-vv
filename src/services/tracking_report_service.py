"""复盘 LLM、报告归一化与兼容复盘接口。"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from src.agent.prompts.review_analysis import REVIEW_ANALYSIS_SYSTEM, REVIEW_ANALYSIS_USER
from src.core.compat_tracking_repo import (
    get_exec_task_stats,
    get_exec_task_team_size,
    get_review_report,
    get_tracking,
    list_exec_tasks_for_report,
    list_snapshots,
    update_review_report,
)
from src.core.calculator import INDICATOR_META
from src.core.config import CN_TZ, get_settings
from src.core.llm import build_chat_llm
from src.core.tracking_names import legacy_auto_solution_label, resolve_solution_name
from src.core.tracking_report_enrichment import needs_llm_enrichment
from src.core.tracing import extract_or_estimate_llm_usage, llm_ainvoke_in_graph

from src.services.tracking_error_service import LLMReviewReportError, TrackingServiceError
from src.services.tracking_helper_service import (
    _derive_adopted_plan_name,
    _is_generic_solution_name,
    _is_tracking_completed,
    _parse_dt,
    _safe_json_dict,
    _ser,
    _to_float,
    _to_int,
)

logger = logging.getLogger(__name__)


async def _llm_review_report(
    tracking_data: dict,
    snapshots: list[dict],
    exec_tasks: list[dict],
    *,
    strict_llm: bool = False,
    preferred_solution_name: str | None = None,
) -> tuple[dict | None, dict | None]:
    settings = get_settings()
    if not settings.llm_enabled or not settings.llm_api_key:
        return None, None

    llm = build_chat_llm(
        model=settings.llm_model,
        temperature=0.3,
        timeout=settings.llm_httpx_timeout(),
        max_retries=0,
    )
    td_for_prompt = dict(tracking_data)
    td_for_prompt["solution_name"] = resolve_solution_name(tracking_data, preferred_solution_name)
    user_msg = REVIEW_ANALYSIS_USER.format(
        tracking_data=json.dumps(td_for_prompt, ensure_ascii=False, indent=2),
        plans="[]",
        exec_tasks=json.dumps(exec_tasks, ensure_ascii=False, indent=2),
        snapshots=json.dumps(snapshots, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": REVIEW_ANALYSIS_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    try:
        resp = await llm_ainvoke_in_graph(llm, messages)
    except Exception as e:
        logger.warning("LLM 复盘生成失败: %s", e)
        if strict_llm:
            raise LLMReviewReportError("AI 复盘生成失败，请稍后重试") from e
        return None, None

    usage = extract_or_estimate_llm_usage(resp, llm=llm, messages=messages)
    if usage:
        logger.info(
            "兼容复盘 tokens(%s): prompt=%s completion=%s total=%s calls=%s",
            usage.get("usage_source", "unknown"),
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
            usage.get("calls", 1),
        )
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    parsed = _safe_json_dict(content)
    if not parsed:
        logger.warning("LLM 复盘生成解析失败")
        if strict_llm:
            raise LLMReviewReportError("AI 复盘结果解析失败，请重试")
        return None, usage
    return parsed, usage


def _build_base_report(
    tracking_id: str,
    td: dict,
    now_iso: str,
    scores: list[float],
    preferred_solution_name: str | None = None,
) -> dict:
    return {
        "tracking_id": tracking_id,
        "plan_id": td.get("plan_id", ""),
        "solution_name": resolve_solution_name(td, preferred_solution_name),
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
        cur_num, base_num = _to_float(cur_val), _to_float(base_val)
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


def _indicator_display_name(code: str) -> str:
    c = str(code or "").strip()
    if not c:
        return "未知指标"
    meta = INDICATOR_META.get(c) or {}
    name = meta.get("name") if isinstance(meta.get("name"), str) else None
    if name and name.strip():
        return name.strip()
    return c


def _build_sections(report: dict) -> list[dict]:
    indicator_analysis = report.get("indicator_analysis")
    metric_content: str | None = None
    if isinstance(indicator_analysis, list) and indicator_analysis:
        lines = [
            f"- **{_indicator_display_name(str(it.get('indicator_code') or it.get('metric_name') or ''))}**：趋势 `{str(it.get('trend') or '无变化')}`。{str(it.get('analysis') or '').strip()}".strip()
            for it in indicator_analysis
            if isinstance(it, dict)
        ]
        if lines:
            metric_content = "\n".join(lines)

    sections = report.get("sections")
    if isinstance(sections, list) and sections:
        if metric_content:
            out = [s for s in sections if isinstance(s, dict) and s.get("title") != "指标分析"]
            out.append({"title": "指标分析", "content": metric_content})
            return out
        return sections

    built: list[dict] = []
    summary = str(report.get("summary") or "").strip()
    if summary:
        built.append({"title": "复盘总结", "content": summary})
    if metric_content:
        built.append({"title": "指标分析", "content": metric_content})
    return built


def _apply_legacy_solution_placeholder_rewrite(out: dict, plan_id: object, solution_name: str) -> None:
    """将正文里历史占位「方案 {plan_id[:8]}」替换为当前解析后的方案名（不改 JSON 字段结构）。"""
    old = legacy_auto_solution_label(str(plan_id or ""))
    new = str(solution_name or "").strip()
    if not old or not new or old == new:
        return

    def rw(val: object) -> str:
        t = str(val or "")
        return t.replace(old, new) if old in t else t

    if out.get("summary"):
        out["summary"] = rw(out["summary"])
    if out.get("executive_summary"):
        out["executive_summary"] = rw(out["executive_summary"])
    recs = out.get("recommendations")
    if isinstance(recs, list):
        out["recommendations"] = [rw(x) for x in recs]
    lessons = out.get("lessons_learned")
    if isinstance(lessons, list):
        out["lessons_learned"] = [rw(x) for x in lessons]
    ind = out.get("indicator_analysis")
    if isinstance(ind, list):
        for it in ind:
            if isinstance(it, dict):
                if it.get("analysis"):
                    it["analysis"] = rw(it.get("analysis"))
                if it.get("trend"):
                    it["trend"] = rw(it.get("trend"))
    sects = out.get("sections")
    if isinstance(sects, list):
        for it in sects:
            if isinstance(it, dict) and it.get("content"):
                it["content"] = rw(it.get("content"))


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
    if preferred and (
        _is_generic_solution_name(report_name, tracking_data.get("plan_id")) or not report_name
    ):
        solution_name = preferred
    if not solution_name:
        solution_name = resolve_solution_name(tracking_data, preferred)
    out["solution_name"] = solution_name
    out["title"] = f"{solution_name}复盘报告"
    out["created_at"] = out.get("created_at") or _ser(report_created_at) or datetime.now(CN_TZ).isoformat()

    first_snapshot_at = _ser(snapshot_rows[0].get("snapshot_at")) if snapshot_rows else None
    last_snapshot_at = _ser(snapshot_rows[-1].get("snapshot_at")) if snapshot_rows else None
    started_at = out.get("started_at") or tracking_data.get("started_at") or first_snapshot_at
    completed_at = out.get("completed_at") or tracking_data.get("completed_at") or last_snapshot_at or _ser(report_created_at)
    out["started_at"] = started_at
    out["completed_at"] = completed_at

    snap_count = out.get("snapshot_count") or out.get("total_snapshots") or tracking_data.get("snapshot_count")
    if snap_count is None:
        snap_count = len(snapshot_rows)
    out["snapshot_count"] = int(snap_count or 0)

    duration_days = out.get("tracking_duration_days")
    if duration_days is None and started_at and completed_at:
        try:
            st, ed = _parse_dt(started_at), _parse_dt(completed_at)
            duration_days = max(1, (ed.date() - st.date()).days + 1) if st and ed else None
        except (TypeError, ValueError):
            duration_days = None
    out["tracking_duration_days"] = int(duration_days or 0)

    if out.get("overall_score") is None:
        score = out.get("final_score") if out.get("final_score") is not None else out.get("overall_achievement_rate")
        score_num = _to_float(score)
        out["overall_score"] = round(score_num, 2) if score_num is not None else 0

    if not isinstance(out.get("recommendations"), list) or not out.get("recommendations"):
        lessons = out.get("lessons_learned")
        out["recommendations"] = (
            [str(x) for x in lessons if str(x).strip()]
            if isinstance(lessons, list) and lessons
            else ["继续保持当前优化策略", "关注核心指标变化趋势"]
        )

    if not isinstance(out.get("metric_effects"), list) or not out.get("metric_effects"):
        out["metric_effects"] = _build_metric_effects(snapshot_rows)

    _apply_legacy_solution_placeholder_rewrite(out, tracking_data.get("plan_id"), solution_name)
    out["sections"] = _build_sections(out)
    return out


async def _derive_execution_summary(tracking_id: str, current_summary: dict, started_at, completed_at) -> dict:
    summary = dict(current_summary) if isinstance(current_summary, dict) else {}
    task_stats = await get_exec_task_stats(tracking_id)
    total_tasks = sum(task_stats.values())
    completed_tasks = task_stats["completed"]
    team_size_db = await get_exec_task_team_size(tracking_id)

    planned_duration = _to_int(summary.get("planned_duration"))
    if planned_duration is None and total_tasks > 0:
        planned_duration = 30
    actual_duration = _to_int(summary.get("actual_duration"))
    if actual_duration is None:
        st, ed = _parse_dt(started_at), _parse_dt(completed_at)
        if st and ed:
            actual_duration = max(1, (ed.date() - st.date()).days + 1)
    completion_rate = _to_float(summary.get("completion_rate"))
    if completion_rate is None:
        completion_rate = round((completed_tasks / total_tasks) * 100.0, 2) if total_tasks > 0 else 0.0
    team_size = _to_int(summary.get("team_size"))
    if team_size is None:
        team_size = team_size_db if team_size_db > 0 else 0

    summary.update(
        {
            "task_stats": task_stats,
            "completion_rate": completion_rate,
            "planned_duration": planned_duration,
            "actual_duration": actual_duration,
            "team_size": team_size,
        }
    )
    return summary


def _pending_list_item(
    thread_id: str,
    diagnosis_id: str,
    review_due_date,
    *,
    solution_name: str | None = None,
    current_score: float | None = None,
    tracking_started_at=None,
) -> dict:
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
        "review_due_date": _ser(review_due_date),
        "scheduled": True,
    }


async def get_compat_review_report(tracking_id: str) -> dict:
    try:
        row = await get_review_report(tracking_id)
        if not row:
            raise TrackingServiceError(404, "复盘报告不存在，请先完成追踪")

        report = row["report"] or {}
        if isinstance(report, str):
            report = json.loads(report)
        if not isinstance(report, dict):
            report = {}

        track_row = await get_tracking(tracking_id)
        tracking_data = (track_row or {}).get("tracking_data") or {}
        if isinstance(tracking_data, str):
            tracking_data = json.loads(tracking_data)
        if not isinstance(tracking_data, dict):
            tracking_data = {}
        if not _is_tracking_completed(tracking_data):
            raise TrackingServiceError(400, "追踪未完成，暂不可查看复盘报告")

        adopted_plan_name = await _derive_adopted_plan_name(tracking_id=tracking_id, tracking_data=tracking_data)
        snapshot_rows = await list_snapshots(tracking_id)

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
            exec_tasks = await list_exec_tasks_for_report(tracking_id)
            base_report = _build_base_report(
                tracking_id=tracking_id,
                td=tracking_data,
                now_iso=_ser(row.get("created_at")) or datetime.now(CN_TZ).isoformat(),
                scores=scores,
                preferred_solution_name=adopted_plan_name,
            )
            llm_report, review_llm_usage = await _llm_review_report(
                tracking_data={
                    **tracking_data,
                    "tracking_id": tracking_id,
                    "score_change": base_report.get("score_change"),
                    "total_snapshots": len(scores),
                },
                snapshots=snapshot_payload,
                exec_tasks=exec_tasks or [],
                preferred_solution_name=adopted_plan_name,
            )
            if llm_report:
                report = _merge_llm_report(base_report, llm_report)
                if review_llm_usage:
                    report["review_llm_usage"] = review_llm_usage

        normalized = _normalize_report_payload(
            tracking_id=tracking_id,
            report=report,
            tracking_data=tracking_data,
            report_created_at=row.get("created_at"),
            snapshot_rows=snapshot_rows,
            preferred_solution_name=adopted_plan_name,
        )
        normalized["execution_summary"] = await _derive_execution_summary(
            tracking_id=tracking_id,
            current_summary=normalized.get("execution_summary") or {},
            started_at=normalized.get("started_at"),
            completed_at=normalized.get("completed_at"),
        )

        if json.dumps(normalized, sort_keys=True, ensure_ascii=False) != json.dumps(report, sort_keys=True, ensure_ascii=False):
            await update_review_report(tracking_id, normalized)
        return normalized
    except TrackingServiceError:
        raise
    except Exception as e:
        logger.exception("查询复盘报告失败")
        raise TrackingServiceError(500, "查询失败，请稍后重试") from e
