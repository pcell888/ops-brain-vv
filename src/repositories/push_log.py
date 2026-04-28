"""推送记录落库 — 诊断系统本地 Postgres，留存消息/任务推送。"""

from __future__ import annotations

import json
import logging

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


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
    extra_json = json.dumps(extra or {}, ensure_ascii=False)
    # 同时写入日志文件，确保推送内容可查
    logger.info(
        "[PUSH_LOG] thread=%s tenant=%s store=%s kind=%s type=%s title=%s content=%s extra=%s",
        thread_id, tenant_id, store_id, kind, message_type, title, content, extra_json,
    )
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO push_logs (thread_id, tenant_id, store_id, kind, message_type, title, content, extra)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (thread_id, tenant_id, store_id, kind, message_type or "", (title or "")[:500], (content or "")[:10000], extra_json),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("推送记录落库失败", thread_id=thread_id, tenant_id=tenant_id, store_id=store_id) from e
