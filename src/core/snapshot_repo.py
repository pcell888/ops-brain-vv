"""效果追踪指标快照管理 — 追踪期间定期采集并落库。"""

from __future__ import annotations

import json
import logging

import psycopg.rows

from src.core.db_init import ensure_ai_effect_snapshot
from src.core.db_pool import get_conn

logger = logging.getLogger(__name__)


async def save_snapshot(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    snapshot_data: dict,
) -> None:
    await ensure_ai_effect_snapshot()
    data_json = json.dumps(snapshot_data, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_effect_snapshot (thread_id, tenant_id, store_id, snapshot_data)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (thread_id[:128], tenant_id[:32], store_id[:32], data_json),
                )
            await conn.commit()
    except Exception as e:
        logger.warning("快照保存失败 [%s]: %s", thread_id, e)


async def list_snapshots(thread_id: str) -> list[dict]:
    """按时间正序返回该 thread 的所有快照。"""
    await ensure_ai_effect_snapshot()
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT snapshot_data, snapshot_at
                    FROM ai_effect_snapshot
                    WHERE thread_id = %s
                    ORDER BY snapshot_at ASC
                    """,
                    (thread_id,),
                )
                rows = await cur.fetchall()
                for r in rows:
                    if hasattr(r.get("snapshot_at"), "isoformat"):
                        r["snapshot_at"] = r["snapshot_at"].isoformat()
                return rows
    except Exception as e:
        logger.warning("查询快照失败 [%s]: %s", thread_id, e)
        return []


async def get_last_snapshot_time(thread_id: str):
    """返回该 thread 最后一次快照的时间（datetime 或 None）。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT MAX(snapshot_at) FROM ai_effect_snapshot WHERE thread_id = %s",
                    (thread_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.warning("查询最后快照时间失败 [%s]: %s", thread_id, e)
        return None


async def get_snapshot_by_id(snapshot_id: int) -> dict | None:
    """按主键 ID 查询单条快照。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT id, thread_id, snapshot_data, snapshot_at FROM ai_effect_snapshot WHERE id = %s",
                    (snapshot_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        logger.warning("查询快照失败 [id=%s]: %s", snapshot_id, e)
        return None


async def list_snapshots_with_id(thread_id: str) -> list[dict]:
    """按时间正序返回该 thread 的所有快照（含 id 字段，供兼容层快照列表）。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT id, snapshot_data, snapshot_at FROM ai_effect_snapshot WHERE thread_id = %s ORDER BY snapshot_at ASC",
                    (thread_id,),
                )
                return await cur.fetchall()
    except Exception as e:
        logger.warning("查询快照列表失败 [%s]: %s", thread_id, e)
        return []


async def get_latest_snapshot(thread_id: str) -> dict | None:
    """返回该 thread 最近一条快照（dict_row 含 id, snapshot_data）。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT id, snapshot_data FROM ai_effect_snapshot WHERE thread_id = %s ORDER BY snapshot_at DESC LIMIT 1",
                    (thread_id,),
                )
                return await cur.fetchone()
    except Exception as e:
        logger.warning("查询最新快照失败 [%s]: %s", thread_id, e)
        return None
