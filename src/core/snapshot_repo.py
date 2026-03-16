"""效果追踪指标快照管理 — 追踪期间定期采集并落库。"""

from __future__ import annotations

import json
import logging

import psycopg

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_effect_snapshot

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


async def save_snapshot(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    snapshot_data: dict,
) -> None:
    await ensure_ai_effect_snapshot()
    data_json = json.dumps(snapshot_data, ensure_ascii=False)
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
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
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
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
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
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
