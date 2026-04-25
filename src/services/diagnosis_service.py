"""诊断业务逻辑服务层。

封装诊断相关的核心业务逻辑，供 API 路由层调用。
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from src.repositories.diagnosis_session import get_session
from src.repositories.diagnosis_report import list_reports, get_report as get_report_from_db
from src.runtime.task_runner import get_graph_state_values
from src.core.calculator import (
    INDICATOR_META,
    DEFAULT_BENCHMARKS,
    DEFAULT_DIMENSION_WEIGHTS,
    ALL_DIMENSIONS,
    calculate_dimension_benchmarks_scores,
)
from src.core.diagnosis_engine import Phase, phase_to_next_nodes
from src.core.phases import calc_overall_progress, phase_name, infer_next_phase
from src.core.progress_utils import is_thread_running_full, safe_percent
from src.runtime.progress_store import progress_cache
from src.runtime.running_tasks import running_tasks
from src.runtime.thread_enterprise import get_running_threads_for_enterprise
from src.core.config import CN_TZ
from src.core.datetime_cn import serialize_instant_cn
from src.repositories.async_job_meta import (
    JOB_STATUS_CANCELLED,
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    get_latest_job_by_thread,
)

logger = logging.getLogger(__name__)


def _score_to_status(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "warning"
    return "danger"


def _map_severity(sev: str) -> str:
    return {"high": "critical", "medium": "high", "low": "medium"}.get(sev, sev)


def _normalize_recommendations(val: object) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, list):
        return [x.strip() for x in val if isinstance(x, str) and x.strip()]
    return []


def _list_item_cn_time(raw: object) -> tuple[str, str | None]:
    if raw is None:
        return "诊断", None
    dt: datetime | None = None
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str) and raw:
        s = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        try:
            dt = datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return "诊断", raw
    else:
        return "诊断", None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(CN_TZ)
    return local.strftime("诊断 %Y-%m-%d %H:%M"), local.isoformat(timespec="seconds")


def _thread_id_created_at(thread_id: str) -> datetime | None:
    if not thread_id.startswith("diag_"):
        return None
    try:
        ts = thread_id.split("_", 2)[1]
        dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
        return dt.replace(tzinfo=timezone.utc).astimezone(CN_TZ)
    except (IndexError, ValueError):
        return None


def _item_created_at_sort_key(item: dict) -> tuple[float, str]:
    raw = item.get("created_at")
    if isinstance(raw, str) and raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00") if raw.endswith("Z") else raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp(), str(item.get("diagnosis_id") or "")
        except (TypeError, ValueError):
            pass
    return 0.0, str(item.get("diagnosis_id") or "")


async def _extract_error_message(values: dict, diagnosis_id: str) -> str:
    cached = (await progress_cache.aget(diagnosis_id)) or {}
    cached_message = str(cached.get("message") or "").strip()
    if cached_message:
        return cached_message
    msgs = values.get("progress_messages") or []
    for m in reversed(msgs if isinstance(msgs, list) else []):
        if isinstance(m, dict) and m.get("content"):
            return str(m["content"])
    return "诊断执行失败"


def extract_total_score(raw: dict) -> float:
    raw_health_score = raw.get("health_score", 0)
    if isinstance(raw_health_score, dict):
        return float(raw_health_score.get("total_score", 0))
    return float(raw_health_score)


_extract_total_score = extract_total_score


def _empty_health_trend() -> dict:
    return {"previous_score": None, "change": None, "direction": None}


def _status_payload(
    diagnosis_id: str,
    *,
    status: str,
    phase: str,
    progress: int,
    message: str,
    health_score: float | None,
) -> dict:
    phase_progress = max(0, min(100, int(progress)))
    overall = calc_overall_progress(phase, phase_progress)
    return {
        "diagnosis_id": diagnosis_id,
        "status": status,
        "phase": phase,
        "phase_name": phase_name(phase),
        "progress": phase_progress,
        "overall_progress": overall,
        "next_phase": infer_next_phase(phase, status),
        "message": message,
        "health_score": health_score,
    }


_get_session_state = get_graph_state_values


def _last_progress_from_values(values: dict) -> tuple[str, int]:
    msg = "诊断执行中..."
    progress = 0
    msgs = values.get("progress_messages") or []
    if msgs and isinstance(msgs, list):
        last = msgs[-1] if isinstance(msgs[-1], dict) else {}
        msg = str(last.get("content", "")) or msg
        try:
            progress = int(float(last.get("percent", 0)))
        except (TypeError, ValueError):
            pass
    return msg, progress


async def _last_progress_from_cache_or_values(thread_id: str, values: dict) -> tuple[str, int]:
    cached = await progress_cache.aget(thread_id)
    if cached:
        msg = cached.get("message", "诊断执行中...")
        progress = safe_percent(cached.get("percent", 0))
        return str(msg), progress
    return _last_progress_from_values(values)


# ── 核心业务逻辑 ──────────────────────────────────────────────


async def get_diagnosis_list_items(
    tenant_id: str | None,
    skip: int,
    limit: int,
    store_id: str | None = None,
    include_running: bool = True,
) -> tuple[list[dict], int]:
    page = skip // limit + 1 if limit else 1
    items, total = await list_reports(tenant_id, store_id, page, limit)

    for row in items:
        if "created_at" in row and row.get("created_at") is not None:
            row["created_at"] = serialize_instant_cn(row["created_at"])

    db_thread_ids = {row.get("thread_id", "") for row in items}

    running_not_in_db: list[dict] = []
    if include_running and tenant_id and skip == 0:
        running_thread_ids = await get_running_threads_for_enterprise(tenant_id)
        for tid in running_thread_ids:
            if await is_thread_running_full(tid) and tid not in db_thread_ids:
                item = await _build_running_item(tid)
                if item:
                    running_not_in_db.append(item)

    result_items = []
    result_items.extend(running_not_in_db)

    for row in items:
        thread_id = row.get("thread_id", "")
        item = await _build_list_item_from_row(thread_id, row)
        result_items.append(item)

    result_items.sort(key=_item_created_at_sort_key, reverse=True)
    if skip == 0 and limit > 0:
        result_items = result_items[:limit]

    adjusted_total = total + len(running_not_in_db)
    return result_items, adjusted_total


async def _build_running_item(thread_id: str) -> dict | None:
    status = "running"
    progress = 0
    message = "诊断执行中..."

    try:
        values, _ = await _get_session_state(thread_id)
        if values:
            msg, pct = _last_progress_from_values(values)
            if msg != "诊断执行中...":
                message = msg
            if pct > 0:
                progress = pct
    except Exception:
        pass

    created_at = _thread_id_created_at(thread_id) or datetime.now(CN_TZ)
    return {
        "diagnosis_id": thread_id,
        "name": created_at.strftime("诊断 %Y-%m-%d %H:%M"),
        "status": status,
        "progress": progress,
        "message": message,
        "error_message": None,
        "health_score": None,
        "anomaly_count": None,
        "report_ready": False,
        "trigger_type": "manual",
        "created_at": created_at.isoformat(timespec="seconds"),
    }


async def _build_list_item_from_row(thread_id: str, row: dict) -> dict:
    report = await get_report_from_db(thread_id)

    status = "completed"
    progress = 100
    message = None
    error_message = None
    health_score_val = None
    anomaly_count = None
    report_ready = False

    if report:
        if report.get("status") == "failed":
            status = "failed"
            progress = 0
            error_message = report.get("error") or "诊断执行失败"
            message = error_message
            report_ready = True
        else:
            health_score_val = report.get("health_score")
            anomalies = report.get("anomalies") or []
            anomaly_count = len(anomalies)
            report_ready = True
        if await is_thread_running_full(thread_id):
            status = "running"
            progress = 0
            message = "诊断执行中..."
            try:
                values, _ = await _get_session_state(thread_id)
                if values:
                    msg, pct = _last_progress_from_values(values)
                    if msg != "诊断执行中...":
                        message = msg
                    if pct > 0:
                        progress = pct
            except Exception:
                pass
    else:
        is_task_running = await is_thread_running_full(thread_id)

        values, next_nodes = await _get_session_state(thread_id)
        if values.get("diagnosis_report"):
            report = values["diagnosis_report"]
            report_ready = True
            health_score_val = report.get("health_score")
            anomaly_count = len(report.get("anomalies") or [])
        elif is_task_running:
            status = "running"
            msg, pct = _last_progress_from_values(values)
            message = msg
            progress = pct
        elif next_nodes:
            status = "failed"
            error_message = await _extract_error_message(values, thread_id)
            message = error_message
        else:
            status = "failed"
            error_message = await _extract_error_message(values, thread_id)
            message = error_message

    _created_at = row.get("created_at")
    _name, _created_at_str = _list_item_cn_time(_created_at)

    return {
        "diagnosis_id": thread_id,
        "name": _name,
        "status": status,
        "progress": progress,
        "message": message,
        "error_message": error_message,
        "health_score": health_score_val,
        "anomaly_count": anomaly_count,
        "report_ready": report_ready,
        "trigger_type": row.get("trigger_type", "manual"),
        "created_at": _created_at_str,
    }


async def get_diagnosis_report_data(diagnosis_id: str) -> dict | None:
    report = await get_report_from_db(diagnosis_id)
    if report is None:
        values, _ = await _get_session_state(diagnosis_id)
        report = values.get("diagnosis_report") if isinstance(values, dict) else None
    return report


async def compute_health_trend(
    diagnosis_id: str,
    tenant_id: str | None,
    current_total_score: float,
) -> dict:
    empty = _empty_health_trend()
    if not tenant_id:
        return empty
    try:
        items, _ = await list_reports(tenant_id, None, 1, 100)
    except Exception as e:
        logger.debug("趋势计算列表失败: %s", e)
        return empty
    idx = next((i for i, row in enumerate(items) if row.get("thread_id") == diagnosis_id), None)
    if idx is None or idx + 1 >= len(items):
        return empty
    prev_tid = items[idx + 1].get("thread_id")
    if not prev_tid:
        return empty
    prev_report = await get_report_from_db(prev_tid)
    if not prev_report:
        return empty
    prev_hs = prev_report.get("health_score", 0)
    if isinstance(prev_hs, dict):
        prev_score = float(prev_hs.get("total_score", 0))
    else:
        prev_score = float(prev_hs)
    change = round(current_total_score - prev_score, 1)
    if change > 0:
        direction = "up"
    elif change < 0:
        direction = "down"
    else:
        direction = "stable"
    return {
        "previous_score": round(prev_score, 1),
        "change": change,
        "direction": direction,
    }


def transform_report_to_frontend_format(thread_id: str, raw: dict, trend: dict | None = None) -> dict:
    raw_health_score = raw.get("health_score", 0)
    if isinstance(raw_health_score, dict):
        total_score = raw_health_score.get("total_score", 0)
    else:
        total_score = float(raw_health_score)

    raw_dim_scores = raw.get("dimension_scores") or {}
    dim_indicator_scores = raw.get("dimension_indicator_scores") or {}

    dimension_scores_list = []
    for dim_name, dim_data in raw_dim_scores.items():
        score = dim_data.get("score", 60) if isinstance(dim_data, dict) else float(dim_data)
        weight = (
            dim_data.get("weight", DEFAULT_DIMENSION_WEIGHTS.get(dim_name, 0.25))
            if isinstance(dim_data, dict)
            else DEFAULT_DIMENSION_WEIGHTS.get(dim_name, 0.25)
        )

        metrics_detail = []
        for ind in dim_indicator_scores.get(dim_name, []):
            code = ind.get("indicator_code", "")
            bench = DEFAULT_BENCHMARKS.get(code, {})
            metrics_detail.append(
                {
                    "name": code,
                    "display_name": ind.get("indicator_name", code),
                    "value": ind.get("current_value", 0),
                    "unit": ind.get("unit", "%"),
                    "score": ind.get("score", 60),
                    "benchmark_avg": bench.get("avg_value", 0) if isinstance(bench, dict) else 0,
                    "benchmark_excellent": bench.get("excellent_value", 0) if isinstance(bench, dict) else 0,
                }
            )

        dimension_scores_list.append(
            {
                "dimension": dim_name,
                "score": score,
                "weight": weight,
                "weighted_score": round(score * weight, 2),
                "status": _score_to_status(score),
                "metrics_detail": metrics_detail,
            }
        )

    raw_anomalies = raw.get("anomalies") or []
    anomalies_list = []
    for a in raw_anomalies:
        root_cause = a.get("root_cause")
        root_cause_chain = []
        if root_cause and isinstance(root_cause, dict):
            cause_text = root_cause.get("cause", "")
            if cause_text:
                root_cause_chain = [s.strip() for s in cause_text.split("→") if s.strip()] or [cause_text]
        code = a.get("indicator_code", "")
        meta = INDICATOR_META.get(code, {})

        stable_id = a.get("id") or hashlib.md5(f"{thread_id}:{code}".encode()).hexdigest()[:8]
        anomalies_list.append(
            {
                "id": stable_id,
                "rule_id": code,
                "rule_name": a.get("indicator_name") or meta.get("name", code),
                "metric_name": code,
                "dimension": a.get("dimension", ""),
                "current_value": a.get("current_value", 0),
                "benchmark_value": a.get("benchmark_avg"),
                "gap_percentage": abs(a.get("deviation_pct", 0)),
                "severity": _map_severity(a.get("severity", "low")),
                "root_cause_chain": root_cause_chain,
                "unit": meta.get("unit", "%"),
            }
        )

    raw_root_causes = raw.get("root_causes") or []
    root_cause_analyses = []
    for rc in raw_root_causes:
        root_cause_analyses.append(
            {
                "metric_name": rc.get("anomaly_indicator", ""),
                "cause_chain": [
                    {"step": 1, "description": rc.get("cause", ""), "is_root": True},
                ],
                "explanation": rc.get("evidence", ""),
                "recommendations": _normalize_recommendations(rc.get("recommendations")),
            }
        )

    benchmark_dimension_scores = []
    dim_bench_scores = raw.get("dimension_benchmarks_scores") or {}
    if dim_bench_scores:
        for dim_name, score in dim_bench_scores.items():
            benchmark_dimension_scores.append(
                {
                    "dimension": dim_name,
                    "score": score,
                }
            )

    health_score_obj = {
        "total_score": round(total_score, 1),
        "status": _score_to_status(total_score),
        "dimension_scores": dimension_scores_list,
        "trend": trend if trend is not None else _empty_health_trend(),
    }

    return {
        "diagnosis_id": thread_id,
        "enterprise_id": raw.get("tenant_id", ""),
        "store_id": raw.get("store_id", ""),
        "status": "completed",
        "health_score": health_score_obj,
        "anomalies": anomalies_list,
        "root_cause_analyses": root_cause_analyses,
        "benchmark_dimension_scores": benchmark_dimension_scores,
        "created_at": raw.get("generated_at"),
        "completed_at": raw.get("generated_at"),
        "summary": raw.get("summary", ""),
    }


def calculate_benchmark_dimension_scores(industry: str = "general") -> dict:
    dim_benchmarks: dict[str, list[dict]] = {}
    for code, meta in INDICATOR_META.items():
        dim = meta["dimension"]
        bench = DEFAULT_BENCHMARKS.get(code)
        if bench is None:
            continue
        dim_benchmarks.setdefault(dim, []).append(
            {
                "indicator_code": code,
                "indicator_name": meta["name"],
                "unit": meta["unit"],
                "avg_value": bench.get("avg_value") if isinstance(bench, dict) else bench,
                "excellent_value": bench.get("excellent_value") if isinstance(bench, dict) else None,
            }
        )

    scores = calculate_dimension_benchmarks_scores(dim_benchmarks)

    return {
        "industry": industry,
        "dimension_scores": [{"dimension": dim, "score": scores.get(dim, 60.0)} for dim in ALL_DIMENSIONS],
    }


async def get_diagnosis_status(diagnosis_id: str) -> dict:
    report = await get_report_from_db(diagnosis_id)
    if report:
        wait_adoption_body = await _status_wait_adoption(diagnosis_id, report)
        if wait_adoption_body is not None:
            return wait_adoption_body
        running_body = await _status_while_graph_running(diagnosis_id, report)
        if running_body is not None:
            return running_body
        hs = report.get("health_score", 0)
        return _status_payload(
            diagnosis_id,
            status="completed",
            phase="completed",
            progress=100,
            message="诊断完成",
            health_score=hs if not isinstance(hs, dict) else hs.get("total_score", 0),
        )

    task = running_tasks.get(diagnosis_id)
    is_running = await is_thread_running_full(diagnosis_id)
    latest_job = await get_latest_job_by_thread(diagnosis_id)
    if is_running:
        try:
            values, next_nodes = await _get_session_state(diagnosis_id)
            if "wait_adoption" in next_nodes:
                rep_early = report
                if not rep_early and values:
                    dr = values.get("diagnosis_report")
                    if isinstance(dr, dict):
                        rep_early = dr
                w_early = await _status_wait_adoption(diagnosis_id, rep_early)
                if w_early is not None:
                    return w_early
        except Exception:
            pass
        if isinstance(latest_job, dict):
            job_status = str(latest_job.get("status") or "").strip().lower()
            job_error = str(latest_job.get("error") or "").strip()
            if job_status == JOB_STATUS_QUEUED:
                queued_seconds = 0
                updated_at = latest_job.get("updated_at")
                if isinstance(updated_at, datetime):
                    queued_seconds = max(
                        0,
                        int((datetime.now(tz=updated_at.tzinfo or timezone.utc) - updated_at).total_seconds()),
                    )
                wait_note = (
                    "（可能未启动诊断 Worker）"
                    if queued_seconds >= 30
                    else ""
                )
                return _status_payload(
                    diagnosis_id,
                    status="pending",
                    phase="diagnosis",
                    progress=0,
                    message=f"任务排队中，等待诊断 Worker 处理{wait_note}",
                    health_score=None,
                )
            if job_status == JOB_STATUS_RUNNING:
                pass
            if job_status in {JOB_STATUS_FAILED, JOB_STATUS_CANCELLED}:
                progress = 0
                cached = await progress_cache.aget(diagnosis_id)
                if cached:
                    progress = safe_percent(cached.get("percent"))
                return _status_payload(
                    diagnosis_id,
                    status="failed",
                    phase="diagnosis",
                    progress=progress,
                    message=job_error or ("诊断已取消" if job_status == JOB_STATUS_CANCELLED else "诊断执行失败"),
                    health_score=None,
                )
        progress = 0
        msg = "诊断执行中..."
        cached = await progress_cache.aget(diagnosis_id)
        if cached:
            cached_type = str(cached.get("type") or "").strip().lower()
            msg = cached.get("message", msg)
            progress = safe_percent(cached.get("percent", 0))
            if cached_type == "error":
                error_progress = progress
                return _status_payload(
                    diagnosis_id,
                    status="failed",
                    phase="diagnosis",
                    progress=error_progress,
                    message=str(msg or "诊断执行失败"),
                    health_score=None,
                )
        else:
            try:
                values, _ = await _get_session_state(diagnosis_id)
                msg, progress = _last_progress_from_values(values)
            except Exception:
                pass
        return _status_payload(
            diagnosis_id,
            status="pending" if progress <= 0 else "running",
            phase="diagnosis",
            progress=progress,
            message=msg,
            health_score=None,
        )

    succeeded_without_report = False
    succeeded_updated_at: datetime | None = None
    if isinstance(latest_job, dict):
        job_status = str(latest_job.get("status") or "").strip().lower()
        job_error = str(latest_job.get("error") or "").strip()
        if job_status == JOB_STATUS_FAILED:
            progress = 0
            cached = await progress_cache.aget(diagnosis_id)
            if cached:
                progress = safe_percent(cached.get("percent"))
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=progress,
                message=job_error or "诊断执行失败",
                health_score=None,
            )
        if job_status == JOB_STATUS_CANCELLED:
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=0,
                message=job_error or "诊断已取消",
                health_score=None,
            )
        if job_status == JOB_STATUS_SUCCEEDED:
            succeeded_without_report = True
            updated_at = latest_job.get("updated_at")
            if isinstance(updated_at, datetime):
                succeeded_updated_at = updated_at

    values, next_nodes = await _get_session_state(diagnosis_id)
    state_report = values.get("diagnosis_report") if isinstance(values, dict) else None
    if isinstance(state_report, dict):
        wait_adoption_body = await _status_wait_adoption(diagnosis_id, state_report)
        if wait_adoption_body is not None:
            return wait_adoption_body
        running_body = await _status_while_graph_running(diagnosis_id, state_report)
        if running_body is not None:
            return running_body
        hs = state_report.get("health_score", 0)
        return _status_payload(
            diagnosis_id,
            status="completed",
            phase="completed",
            progress=100,
            message="诊断完成",
            health_score=hs if not isinstance(hs, dict) else hs.get("total_score", 0),
        )

    if next_nodes:
        if "wait_adoption" in next_nodes:
            rep_fb = None
            if isinstance(values, dict):
                dr = values.get("diagnosis_report")
                if isinstance(dr, dict):
                    rep_fb = dr
            w_fb = await _status_wait_adoption(diagnosis_id, rep_fb)
            if w_fb is not None:
                return w_fb
        if not is_running:
            err = await _extract_error_message(values if isinstance(values, dict) else {}, diagnosis_id)
            progress = 0
            msgs = values.get("progress_messages") or [] if isinstance(values, dict) else []
            if msgs:
                last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                try:
                    progress = int(float(last.get("percent", 0)))
                except (TypeError, ValueError):
                    pass
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=progress,
                message=err,
                health_score=None,
            )
        msg = "诊断执行中..."
        progress = 0
        msgs = values.get("progress_messages") or [] if isinstance(values, dict) else []
        if msgs:
            last = msgs[-1] if isinstance(msgs[-1], dict) else {}
            msg = str(last.get("content", "")) or msg
            try:
                progress = int(float(last.get("percent", 0)))
            except (TypeError, ValueError):
                pass
        phase = "diagnosis"
        if "execute_plans" in next_nodes:
            phase = "execution"
        elif "track_effects" in next_nodes:
            phase = "tracking"
        elif "wait_adoption" in next_nodes:
            phase = "adoption"
        return _status_payload(
            diagnosis_id,
            status="pending" if progress <= 0 else "running",
            phase=phase,
            progress=progress,
            message=msg,
            health_score=None,
        )

    if task is not None and task.done():
        err = await _extract_error_message(values if isinstance(values, dict) else {}, diagnosis_id)
        progress = 0
        msgs = values.get("progress_messages") or [] if isinstance(values, dict) else []
        if msgs:
            last = msgs[-1] if isinstance(msgs[-1], dict) else {}
            try:
                progress = int(float(last.get("percent", 0)))
            except (TypeError, ValueError):
                pass
        return _status_payload(
            diagnosis_id,
            status="failed",
            phase="diagnosis",
            progress=progress,
            message=err,
            health_score=None,
        )

    if succeeded_without_report:
        waited_seconds = 0
        if isinstance(succeeded_updated_at, datetime):
            waited_seconds = max(
                0,
                int((datetime.now(tz=succeeded_updated_at.tzinfo or timezone.utc) - succeeded_updated_at).total_seconds()),
            )
        if waited_seconds >= 30:
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=99,
                message="诊断任务已结束但未生成报告，请稍后重试或联系管理员检查服务日志",
                health_score=None,
            )
        return _status_payload(
            diagnosis_id,
            status="running",
            phase="diagnosis",
            progress=99,
            message="任务已完成，等待报告落库",
            health_score=None,
        )

    return _status_payload(
        diagnosis_id,
        status="not_found",
        phase="diagnosis",
        progress=0,
        message="诊断记录不存在",
        health_score=None,
    )


async def _status_while_graph_running(diagnosis_id: str, report: dict | None) -> dict | None:
    if not await is_thread_running_full(diagnosis_id):
        return None
    progress = 0
    msg = "诊断执行中..."
    cached = await progress_cache.aget(diagnosis_id)
    stage = ""
    if cached:
        msg = cached.get("message", msg)
        cached_type = str(cached.get("type") or "").strip().lower()
        stage = str(cached.get("stage") or "").strip().lower()
        progress = safe_percent(cached.get("percent", 0))
        if cached_type == "error":
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=0,
                message=str(msg or "诊断执行失败"),
                health_score=None,
            )
    else:
        try:
            values, _ = await _get_session_state(diagnosis_id)
            msg, progress = _last_progress_from_values(values)
        except Exception:
            pass
    health_score_val = None
    if report:
        hs = report.get("health_score", 0)
        health_score_val = hs if not isinstance(hs, dict) else hs.get("total_score", 0)
    phase = "diagnosis"
    if stage == "execution":
        phase = "execution"
    elif stage == "effect_track":
        phase = "tracking"
    return _status_payload(
        diagnosis_id,
        status="pending" if progress <= 0 else "running",
        phase=phase,
        progress=progress,
        message=msg,
        health_score=health_score_val,
    )


async def _status_wait_adoption(diagnosis_id: str, report: dict | None) -> dict | None:
    values, next_nodes = await _get_session_state(diagnosis_id)
    if "wait_adoption" not in next_nodes:
        return None
    msg = "方案生成完成"
    progress_msgs = values.get("progress_messages") or []
    if isinstance(progress_msgs, list):
        for item in reversed(progress_msgs):
            if not isinstance(item, dict):
                continue
            text = str(item.get("content") or "").strip()
            if not text:
                continue
            if "采集" in text and "方案" not in text:
                continue
            msg = text
            break
    if msg == "方案生成完成":
        cached = await progress_cache.aget(diagnosis_id)
        if isinstance(cached, dict):
            cached_msg = str(cached.get("message") or "").strip()
            if cached_msg and ("方案" in cached_msg or "采纳" in cached_msg):
                msg = cached_msg
    health_score_val = None
    if report:
        hs = report.get("health_score", 0)
        health_score_val = hs if not isinstance(hs, dict) else hs.get("total_score", 0)
    return _status_payload(
        diagnosis_id,
        status="completed",
        phase="diagnosis",
        progress=100,
        message=msg,
        health_score=health_score_val,
    )
