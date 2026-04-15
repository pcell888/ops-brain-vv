"""compat_tracking 数据访问层。"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from psycopg.rows import dict_row

from src.core.db_pool import get_conn

logger = logging.getLogger(__name__)


async def create_tracking(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    tracking_data: dict,
    created_at: datetime,
) -> None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ai_effect_tracking (thread_id, tenant_id, store_id, tracking_data, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (thread_id, tenant_id, store_id, json.dumps(tracking_data, ensure_ascii=False), created_at),
            )
        await conn.commit()


async def get_tracking(thread_id: str) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT thread_id, tenant_id, store_id, tracking_data, created_at FROM ai_effect_tracking WHERE thread_id = %s",
                (thread_id,),
            )
            return await cur.fetchone()


async def tracking_exists(thread_id: str) -> bool:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM ai_effect_tracking WHERE thread_id = %s", (thread_id,))
            return await cur.fetchone() is not None


async def update_tracking_data(thread_id: str, tracking_data: dict) -> None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE ai_effect_tracking SET tracking_data = %s WHERE thread_id = %s",
                (json.dumps(tracking_data, ensure_ascii=False), thread_id),
            )
        await conn.commit()


async def count_trackings(enterprise_id: str | None, diagnosis_id: str | None) -> int:
    where_parts: list[str] = []
    params: list = []
    if enterprise_id:
        where_parts.append("t.tenant_id = %s")
        params.append(enterprise_id)
    if diagnosis_id:
        where_parts.append(
            """(
            t.thread_id = %s
            OR EXISTS (
                SELECT 1 FROM ai_exec_task e
                WHERE (t.tracking_data->>'plan_id') IS NOT NULL
                  AND (t.tracking_data->>'plan_id') <> ''
                  AND e.plan_id = (t.tracking_data->>'plan_id')
                  AND e.thread_id = %s
                  AND e.tenant_id = t.tenant_id
            )
        )"""
        )
        params.append(diagnosis_id)
        params.append(diagnosis_id)
    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(f"SELECT COUNT(*) FROM ai_effect_tracking t {where_sql}", params)
            row = await cur.fetchone()
            return int((row or {}).get("count", 0))


async def list_trackings(
    enterprise_id: str | None,
    diagnosis_id: str | None,
    skip: int,
    limit: int,
) -> list[dict]:
    where_parts: list[str] = []
    params: list = []
    if enterprise_id:
        where_parts.append("t.tenant_id = %s")
        params.append(enterprise_id)
    if diagnosis_id:
        where_parts.append(
            """(
            t.thread_id = %s
            OR EXISTS (
                SELECT 1 FROM ai_exec_task e
                WHERE (t.tracking_data->>'plan_id') IS NOT NULL
                  AND (t.tracking_data->>'plan_id') <> ''
                  AND e.plan_id = (t.tracking_data->>'plan_id')
                  AND e.thread_id = %s
                  AND e.tenant_id = t.tenant_id
            )
        )"""
        )
        params.append(diagnosis_id)
        params.append(diagnosis_id)
    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"""SELECT t.thread_id, t.tenant_id, t.store_id, t.tracking_data, t.created_at,
                    (SELECT MIN(e.thread_id) FROM ai_exec_task e
                     WHERE e.plan_id = (t.tracking_data->>'plan_id')
                       AND e.tenant_id = t.tenant_id) AS diagnosis_id
                    ,(SELECT sk.plan_name FROM ai_solution_knowledge sk
                      WHERE sk.thread_id = t.thread_id
                      ORDER BY sk.created_at DESC LIMIT 1) AS adopted_plan_name
                    FROM ai_effect_tracking t
                    {where_sql}
                    ORDER BY t.created_at DESC OFFSET %s LIMIT %s""",
                params + [skip, limit],
            )
            return await cur.fetchall()


async def get_diagnosis_health_score(thread_id: str) -> float | None:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT report FROM ai_diagnosis_report WHERE thread_id = %s", (thread_id,))
                row = await cur.fetchone()
        if not row:
            return None
        report = row.get("report")
        if isinstance(report, str):
            report = json.loads(report)
        if not isinstance(report, dict):
            return None
        val = report.get("health_score")
        return round(float(val), 1) if val is not None else None
    except Exception:
        return None


async def get_diagnosis_scores(thread_ids: list[str]) -> dict[str, float]:
    if not thread_ids:
        return {}
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """SELECT thread_id, report->>'health_score' AS hs
                   FROM ai_diagnosis_report WHERE thread_id = ANY(%s)""",
                (thread_ids,),
            )
            rows = await cur.fetchall()
    out: dict[str, float] = {}
    for row in rows:
        hs = row.get("hs")
        if hs is None:
            continue
        try:
            out[row["thread_id"]] = round(float(hs), 1)
        except (TypeError, ValueError):
            continue
    return out


async def get_latest_adopted_plan_name(thread_id: str) -> str | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """SELECT plan_name FROM ai_solution_knowledge
                   WHERE thread_id = %s ORDER BY created_at DESC LIMIT 1""",
                (thread_id,),
            )
            row = await cur.fetchone()
            return str((row or {}).get("plan_name") or "").strip() or None


async def get_first_exec_task(thread_id: str, plan_id: str | None = None) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            if plan_id:
                await cur.execute(
                    """SELECT description, task_name, created_at FROM ai_exec_task
                       WHERE thread_id = %s AND plan_id = %s ORDER BY created_at ASC LIMIT 1""",
                    (thread_id, plan_id),
                )
            else:
                await cur.execute(
                    """SELECT description, task_name, created_at FROM ai_exec_task
                       WHERE thread_id = %s ORDER BY created_at ASC LIMIT 1""",
                    (thread_id,),
                )
            return await cur.fetchone()


async def get_earliest_exec_task_created_at(thread_id: str) -> datetime | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT MIN(created_at) AS t FROM ai_exec_task WHERE thread_id = %s",
                (thread_id,),
            )
            row = await cur.fetchone()
            return (row or {}).get("t")


async def get_first_exec_task_plan_store(thread_id: str, tenant_id: str) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT plan_id, store_id FROM ai_exec_task WHERE thread_id = %s AND tenant_id = %s ORDER BY created_at ASC LIMIT 1",
                (thread_id, tenant_id),
            )
            return await cur.fetchone()


async def list_exec_tasks_for_report(thread_id: str) -> list[dict]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT task_name, status, description, deadline FROM ai_exec_task WHERE thread_id = %s ORDER BY created_at ASC",
                (thread_id,),
            )
            return await cur.fetchall()


async def get_exec_task_stats(thread_id: str) -> dict[str, int]:
    stats: dict[str, int] = {
        "pending": 0,
        "ready": 0,
        "running": 0,
        "paused": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0,
    }
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT COALESCE(status, 'pending') AS st, COUNT(*)::int AS cnt FROM ai_exec_task WHERE thread_id = %s GROUP BY COALESCE(status, 'pending')",
                (thread_id,),
            )
            rows = await cur.fetchall()
    for row in rows:
        key = str(row.get("st") or "").lower()
        if key in stats:
            stats[key] = int(row.get("cnt") or 0)
    return stats


async def get_exec_task_team_size(thread_id: str) -> int:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT COUNT(DISTINCT assignee_user_id)::int AS team_size FROM ai_exec_task WHERE thread_id = %s AND assignee_user_id IS NOT NULL",
                (thread_id,),
            )
            row = await cur.fetchone()
            return int((row or {}).get("team_size") or 0)


async def list_snapshots(thread_id: str, *, with_id: bool = False) -> list[dict]:
    fields = "id, snapshot_data, snapshot_at" if with_id else "snapshot_data, snapshot_at"
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"SELECT {fields} FROM ai_effect_snapshot WHERE thread_id = %s ORDER BY snapshot_at ASC",
                (thread_id,),
            )
            return await cur.fetchall()


async def get_latest_snapshot(thread_id: str) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, snapshot_data FROM ai_effect_snapshot WHERE thread_id = %s ORDER BY snapshot_at DESC LIMIT 1",
                (thread_id,),
            )
            return await cur.fetchone()


async def get_snapshot_by_id(snapshot_id: int) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT snapshot_data, snapshot_at FROM ai_effect_snapshot WHERE id = %s",
                (snapshot_id,),
            )
            return await cur.fetchone()


async def insert_snapshot(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    snapshot_data: dict,
    snapshot_at: datetime,
) -> None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO ai_effect_snapshot (thread_id, tenant_id, store_id, snapshot_data, snapshot_at) VALUES (%s, %s, %s, %s, %s)",
                (thread_id, tenant_id, store_id, json.dumps(snapshot_data, ensure_ascii=False), snapshot_at),
            )
        await conn.commit()


async def get_review_report(thread_id: str) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT report, created_at FROM ai_review_report WHERE thread_id = %s", (thread_id,))
            return await cur.fetchone()


async def update_review_report(thread_id: str, report: dict) -> None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE ai_review_report SET report = %s WHERE thread_id = %s",
                (json.dumps(report, ensure_ascii=False), thread_id),
            )
        await conn.commit()


async def upsert_review_report(
    thread_id: str,
    tenant_id: str,
    store_id: str,
    report: dict,
    created_at: datetime,
) -> None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ai_review_report (thread_id, tenant_id, store_id, report, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (thread_id) DO UPDATE SET report = EXCLUDED.report
                """,
                (thread_id, tenant_id, store_id, json.dumps(report, ensure_ascii=False), created_at),
            )
        await conn.commit()


