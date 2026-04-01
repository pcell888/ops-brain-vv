"""效果追踪与复盘报告落库 — 诊断系统本地 Postgres。"""

from __future__ import annotations

import json
import logging

import psycopg

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_effect_tracking, ensure_ai_review_report

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


async def save_effect_tracking(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    tracking_data: dict,
) -> None:
    """写入或覆盖该 thread_id 的效果追踪数据。"""
    await ensure_ai_effect_tracking()
    data_json = json.dumps(tracking_data, ensure_ascii=False)
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
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
        logger.warning("效果追踪落库失败: %s", e)


async def save_review_report(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    report: dict,
) -> None:
    """写入或覆盖该 thread_id 的复盘报告。"""
    await ensure_ai_review_report()
    report_json = json.dumps(report, ensure_ascii=False)
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
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
        logger.warning("复盘报告落库失败: %s", e)


async def review_report_exists(thread_id: str) -> bool:
    """是否已有复盘报告行（含兼容层「完成追踪」写入）。"""
    await ensure_ai_review_report()
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM ai_review_report WHERE thread_id = %s LIMIT 1",
                    (thread_id[:128],),
                )
                return await cur.fetchone() is not None
    except Exception as e:
        logger.warning("查询复盘报告是否存在失败: %s", e)
        return False
