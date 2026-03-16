"""推送记录落库 — 诊断系统本地 Postgres，留存消息/任务推送。"""

from __future__ import annotations

import json
import logging

import psycopg

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_push_log

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


async def save_push_log(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    kind: str,
    message_type: str = "",
    title: str = "",
    content: str = "",
    extra: dict | None = None,
) -> None:
    """写入一条推送记录。kind: message | task。"""
    await ensure_ai_push_log()
    extra_json = json.dumps(extra or {}, ensure_ascii=False)
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_push_log (thread_id, tenant_id, store_id, kind, message_type, title, content, extra)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (thread_id, tenant_id, store_id, kind, message_type or "", (title or "")[:500], (content or "")[:10000], extra_json),
                )
            await conn.commit()
    except Exception as e:
        logger.warning("推送记录落库失败: %s", e)
