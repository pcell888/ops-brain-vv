"""诊断报告落库 — 诊断系统内部 Postgres。"""

from __future__ import annotations

import json
import logging

from psycopg.rows import dict_row

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def save_report(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
    report: dict,
    *,
    plan_ids: list[str] | None = None,
) -> None:
    """写入或覆盖该 thread_id 的诊断报告。落库前确保表存在。"""
    report_json = json.dumps(report, ensure_ascii=False)
    plan_ids_json = json.dumps(plan_ids or [], ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO diag_reports (thread_id, tenant_id, store_id, trigger_type, report, plan_ids)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        tenant_id = EXCLUDED.tenant_id,
                        store_id = EXCLUDED.store_id,
                        trigger_type = EXCLUDED.trigger_type,
                        report = EXCLUDED.report,
                        plan_ids = EXCLUDED.plan_ids,
                        created_at = NOW()
                    """,
                    (thread_id, tenant_id, store_id, trigger_type, report_json, plan_ids_json),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("保存诊断报告失败", thread_id=thread_id, tenant_id=tenant_id, store_id=store_id) from e


async def get_report(thread_id: str) -> dict | None:
    """按 thread_id 查询报告。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT tenant_id, store_id, report FROM diag_reports WHERE thread_id = %s",
                    (thread_id,),
                )
                row = await cur.fetchone()
                if row and row.get("report"):
                    report = row["report"] if isinstance(row["report"], dict) else dict(row["report"])
                    return report
                return None
    except Exception as e:
        raise AppError("查询诊断报告失败", thread_id=thread_id) from e


async def list_reports(
    tenant_id: str | None,
    store_id: str | None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页列表，按创建时间倒序。返回 (items, total)。"""
    try:
        async with get_conn() as conn:
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
                    f"SELECT COUNT(*) AS c FROM diag_reports WHERE {where_sql}",
                    params,
                )
                total = (await cur.fetchone()).get("c", 0)

                params.extend([page_size, (page - 1) * page_size])
                await cur.execute(
                    f"""
                    SELECT thread_id, tenant_id, store_id, trigger_type, created_at
                    FROM diag_reports WHERE {where_sql}
                    ORDER BY created_at DESC LIMIT %s OFFSET %s
                    """,
                    params,
                )
                rows = await cur.fetchall()
                items = [dict(r) for r in rows]
                return items, total
    except Exception as e:
        raise AppError("列表诊断报告失败", tenant_id=tenant_id, store_id=store_id, page=page) from e


async def update_plan_ids(thread_id: str, plan_ids: list[str]) -> None:
    """更新指定诊断报告的 plan_ids 列表。"""
    plan_ids_json = json.dumps(plan_ids, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE diag_reports
                    SET plan_ids = %s::jsonb
                    WHERE thread_id = %s
                    """,
                    (plan_ids_json, thread_id),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("更新 plan_ids 失败", thread_id=thread_id) from e


async def find_all_thread_ids_by_plan_id(plan_id: str) -> list[str]:
    """通过 plan_id 查找所有对应的 thread_id，按创建时间倒序。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT thread_id
                    FROM diag_reports
                    WHERE plan_ids @> %s::jsonb
                    ORDER BY created_at DESC
                    """,
                    (json.dumps([plan_id]),),
                )
                rows = await cur.fetchall()
                return [r["thread_id"] for r in rows if r.get("thread_id")]
    except Exception as e:
        raise AppError("通过 plan_id 查找 thread_id 失败", plan_id=plan_id) from e
