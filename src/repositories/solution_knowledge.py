"""方案沉淀知识库 — 存储复盘验证有效的方案，供后续诊断参考。"""

from __future__ import annotations

import json
import logging

import psycopg.rows

from src.core.datetime_cn import serialize_instant_cn
from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def save_effective_plan(
    tenant_id: str,
    store_id: str,
    thread_id: str,
    plan: dict,
    achievement_rate: float,
    indicator_changes: list[dict],
    lessons_learned: list[str],
    industry_code: str | None = None,
) -> None:
    """将复盘验证有效的方案沉淀到知识库。"""
    target_indicators = plan.get("target_indicators", [])
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ai_solution_knowledge
                        (tenant_id, store_id, thread_id, plan_id, plan_name,
                         target_indicators, industry_code, achievement_rate,
                         indicator_changes, plan_detail, lessons_learned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                    """,
                    (
                        tenant_id[:32], store_id[:32], thread_id[:128],
                        plan.get("plan_id", "")[:32],
                        plan.get("plan_name", "")[:500],
                        target_indicators,
                        industry_code,
                        achievement_rate,
                        json.dumps(indicator_changes, ensure_ascii=False),
                        json.dumps(plan, ensure_ascii=False),
                        json.dumps(lessons_learned, ensure_ascii=False),
                    ),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("方案沉淀失败", plan_id=plan.get("plan_id"), thread_id=thread_id) from e


async def search_similar_plans(
    target_indicators: list[str],
    industry_code: str | None = None,
    min_achievement: float = 50.0,
    limit: int = 5,
) -> list[dict]:
    """检索与目标指标相关且达成率高于阈值的历史有效方案。"""
    if not target_indicators:
        return []
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    """
                    SELECT plan_name, target_indicators, achievement_rate,
                           indicator_changes, plan_detail, lessons_learned,
                           industry_code, created_at
                    FROM ai_solution_knowledge
                    WHERE target_indicators && %s
                      AND achievement_rate >= %s
                    ORDER BY achievement_rate DESC, created_at DESC
                    LIMIT %s
                    """,
                    (target_indicators, min_achievement, limit),
                )
                rows = await cur.fetchall()
                for r in rows:
                    if r.get("created_at") is not None:
                        r["created_at"] = serialize_instant_cn(r["created_at"])
                return rows
    except Exception as e:
        raise AppError("检索方案知识库失败") from e


async def list_knowledge(
    tenant_id: str | None = None,
    industry_code: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页查询知识库。"""
    conditions = []
    params: list = []
    if tenant_id:
        conditions.append("tenant_id = %s")
        params.append(tenant_id)
    if industry_code:
        conditions.append("industry_code = %s")
        params.append(industry_code)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    f"SELECT COUNT(*) AS cnt FROM ai_solution_knowledge {where}",
                    params,
                )
                total = (await cur.fetchone())["cnt"]

                await cur.execute(
                    f"""
                    SELECT id, tenant_id, store_id, thread_id, plan_id, plan_name,
                           target_indicators, industry_code, achievement_rate,
                           indicator_changes, lessons_learned, created_at
                    FROM ai_solution_knowledge
                    {where}
                    ORDER BY achievement_rate DESC, created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [page_size, offset],
                )
                rows = await cur.fetchall()
                for r in rows:
                    if r.get("created_at") is not None:
                        r["created_at"] = serialize_instant_cn(r["created_at"])
                return rows, total
    except Exception as e:
        raise AppError("查询方案知识库失败", tenant_id=tenant_id, industry_code=industry_code, page=page) from e