async def search_solution_cases(
    plan_name: str | None,
    skip: int,
    limit: int,
) -> tuple[list[dict], int]:
    where_parts: list[str] = []
    params: list = []
    key = (plan_name or "").strip()
    if key:
        where_parts.append("plan_name ILIKE %s ESCAPE '\\'")
        like = "%" + key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        params.append(like)
    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(f"SELECT COUNT(*) FROM ai_solution_knowledge {where_sql}", params)
            total = int((await cur.fetchone() or {}).get("count", 0))
            await cur.execute(
                f"""SELECT id, tenant_id, thread_id, plan_id, plan_name, target_indicators, industry_code,
                           achievement_rate, indicator_changes, plan_detail, lessons_learned, created_at
                    FROM ai_solution_knowledge {where_sql}
                    ORDER BY achievement_rate DESC OFFSET %s LIMIT %s""",
                params + [skip, limit],
            )
            rows = await cur.fetchall()
    return rows, total


async def list_similar_solution_cases(
    indicator_list: list[str],
    industry: str | None,
    limit: int,
) -> list[dict]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            if indicator_list:
                await cur.execute(
                    """SELECT id, tenant_id, thread_id, plan_id, plan_name, target_indicators, industry_code,
                              achievement_rate, indicator_changes, plan_detail, lessons_learned, created_at
                       FROM ai_solution_knowledge WHERE target_indicators && %s
                       ORDER BY achievement_rate DESC LIMIT %s""",
                    (indicator_list, limit),
                )
            else:
                where = "WHERE industry_code = %s" if industry else ""
                params: list = [industry] if industry else []
                await cur.execute(
                    f"""SELECT id, tenant_id, thread_id, plan_id, plan_name, target_indicators, industry_code,
                               achievement_rate, indicator_changes, plan_detail, lessons_learned, created_at
                        FROM ai_solution_knowledge {where}
                        ORDER BY achievement_rate DESC LIMIT %s""",
                    params + [limit],
                )
            return await cur.fetchall()


async def get_solution_case(case_id: int) -> dict | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM ai_solution_knowledge WHERE id = %s", (case_id,))
            return await cur.fetchone()
