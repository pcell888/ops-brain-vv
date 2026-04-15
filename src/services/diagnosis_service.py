"""诊断业务逻辑服务层。

封装诊断相关的核心业务逻辑，供 API 路由层调用。
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from src.core.diagnosis_report_repo import list_reports, get_report as get_report_from_db
from src.core.calculator import (
    INDICATOR_META,
    DEFAULT_BENCHMARKS,
    DEFAULT_DIMENSION_WEIGHTS,
    ALL_DIMENSIONS,
    calculate_dimension_benchmarks_scores,
)
from src.runtime.graph_app import get_graph_app
from src.runtime.progress_store import progress_cache
from src.runtime.running_tasks import running_tasks
from src.runtime.thread_enterprise import get_running_threads_for_enterprise
from src.core.config import CN_TZ
from src.core.async_job_meta_repo import (
    JOB_STATUS_CANCELLED,
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    get_latest_job_by_thread,
)

logger = logging.getLogger(__name__)


# ── 辅助函数 ──────────────────────────────────────────────────


def _score_to_status(score: float) -> str:
    """将分数转换为状态标签。"""
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "warning"
    return "danger"


def _map_severity(sev: str) -> str:
    """映射严重程度。"""
    return {"high": "critical", "medium": "high", "low": "medium"}.get(sev, sev)


def _normalize_recommendations(val: object) -> list[str]:
    """规范化建议列表。"""
    if val is None:
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, list):
        return [x.strip() for x in val if isinstance(x, str) and x.strip()]
    return []


def _list_item_cn_time(raw: object) -> tuple[str, str | None]:
    """列表项创建时间统一为中国时区。"""
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


async def _extract_error_message(values: dict, diagnosis_id: str) -> str:
    """从状态值/缓存中提取失败消息。"""
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
    """提取总分。"""
    raw_health_score = raw.get("health_score", 0)
    if isinstance(raw_health_score, dict):
        return float(raw_health_score.get("total_score", 0))
    return float(raw_health_score)


# 保留旧名称以兼容现有代码
_extract_total_score = extract_total_score


def _empty_health_trend() -> dict:
    """空的健康趋势。"""
    return {"previous_score": None, "change": None, "direction": None}


_PHASE_NAME = {
    "diagnosis": "诊断",
    "adoption": "采纳",
    "execution": "执行",
    "tracking": "追踪",
    "completed": "已完成",
}

_PHASE_OVERALL_RANGE = {
    "diagnosis": (0, 60),
    "adoption": (60, 75),
    "execution": (75, 90),
    "tracking": (90, 99),
    "completed": (100, 100),
}


def _calc_overall_progress(phase: str, phase_progress: int) -> int:
    p = max(0, min(100, int(phase_progress)))
    lo, hi = _PHASE_OVERALL_RANGE.get(phase, (0, 100))
    if lo == hi:
        return lo
    return int(round(lo + (hi - lo) * (p / 100.0)))


def _infer_next_phase(phase: str, status: str) -> str | None:
    """业务流程下一里程碑阶段（与 phase 同枚举）；失败/不存在/已全流程结束为 None。"""
    if status in ("failed", "not_found"):
        return None
    if phase == "completed":
        return None
    if phase == "diagnosis":
        return "adoption"
    if phase == "adoption":
        return "execution"
    if phase == "execution":
        return "tracking"
    if phase == "tracking":
        return "completed"
    return None


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
    overall = _calc_overall_progress(phase, phase_progress)
    return {
        "diagnosis_id": diagnosis_id,
        "status": status,
        "phase": phase,
        "phase_name": _PHASE_NAME.get(phase, phase),
        "progress": phase_progress,  # 阶段内进度（兼容字段）
        "overall_progress": overall,  # 全流程总进度
        "next_phase": _infer_next_phase(phase, status),
        "message": message,
        "health_score": health_score,
    }

# ── 核心业务逻辑 ──────────────────────────────────────────────


async def get_diagnosis_list_items(
    tenant_id: str | None,
    skip: int,
    limit: int,
    store_id: str | None = None,
    include_running: bool = True,
) -> tuple[list[dict], int]:
    """获取诊断列表（内部格式）。
    
    Args:
        tenant_id: 租户ID
        skip: 跳过记录数
        limit: 返回记录数
        store_id: 门店ID（可选）
        include_running: 是否包含运行中但未入库的任务
        
    Returns:
        (items, total) - 诊断列表项和总数
    """
    page = skip // limit + 1 if limit else 1
    items, total = await list_reports(tenant_id, store_id, page, limit)

    # 格式化时间字段
    for row in items:
        if "created_at" in row and hasattr(row["created_at"], "isoformat"):
            row["created_at"] = row["created_at"].isoformat()

    db_thread_ids = {row.get("thread_id", "") for row in items}

    # 找出正在运行但尚未入库的任务
    running_not_in_db: list[dict] = []
    if include_running and tenant_id and skip == 0:
        running_thread_ids = await get_running_threads_for_enterprise(tenant_id)
        for tid in running_thread_ids:
            task = running_tasks.get(tid)
            is_running = (task is not None and not task.done()) or await running_tasks.is_running(tid)
            if is_running and tid not in db_thread_ids:
                item = await _build_running_item(tid)
                if item:
                    running_not_in_db.append(item)

    result_items = []
    result_items.extend(running_not_in_db)

    for row in items:
        thread_id = row.get("thread_id", "")
        item = await _build_list_item_from_row(thread_id, row)
        result_items.append(item)

    adjusted_total = total + len(running_not_in_db)
    return result_items, adjusted_total


async def _build_running_item(thread_id: str) -> dict | None:
    """为尚未入库但正在运行的任务构建列表项。"""
    status = "running"
    progress = 0
    message = "诊断执行中..."

    try:
        app = await get_graph_app()
        config = {"configurable": {"thread_id": thread_id}}
        state = await app.aget_state(config)
        values = state.values if state and state.values else {}
        msgs = values.get("progress_messages") or []
        if msgs:
            last = msgs[-1] if isinstance(msgs[-1], dict) else {}
            message = str(last.get("content", "")) or message
            try:
                progress = int(float(last.get("percent", 0)))
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    _now = datetime.now(CN_TZ)
    return {
        "diagnosis_id": thread_id,
        "name": _now.strftime("诊断 %Y-%m-%d %H:%M"),
        "status": status,
        "progress": progress,
        "message": message,
        "error_message": None,
        "health_score": None,
        "anomaly_count": None,
        "report_ready": False,
        "trigger_type": "manual",
        "created_at": _now.isoformat(),
    }


async def _build_list_item_from_row(thread_id: str, row: dict) -> dict:
    """从数据库行构建列表项。"""
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
        # 报告在 diagnose 节点已落库，但 LangGraph 任务可能仍在执行
        task = running_tasks.get(thread_id)
        is_running = (task is not None and not task.done()) or await running_tasks.is_running(thread_id)
        if is_running:
            status = "running"
            progress = 0
            message = "诊断执行中..."
            try:
                app = await get_graph_app()
                config = {"configurable": {"thread_id": thread_id}}
                state = await app.aget_state(config)
                values = state.values if state and state.values else {}
                msgs = values.get("progress_messages") or []
                if msgs:
                    last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                    message = str(last.get("content", "")) or message
                    try:
                        progress = int(float(last.get("percent", 0)))
                    except (TypeError, ValueError):
                        pass
            except Exception:
                pass
    else:
        task = running_tasks.get(thread_id)
        is_task_running = (task is not None and not task.done()) or await running_tasks.is_running(thread_id)

        app = await get_graph_app()
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = await app.aget_state(config)
            values = state.values if state and state.values else {}
            if values.get("diagnosis_report"):
                report = values["diagnosis_report"]
                report_ready = True
                health_score_val = report.get("health_score")
                anomaly_count = len(report.get("anomalies") or [])
            elif is_task_running:
                status = "running"
                msgs = values.get("progress_messages") or []
                if msgs:
                    last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                    message = str(last.get("content", ""))
                    try:
                        progress = int(float(last.get("percent", 0)))
                    except (TypeError, ValueError):
                        pass
                else:
                    message = "诊断执行中..."
                    progress = 0
            elif state.next:
                status = "failed"
                error_message = await _extract_error_message(values, thread_id)
                message = error_message
            else:
                status = "failed"
                error_message = await _extract_error_message(values, thread_id)
                message = error_message
        except Exception:
            if is_task_running:
                status = "running"
                progress = 0
                message = "诊断执行中..."
            else:
                status = "failed"
                error_message = "无法获取诊断状态"

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
    """获取诊断报告数据（内部格式）。
    
    Args:
        diagnosis_id: 诊断ID (thread_id)
        
    Returns:
        报告数据字典，如果不存在返回 None
    """
    report = await get_report_from_db(diagnosis_id)
    if report is None:
        app = await get_graph_app()
        config = {"configurable": {"thread_id": diagnosis_id}}
        state = await app.aget_state(config)
        if state and state.values:
            report = state.values.get("diagnosis_report")
    return report


async def compute_health_trend(
    diagnosis_id: str,
    tenant_id: str | None,
    current_total_score: float,
) -> dict:
    """对比同租户按时间倒序的上一份已落库报告，计算综合健康度变化。"""
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
    """将后端原始 report dict 转换为前端格式。
    
    这是兼容层使用的转换函数，将内部报告格式转换为前端期望的格式。
    """
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
        "root_cause_llm_usage": raw.get("root_cause_llm_usage"),
        "llm_usage_summary": raw.get("llm_usage_summary"),
    }


def calculate_benchmark_dimension_scores(industry: str = "general") -> dict:
    """计算行业基准维度得分。
    
    Args:
        industry: 行业类型（目前未使用，预留扩展）
        
    Returns:
        包含行业和维度得分的字典
    """
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
    """获取诊断状态（内部格式）。
    
    Args:
        diagnosis_id: 诊断ID (thread_id)
        
    Returns:
        状态字典，包含 status, progress, message, health_score 等
    """
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
    is_running = (task is not None and not task.done()) or await running_tasks.is_running(diagnosis_id)
    latest_job = await get_latest_job_by_thread(diagnosis_id)
    if is_running:
        # 图已停在 wait_adoption 时，诊断 Worker 可能尚未 unregister，避免一直显示 running
        try:
            app_early = await get_graph_app()
            cfg_early = {"configurable": {"thread_id": diagnosis_id}}
            st_early = await app_early.aget_state(cfg_early)
            nn_early = list(st_early.next) if st_early and st_early.next else []
            if "wait_adoption" in nn_early:
                rep_early = report
                if not rep_early and st_early.values:
                    dr = st_early.values.get("diagnosis_report")
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
                return _status_payload(
                    diagnosis_id,
                    status="failed",
                    phase="diagnosis",
                    progress=0,
                    message=job_error or ("诊断已取消" if job_status == JOB_STATUS_CANCELLED else "诊断执行失败"),
                    health_score=None,
                )
        progress = 0
        msg = "诊断执行中..."
        cached = await progress_cache.aget(diagnosis_id)
        if cached:
            msg = cached.get("message", msg)
            try:
                progress = int(float(cached.get("percent", 0) or 0))
            except (TypeError, ValueError):
                pass
        else:
            try:
                app = await get_graph_app()
                config = {"configurable": {"thread_id": diagnosis_id}}
                state = await app.aget_state(config)
                values = state.values if state and state.values else {}
                msgs = values.get("progress_messages") or []
                if msgs:
                    last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                    msg = str(last.get("content", "")) or msg
                    try:
                        progress = int(float(last.get("percent", 0)))
                    except (TypeError, ValueError):
                        pass
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
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=0,
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

    app = await get_graph_app()
    config = {"configurable": {"thread_id": diagnosis_id}}
    try:
        state = await app.aget_state(config)
    except Exception:
        state = None

    values = state.values if state and state.values else {}
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

    if state and state.next:
        next_nodes_fb = list(state.next)
        if "wait_adoption" in next_nodes_fb:
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
            return _status_payload(
                diagnosis_id,
                status="failed",
                phase="diagnosis",
                progress=0,
                message=err,
                health_score=None,
            )
        msgs = values.get("progress_messages") or [] if isinstance(values, dict) else []
        msg = "诊断执行中..."
        progress = 0
        if msgs:
            last = msgs[-1] if isinstance(msgs[-1], dict) else {}
            msg = str(last.get("content", "")) or msg
            try:
                progress = int(float(last.get("percent", 0)))
            except (TypeError, ValueError):
                pass
        phase = "diagnosis"
        next_nodes = list(state.next) if state and state.next else []
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
        return _status_payload(
            diagnosis_id,
            status="failed",
            phase="diagnosis",
            progress=0,
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
                progress=0,
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

    # 不存在
    return _status_payload(
        diagnosis_id,
        status="not_found",
        phase="diagnosis",
        progress=0,
        message="诊断记录不存在",
        health_score=None,
    )


async def _status_while_graph_running(diagnosis_id: str, report: dict | None) -> dict | None:
    """报告已落库或仅在 state 中，但 LangGraph 任务仍在跑时，返回 running + 实时进度。"""
    task = running_tasks.get(diagnosis_id)
    is_running = (task is not None and not task.done()) or await running_tasks.is_running(diagnosis_id)
    if not is_running:
        return None
    progress = 0
    msg = "诊断执行中..."
    cached = await progress_cache.aget(diagnosis_id)
    stage = ""
    if cached:
        msg = cached.get("message", msg)
        stage = str(cached.get("stage") or "").strip().lower()
        try:
            progress = int(float(cached.get("percent", 0) or 0))
        except (TypeError, ValueError):
            pass
    else:
        try:
            app = await get_graph_app()
            config = {"configurable": {"thread_id": diagnosis_id}}
            state = await app.aget_state(config)
            values = state.values if state and state.values else {}
            msgs = values.get("progress_messages") or []
            if msgs:
                last = msgs[-1] if isinstance(msgs[-1], dict) else {}
                msg = str(last.get("content", "")) or msg
                try:
                    progress = int(float(last.get("percent", 0)))
                except (TypeError, ValueError):
                    pass
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
    """图已暂停在 wait_adoption：诊断阶段（采集/分析/方案生成）已结束，返回阶段完成态。"""
    app = await get_graph_app()
    config = {"configurable": {"thread_id": diagnosis_id}}
    try:
        state = await app.aget_state(config)
    except Exception:
        return None
    next_nodes = list(state.next) if state and state.next else []
    if "wait_adoption" not in next_nodes:
        return None
    msg = "方案生成完成"
    values = state.values if state and state.values else {}
    progress_msgs = values.get("progress_messages") or []
    if isinstance(progress_msgs, list):
        for item in reversed(progress_msgs):
            if not isinstance(item, dict):
                continue
            text = str(item.get("content") or "").strip()
            if not text:
                continue
            # 进入待采纳后不再展示采集阶段旧文案。
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
