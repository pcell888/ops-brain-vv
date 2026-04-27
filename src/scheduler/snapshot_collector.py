"""效果追踪指标快照落库（定时由 weekly_diagnosis 注册）。

目标 thread：待复盘 pending，以及「已建 effect_trackings 且仍为 active 的 diag_*」（首次快照会 cancel 待复盘但仍需周期采集）。
调度：每日 effect_snapshot_hour 整点跑一轮；同 thread 按 effect_snapshot_interval_days（天，可小数）做时间间隔节流；0 表示不限制。
复盘节点 track_effects 仍会实时拉指标。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from src.repositories.diagnosis_session import get_session as get_diagnosis_session
from src.repositories.tracking import get_tracking
from src.core.config import CN_TZ, get_settings
from src.core.calculator import resolve_active_indicators
from src.repositories.snapshot import save_snapshot, get_last_snapshot_time
from src.services.tracking_snapshot import _build_effect_tracking_snapshot

logger = logging.getLogger(__name__)

# IntervalTrigger 与 max_instances 配合：上一轮若仍在采集指标，新触发可进入本协程并立即返回，避免被调度器整段丢弃。
_snapshot_collect_lock = asyncio.Lock()
_snapshot_collect_busy = False


async def _get_pending_threads() -> list[dict]:
    """获取所有处于追踪等待状态的 pending review 记录（含到期日）。"""
    from src.core.db_pool import get_conn
    import psycopg.rows

    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT thread_id, tenant_id, store_id, review_due_date FROM pending_reviews WHERE status = 'pending'"
                )
                return await cur.fetchall()
    except Exception as e:
        logger.warning("查询待追踪记录失败: %s", e)
        return []


async def _get_active_diag_tracking_threads(exclude_thread_ids: set[str]) -> list[dict]:
    """采纳后若用户曾走「首次快照」接口，会 cancel 掉 pending_reviews，但 effect_trackings 仍为 active。

    此类诊断仍应用 LangGraph checkpoint 做周期快照，故在此补全目标列表（仅 diag_ 前缀，与 checkpoint thread_id 一致）。
    """
    from src.core.db_pool import get_conn
    import psycopg.rows

    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT t.thread_id, t.tenant_id, t.store_id, NULL::timestamptz AS review_due_date
                    FROM effect_trackings t
                    WHERE LEFT(t.thread_id, 5) = 'diag_'
                      AND (
                        t.tracking_data->>'status' IS NULL
                        OR TRIM(COALESCE(t.tracking_data->>'status', '')) IN ('', 'active')
                      )
                    """
                )
                rows = await cur.fetchall()
        return [r for r in rows if str(r.get("thread_id") or "") not in exclude_thread_ids]
    except Exception as e:
        logger.warning("查询 active 效果追踪(diag)失败: %s", e)
        return []


async def _get_snapshot_target_threads() -> list[dict]:
    pending = await _get_pending_threads()
    seen = {str(r.get("thread_id") or "") for r in pending}
    extra = await _get_active_diag_tracking_threads(seen)
    return pending + extra


def _to_cn(dt: datetime) -> datetime:
    if dt.tzinfo:
        return dt.astimezone(CN_TZ)
    return dt.replace(tzinfo=CN_TZ)


