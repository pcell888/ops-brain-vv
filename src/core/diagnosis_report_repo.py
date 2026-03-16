"""诊断报告落库 — 诊断系统内部 Postgres。"""

from __future__ import annotations

import json
import logging

import psycopg
from psycopg.rows import dict_row

from src.core.config import get_settings
from src.core.db_init import _uri_to_conninfo, ensure_ai_diagnosis_report

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return _uri_to_conninfo(get_settings().postgres_uri)


async def save_report(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    report: dict,
) -> None:
    """写入或覆盖该 thread_id 的诊断报告。落库前确保表存在。"""
    await ensure_ai_diagnosis_report()
    report_json = json.dumps(report, ensure_ascii=False)
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_diagnosis_report (thread_id, tenant_id, store_id, trigger_type, report)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        tenant_id = EXCLUDED.tenant_id,
                        store_id = EXCLUDED.store_id,
                        trigger_type = EXCLUDED.trigger_type,
                        report = EXCLUDED.report,
                        created_at = NOW()
                    """,
                    (thread_id, tenant_id, store_id, trigger_type, report_json),
                )
            await conn.commit()
    except Exception as e:
        logger.warning("诊断报告落库失败: %s", e)
        raise


async def get_report(thread_id: str) -> dict | None:
    """按 thread_id 查询报告。"""
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT report FROM ai_diagnosis_report WHERE thread_id = %s",
                    (thread_id,),
                )
                row = await cur.fetchone()
                if row and row.get("report"):
                    return row["report"] if isinstance(row["report"], dict) else dict(row["report"])
                return None
    except Exception as e:
        logger.warning("查询诊断报告失败: %s", e)
        return None


async def list_reports(
    tenant_id: str | None,
    store_id: str | None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页列表，按创建时间倒序。返回 (items, total)。"""
    try:
        async with await psycopg.AsyncConnection.connect(_conninfo()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where, params = [], []
                if tenant_id:
                    where.append("tenant_id = %s")
                    params.append(tenant_id)
                if store_id:
                    where.append("store_id = %s")
                    params.append(store_id)
                where_sql = " AND ".join(where) if where else "1=1"

                await cur.execute(
                    f"SELECT COUNT(*) AS c FROM ai_diagnosis_report WHERE {where_sql}",
                    params,
                )
                total = (await cur.fetchone()).get("c", 0)

                params.extend([page_size, (page - 1) * page_size])
                await cur.execute(
                    f"""
                    SELECT thread_id, tenant_id, store_id, trigger_type, created_at
                    FROM ai_diagnosis_report WHERE {where_sql}
                    ORDER BY created_at DESC LIMIT %s OFFSET %s
                    """,
                    params,
                )
                rows = await cur.fetchall()
                items = [dict(r) for r in rows]
                return items, total
    except Exception as e:
        logger.warning("列表诊断报告失败: %s", e)
        return [], 0
