"""效果追踪与复盘报告落库 — 诊断系统本地 Postgres。"""

from __future__ import annotations

import json
import logging

from psycopg.rows import dict_row

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def save_effect_tracking(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    tracking_data: dict,
) -> None:
    """写入或覆盖该 thread_id 的效果追踪数据。"""
    data_json = json.dumps(tracking_data, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_effect_tracking (thread_id, tenant_id, store_id, tracking_data)
                    VALUES (%s, %s, %s, %s::jsonb)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        tenant_id = EXCLUDED.tenant_id,
                        store_id = EXCLUDED.store_id,
                        tracking_data = ai_effect_tracking.tracking_data || EXCLUDED.tracking_data,
                        created_at = NOW()
                    """,
                    (thread_id[:128], tenant_id[:32], store_id[:32], data_json),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("效果追踪落库失败", thread_id=thread_id) from e


async def save_review_report(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    report: dict,
) -> None:
    """写入或覆盖该 thread_id 的复盘报告。"""
    report_json = json.dumps(report, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_review_report (thread_id, tenant_id, store_id, report)
                    VALUES (%s, %s, %s, %s::jsonb)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        tenant_id = EXCLUDED.tenant_id,
                        store_id = EXCLUDED.store_id,
                        report = EXCLUDED.report,
                        created_at = NOW()
                    """,
                    (thread_id[:128], tenant_id[:32], store_id[:32], report_json),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("复盘报告落库失败", thread_id=thread_id) from e


async def review_report_exists(thread_id: str) -> bool:
    """是否已有复盘报告行（含兼容层「完成追踪」写入）。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM ai_review_report WHERE thread_id = %s LIMIT 1",
                    (thread_id[:128],),
                )
                return await cur.fetchone() is not None
    except Exception as e:
        raise AppError("查询复盘报告是否存在失败", thread_id=thread_id) from e

async def get_tracking(thread_id: str) -> dict | None:
    """按 thread_id 返回效果追踪行（dict_row），无则 None。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT thread_id, tenant_id, store_id, tracking_data, created_at "
                    "FROM ai_effect_tracking WHERE thread_id = %s",
                    (thread_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        raise AppError("查询效果追踪失败", thread_id=thread_id) from e


async def update_tracking_data(thread_id: str, tracking_data: dict) -> None:
    """覆盖更新 tracking_data JSON 字段。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                    (json.dumps(tracking_data, ensure_ascii=False), thread_id),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("更新效果追踪失败", thread_id=thread_id) from e


async def tracking_exists(thread_id: str) -> bool:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM ai_effect_tracking WHERE thread_id = %s",
                    (thread_id,),
                )
                return await cur.fetchone() is not None
    except Exception as e:
        raise AppError("查询效果追踪是否存在失败", thread_id=thread_id) from e


async def get_review_report(thread_id: str) -> dict | None:
    """按 thread_id 返回复盘报告行（dict_row），无则 None。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT thread_id, tenant_id, store_id, report, created_at "
                    "FROM ai_review_report WHERE thread_id = %s",
                    (thread_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        raise AppError("查询复盘报告失败", thread_id=thread_id) from e


async def update_review_report(thread_id: str, report: dict) -> None:
    """覆盖更新复盘报告 JSON 字段。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_review_report SET report = %s WHERE thread_id = %s",
                    (json.dumps(report, ensure_ascii=False), thread_id),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("更新复盘报告失败", thread_id=thread_id) from e