async def _collect_snapshot_for_thread(thread: dict) -> None:
    thread_id = thread["thread_id"]
    diagnosis_id = thread_id  # 与 LangGraph / 前端「诊断 ID」一致
    tenant_id = thread["tenant_id"]
    store_id = thread["store_id"]

    settings = get_settings()
    interval_days = float(settings.effect_snapshot_interval_days or 0.0)

    now_cn = datetime.now(CN_TZ)
    last_raw = await get_last_snapshot_time(thread_id)
    if last_raw is not None and isinstance(last_raw, datetime):
        last_cn = _to_cn(last_raw)
        if interval_days > 0:
            gap_required = timedelta(days=interval_days)
            if now_cn - last_cn < gap_required:
                logger.info(
                    "快照跳过 diagnosis_id=%s: 距上次快照不足 %s 天 (last=%s)",
                    diagnosis_id,
                    interval_days,
                    last_cn.isoformat(),
                )
                return

    # 不在此用 review_due_date 拦截：execute 写入的到期日常为「任务 deadline 当日 00:00」，
    # 当天午后会误判为已到期，导致整日无法自动快照。是否仍应采集由 status=pending 界定。

    app = await get_diagnosis_session(thread_id)
    if not app:
        logger.info(
            "快照跳过 diagnosis_id=%s: 无诊断会话记录",
            diagnosis_id,
        )
        return

    state_values = app.get("state_json")
    if isinstance(state_values, str):
        try:
            state_values = json.loads(state_values)
        except (json.JSONDecodeError, TypeError):
            state_values = {}
    if not isinstance(state_values, dict):
        state_values = {}

    tracking_data: dict = {}
    row = await get_tracking(thread_id)
    if row and row.get("tracking_data") is not None:
        raw_td = row["tracking_data"]
        if isinstance(raw_td, str):
            tracking_data = json.loads(raw_td) if raw_td.strip() else {}
        elif isinstance(raw_td, dict):
            tracking_data = dict(raw_td)
    if state_values.get("selected_dimensions") is not None:
        tracking_data["selected_dimensions"] = state_values.get("selected_dimensions")
    if state_values.get("selected_indicators") is not None:
        tracking_data["selected_indicators"] = state_values.get("selected_indicators")

    active_dims, _ = resolve_active_indicators(
        tracking_data.get("selected_dimensions"),
        tracking_data.get("selected_indicators"),
    )
    if not active_dims:
        logger.info(
            "快照跳过 diagnosis_id=%s: 无可用指标维度 (active_dims=%s selected_dimensions=%s)",
            diagnosis_id,
            sorted(active_dims),
            tracking_data.get("selected_dimensions"),
        )
        return

    auth_raw = state_values.get("auth_token")
    auth_token = str(auth_raw).strip() if auth_raw else None
    if not auth_token:
        logger.warning(
            "快照 diagnosis_id=%s: checkpoint 无 auth_token，企服指标可能为空（与手动带 Token 不一致）",
            diagnosis_id,
        )

    try:
        logger.info(
            "快照拉取指标 diagnosis_id=%s tenant_id=%s store_id=%s has_auth_token=%s",
            diagnosis_id,
            tenant_id,
            store_id or "",
            bool(auth_token),
        )
        snapshot_payload = await _build_effect_tracking_snapshot(
            tenant_id,
            store_id or "",
            tracking_data,
            snapshot_at=now_cn,
            auth_token=auth_token,
        )
        await save_snapshot(thread_id, tenant_id, store_id, snapshot_payload)
        logger.info("快照采集完成 diagnosis_id=%s", diagnosis_id)
    except Exception as e:
        logger.error("快照采集失败 diagnosis_id=%s, error=%s", diagnosis_id, e)


async def collect_effect_snapshots():
    """入口：扫描所有追踪中的 thread，按调度与节流规则采集快照。"""
    global _snapshot_collect_busy
    async with _snapshot_collect_lock:
        if _snapshot_collect_busy:
            logger.debug("效果追踪快照采集跳过：上一轮仍在执行")
            return
        _snapshot_collect_busy = True
    try:
        logger.info("===== 开始效果追踪快照采集 =====")
        threads = await _get_snapshot_target_threads()
        if not threads:
            logger.info("无追踪中的诊断会话（待复盘 + active diag 效果追踪）")
            return

        logger.info("共 %d 个追踪中的诊断会话（待复盘 + active diag 效果追踪）", len(threads))
        for thread in threads:
            try:
                await _collect_snapshot_for_thread(thread)
            except Exception as e:
                logger.error(
                    "快照采集异常 diagnosis_id=%s, error=%s",
                    thread.get("thread_id"),
                    e,
                )

        logger.info("===== 效果追踪快照采集完成 =====")
    finally:
        async with _snapshot_collect_lock:
            _snapshot_collect_busy = False
