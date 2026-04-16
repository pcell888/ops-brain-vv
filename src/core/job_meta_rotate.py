"""更新 ai_async_job_meta 的 job_id（仅依赖 db_pool，供 arq_queue 使用以避免循环导入）。"""

from __future__ import annotations

import json

from src.core.db_pool import get_conn


async def rotate_async_job_id_in_meta(*, old_job_id: str, new_job_id: str, thread_id: str) -> None:
    """arq 因旧 job_id 在 Redis 中仍存在而拒绝入队时，更新 PG 中的 job_id 与 payload.job_id。"""
    payload_patch = json.dumps({"job_id": new_job_id}, ensure_ascii=False)
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE ai_async_job_meta
                   SET job_id = %s,
                       payload = payload || %s::jsonb,
                       updated_at = NOW()
                 WHERE job_id = %s AND thread_id = %s
                """,
                (new_job_id, payload_patch, old_job_id, thread_id),
            )
        await conn.commit()
